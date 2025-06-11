import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import types
import csv
import io
import importlib
from datetime import datetime

# Fake boto3 and urllib3 modules

class FakePaginator:
    def __init__(self, snapshots):
        self.snapshots = snapshots

    def paginate(self, OwnerIds=None):
        yield {"Snapshots": self.snapshots}


class FakeEC2Client:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.deleted = []

    def get_paginator(self, name):
        assert name == "describe_snapshots"
        return FakePaginator(self.snapshots)

    def delete_snapshot(self, SnapshotId=None):
        self.deleted.append(SnapshotId)


class FakeS3Client:
    def __init__(self):
        self.put_calls = []

    def put_object(self, Bucket=None, Key=None, Body=None):
        self.put_calls.append({"Bucket": Bucket, "Key": Key, "Body": Body})


class FakeHTTP:
    def request(self, *args, **kwargs):
        class Resp:
            status = 200
            data = b""
        return Resp()


def setup_module(module):
    # snapshots for one volume: 6 snapshots with ascending times
    snapshots = []
    for i in range(1, 7):
        snapshots.append({
            "SnapshotId": f"snap-{i}",
            "StartTime": datetime(2021, 1, i),
            "VolumeId": "vol-1",
            "State": "completed",
            "Description": f"snapshot {i}",
            "VolumeSize": i,
            "Tags": [{"Key": "Name", "Value": f"snap{i}"}],
        })

    module.fake_ec2 = FakeEC2Client(snapshots)
    module.fake_s3 = FakeS3Client()

    boto3_stub = types.ModuleType("boto3")

    def client(service):
        if service == "ec2":
            return module.fake_ec2
        if service == "s3":
            return module.fake_s3
        raise ValueError(service)

    boto3_stub.client = client
    sys.modules["boto3"] = boto3_stub

    urllib3_stub = types.ModuleType("urllib3")
    urllib3_stub.PoolManager = lambda: FakeHTTP()
    sys.modules["urllib3"] = urllib3_stub



def test_old_snapshots_to_csv():
    import ebs_snapshot_inspection as mod

    mod.SEND_SLACK_MESSAGE = False
    mod.DELETE_SNAPSHOTS = False

    mod.lambda_handler({}, None)

    assert len(fake_s3.put_calls) == 1
    body = fake_s3.put_calls[0]["Body"]
    rows = list(csv.reader(io.StringIO(body)))

    # first row is header, next two rows should be the old snapshots
    assert rows[1][0] == "snap-2"
    assert rows[2][0] == "snap-1"

    # last row should contain total size 3 (sizes of snap-2 and snap-1)
    assert rows[-1][0] == "Total Size to Delete (GiB)"
    assert int(rows[-1][1]) == 3
