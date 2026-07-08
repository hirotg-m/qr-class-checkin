from __future__ import annotations

import os
from functools import cache

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
# フロントエンド(S3+CloudFront)とAPIが別オリジンのため必要。Bearerトークン方式でCookieを
# 使わないためCSRFの懸念がなく、既定は全許可とする（絞りたい場合はカンマ区切りで指定）。
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
DYNAMODB_TABLE_PREFIX = os.environ.get("DYNAMODB_TABLE_PREFIX", "")
# ローカル開発・テスト用（DynamoDB Local / moto のエンドポイント）。本番では未設定。
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")

CHECKIN_TOKEN_TTL_SECONDS = 10 * 60
AUTH_TOKEN_TTL_SECONDS = 8 * 60 * 60


def table_name(logical_name: str) -> str:
    return f"{DYNAMODB_TABLE_PREFIX}{logical_name}"


@cache
def _ssm_parameter(name: str) -> str:
    client = boto3.client("ssm", region_name=AWS_REGION)
    response = client.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_secret(direct_env_name: str, ssm_param_env_name: str) -> str:
    """direct_env_name の環境変数が設定されていればそれを使う（ローカル/テスト用）。
    なければ ssm_param_env_name が指すSSMパラメータ名からSecureStringを取得する（本番用、
    docs/backend-design.md 8節）。"""
    direct_value = os.environ.get(direct_env_name)
    if direct_value is not None:
        return direct_value
    param_name = os.environ[ssm_param_env_name]
    return _ssm_parameter(param_name)


def jwt_secret() -> str:
    return get_secret("JWT_SECRET", "JWT_SECRET_PARAM")


def teacher_code() -> str:
    return get_secret("TEACHER_CODE", "TEACHER_CODE_PARAM")


def admin_code() -> str:
    return get_secret("ADMIN_CODE", "ADMIN_CODE_PARAM")
