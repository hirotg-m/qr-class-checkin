from __future__ import annotations

import boto3

from app.core.config import AWS_REGION, DYNAMODB_ENDPOINT_URL, table_name


def get_table(logical_name: str):
    resource = boto3.resource(
        "dynamodb", region_name=AWS_REGION, endpoint_url=DYNAMODB_ENDPOINT_URL
    )
    return resource.Table(table_name(logical_name))
