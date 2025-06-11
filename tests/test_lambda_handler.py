import os
import sys
from types import ModuleType
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Provide a minimal dummy boto3 module so that the module under test imports
# without requiring the real package.
dummy_boto3 = ModuleType("boto3")
dummy_boto3.client = lambda *args, **kwargs: None
sys.modules.setdefault("boto3", dummy_boto3)

dummy_urllib3 = ModuleType("urllib3")
dummy_urllib3.PoolManager = lambda *args, **kwargs: None
sys.modules.setdefault("urllib3", dummy_urllib3)

import ebs_snapshot_inspection


def test_lambda_handler_reraises_exception():
    # Force boto3.client to raise an error to trigger the exception path
    with mock.patch('boto3.client', side_effect=Exception("boom")):
        with pytest.raises(Exception):
            ebs_snapshot_inspection.lambda_handler({}, {})
