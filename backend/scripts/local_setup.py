from __future__ import annotations

import os

os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-1")
os.environ.setdefault("AWS_REGION", "ap-northeast-1")
os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:8001")

import boto3

ENDPOINT = os.environ["DYNAMODB_ENDPOINT_URL"]
REGION = os.environ["AWS_REGION"]

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


def main() -> None:
    client = boto3.client("dynamodb", region_name=REGION, endpoint_url=ENDPOINT)
    existing = set(client.list_tables()["TableNames"])
    for name, spec in TABLES.items():
        if name in existing:
            print(f"skip (exists): {name}")
            continue
        client.create_table(
            TableName=name,
            KeySchema=spec["KeySchema"],
            AttributeDefinitions=spec["AttributeDefinitions"],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"created: {name}")

    resource = boto3.resource("dynamodb", region_name=REGION, endpoint_url=ENDPOINT)

    resource.Table("Classes").put_item(
        Item={
            "PK": "CLASS#c_001",
            "classId": "c_001",
            "name": "少年サッカークラス",
            "description": "毎週日曜開催",
            "targetGrades": ["小1", "小2", "小3", "小4", "小5", "小6"],
        }
    )
    print("seeded: Classes c_001")

    from datetime import date

    today = date.today()
    resource.Table("Schedule").put_item(
        Item={
            "PK": "CLASS#c_001",
            "SK": f"DATE#{today.isoformat()}",
            "date": today.isoformat(),
            "startTime": "00:00",
            "endTime": "23:59",
            "location": "第一体育館",
        }
    )
    print(f"seeded: Schedule c_001 {today.isoformat()} (00:00-23:59, always accepting)")

    month = today.strftime("%Y-%m")
    resource.Table("MonthlyPin").put_item(Item={"PK": f"CLASS#c_001#MONTH#{month}", "pin": "1234"})
    print(f"seeded: MonthlyPin c_001 {month} = 1234")


if __name__ == "__main__":
    main()
