
Here is a sample README file for the provided Lambda function script:

---

# EBS Snapshot Cleanup Lambda

This AWS Lambda function automates the cleanup of old EBS snapshots. It identifies and deletes snapshots, keeping only the newest four per volume, and uploads a CSV report to an S3 bucket. Optionally, the function sends a Slack notification with the report link and total space marked for deletion.

## Features

- Deletes older EBS snapshots beyond the newest four for each volume.
- Generates a CSV report with details about deleted snapshots.
- Uploads the report to a specified S3 bucket.
- Sends a Slack notification with the report link and storage space summary.

## Prerequisites

- **AWS IAM Role**: The Lambda function requires an IAM role with permissions for:
  - `ec2:DescribeSnapshots`, `ec2:DeleteSnapshot`, `s3:PutObject`, and `s3:GetObject`.
- **S3 Bucket**: Specify an S3 bucket for storing the CSV report.
- **Slack Webhook**: Set up a Slack Webhook URL to enable Slack notifications.

## Configuration

Set the following constants in the Lambda function:

- **`DELETE_SNAPSHOTS`**: Set to `True` to enable snapshot deletion; `False` to generate only the report.
- **`SEND_SLACK_MESSAGE`**: Set to `True` to send a Slack notification when the report is uploaded.
- **`S3_BUCKET`**: Your S3 bucket name for storing the CSV report.
- **`S3_KEY`**: Desired name for the CSV report file in S3 (e.g., `old_snapshots.csv`).
- **`SLACK_WEBHOOK_URL`**: Your Slack Webhook URL for sending notifications.
- **`SLACK_CHANNEL`**: The Slack channel to receive notifications.

## Usage

1. Deploy the script as an AWS Lambda function.
2. Configure the environment variables (`DELETE_SNAPSHOTS`, `SEND_SLACK_MESSAGE`, etc.).
3. Schedule the Lambda function using Amazon CloudWatch Events for regular cleanup.

## Example Workflow

1. **Snapshot Retrieval**: The function lists all snapshots owned by the account and sorts them by `StartTime`.
2. **Filtering Old Snapshots**: For each volume, snapshots beyond the four most recent are flagged as old snapshots.
3. **CSV Report Generation**: Details of old snapshots are written to a CSV file stored in S3.
4. **Optional Deletion**: If `DELETE_SNAPSHOTS` is `True`, the function deletes the flagged snapshots.
5. **Slack Notification**: Sends a message to the specified Slack channel with a report link and summary.

## Code

```python
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
S3_BUCKET = 'verato-snapshot-inspection'  # Replace with your S3 bucket name
S3_KEY = 'old_snapshots.csv'  # Replace with your desired S3 key (file name)

# Slack configuration
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/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'  # Replace with your Slack webhook URL
SLACK_CHANNEL = '#infoservices-alerts'  # Replace with your Slack channel

# Main function
def lambda_handler(event, context):
    # Function logic here...
```

## Logging and Monitoring

- Logs information about the snapshots processed, deleted snapshots, and total storage space marked for deletion.
- Logs errors encountered during processing for troubleshooting.

## License

This project is licensed under the MIT License.
