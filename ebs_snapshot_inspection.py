import boto3
import logging
import csv
from io import StringIO
import json
import urllib3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boolean to enable/disable deletion of snapshots
DELETE_SNAPSHOTS = False
SEND_SLACK_MESSAGE = True  # Boolean to enable/disable Slack notification

# S3 bucket and key for storing CSV output
S3_BUCKET = 'snapshot-inspection'  # Replace with your S3 bucket name
S3_KEY = 'old_snapshots.csv'  # Replace with your desired S3 key (file name)

# Slack configuration
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/xxx/xxx'  # Replace with your Slack webhook URL
SLACK_CHANNEL = '#alert-channel'  # Replace with your Slack channel

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    s3 = boto3.client('s3')
    http = urllib3.PoolManager()

    try:
        # Describe all snapshots in the account
        paginator = ec2.get_paginator('describe_snapshots')
        page_iterator = paginator.paginate(OwnerIds=['self'])

        snapshots = []
        for page in page_iterator:
            snapshots.extend(page['Snapshots'])

        # Sort snapshots by StartTime (most recent first)
        snapshots.sort(key=lambda x: x['StartTime'], reverse=True)

        # Output a list of all snapshots that are not the newest 4 for each volume
        snapshots_by_volume = {}
        for snapshot in snapshots:
            volume_id = snapshot['VolumeId']
            if volume_id not in snapshots_by_volume:
                snapshots_by_volume[volume_id] = []
            snapshots_by_volume[volume_id].append(snapshot)

        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['SnapshotId', 'StartTime', 'VolumeId', 'State', 'Description', 'Size (GiB)', 'Name'])

        total_size_by_volume = {}
        total_size_to_delete = 0

        for volume_id, volume_snapshots in snapshots_by_volume.items():
            if len(volume_snapshots) > 4:
                old_snapshots = volume_snapshots[4:]
                for snapshot in old_snapshots:
                    snapshot_id = snapshot['SnapshotId']
                    start_time = snapshot['StartTime']
                    state = snapshot['State']
                    description = snapshot.get('Description', 'N/A')
                    size = snapshot['VolumeSize']
                    name = next((tag['Value'] for tag in snapshot.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')

                    csv_writer.writerow([snapshot_id, start_time, volume_id, state, description, size, name])
                    logger.info(f"Old snapshot: {snapshot_id}, Description: {description}, Size: {size} GiB, Name: {name}")

                    # Accumulate the size for each volume
                    if volume_id not in total_size_by_volume:
                        total_size_by_volume[volume_id] = 0
                    total_size_by_volume[volume_id] += size

                    # Accumulate total size to delete
                    total_size_to_delete += size

                    # Delete the snapshot if DELETE_SNAPSHOTS is True
                    if DELETE_SNAPSHOTS:
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        logger.info(f"Deleted snapshot: {snapshot_id}")

        # Log the total size by volume
        for volume_id, total_size in total_size_by_volume.items():
            logger.info(f"Total size for snapshots in volume '{volume_id}': {total_size} GiB")

        # Log the total size to be deleted
        logger.info(f"Total size to be deleted: {total_size_to_delete} GiB")

        # Add total size to delete to the CSV
        csv_writer.writerow([])  # Add an empty row for separation
        csv_writer.writerow(['Total Size to Delete (GiB)', total_size_to_delete])

        # Upload CSV to S3
        s3.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=csv_buffer.getvalue())
        logger.info(f"Old snapshots list uploaded to S3: s3://{S3_BUCKET}/{S3_KEY}")

        # Send Slack message if enabled
        if SEND_SLACK_MESSAGE:
            slack_message = {
                "channel": SLACK_CHANNEL,
                "text": f"Old snapshots list uploaded to S3: s3://{S3_BUCKET}/{S3_KEY}\nTotal size to be deleted: {total_size_to_delete} GiB"
            }
            encoded_message = json.dumps(slack_message).encode('utf-8')
            response = http.request('POST', SLACK_WEBHOOK_URL, body=encoded_message, headers={'Content-Type': 'application/json'})
            if response.status == 200:
                logger.info("Slack message sent successfully.")
            else:
                logger.error(f"Failed to send Slack message. Status code: {response.status}, Response: {response.data}")
    except Exception as e:
        logger.error(f"Error processing snapshots: {str(e)}")

def get_instance_name(ec2, volume_id):
    try:
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        if response['Volumes']:
            volume = response['Volumes'][0]
            if 'Attachments' in volume and volume['Attachments']:
                instance_id = volume['Attachments'][0]['InstanceId']
                instance_response = ec2.describe_instances(InstanceIds=[instance_id])
                if instance_response['Reservations']:
                    instance = instance_response['Reservations'][0]['Instances'][0]
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            return tag['Value']
        return 'N/A'
    except Exception as e:
        logger.error(f"Error getting instance name for volume {volume_id}: {str(e)}")
        return 'N/A'
