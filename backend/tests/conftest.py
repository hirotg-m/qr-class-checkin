from __future__ import annotations

import os

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")
os.environ.setdefault("AWS_REGION", "ap-northeast-1")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TEACHER_CODE", "11111111")
os.environ.setdefault("ADMIN_CODE", "99999999")

import boto3  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from moto import mock_aws  # noqa: E402

from app.core.config import AWS_REGION  # noqa: E402

_KEY_ONLY = {
    "KeySchema": [{"AttributeName": "PK", "KeyType": "HASH"}],
    "AttributeDefinitions": [{"AttributeName": "PK", "AttributeType": "S"}],
}
_KEY_AND_SORT = {
    "KeySchema": [
        {"AttributeName": "PK", "KeyType": "HASH"},
        {"AttributeName": "SK", "KeyType": "RANGE"},
    ],
    "AttributeDefinitions": [
        {"AttributeName": "PK", "AttributeType": "S"},
        {"AttributeName": "SK", "AttributeType": "S"},
    ],
}

TABLES = {
    "Classes": _KEY_ONLY,
    "Schedule": _KEY_AND_SORT,
    "MonthlyPin": _KEY_ONLY,
    "Participants": _KEY_AND_SORT,
    "SessionLog": _KEY_AND_SORT,
    "LoginAttempts": _KEY_ONLY,
}


@pytest.fixture()
def dynamodb_tables():
    with mock_aws():
        client = boto3.client("dynamodb", region_name=AWS_REGION)
        for name, spec in TABLES.items():
            client.create_table(
                TableName=name,
                KeySchema=spec["KeySchema"],
                AttributeDefinitions=spec["AttributeDefinitions"],
                BillingMode="PAY_PER_REQUEST",
            )
        yield


@pytest.fixture()
def client(dynamodb_tables):
    from app.main import app

    return TestClient(app)
