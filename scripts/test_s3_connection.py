import argparse
import os
import sys
import uuid

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv


def _require_value(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"Missing required value: {name}")
    return value


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default=os.environ.get("AWS_BUCKET_NAME"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-southeast-1"))
    parser.add_argument("--prefix", default="healthcheck/")
    parser.add_argument("--upload-test", action="store_true")
    parser.add_argument("--skip-sts", action="store_true")
    args = parser.parse_args()

    bucket = _require_value("AWS_BUCKET_NAME or --bucket", args.bucket)

    session = boto3.session.Session(region_name=args.region)

    s3 = session.client("s3")

    if not args.skip_sts:
        try:
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            print({"sts_account": identity.get("Account"), "sts_arn": identity.get("Arn")})
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise RuntimeError(
                "Không tìm thấy AWS credentials. Hãy export AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY "
                "hoặc cấu hình AWS profile/role (EC2 IAM Role), rồi chạy lại."
            ) from e

    try:
        s3.head_bucket(Bucket=bucket)
        print({"bucket": bucket, "head_bucket": "ok"})
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        raise RuntimeError({"bucket": bucket, "head_bucket": "failed", "error_code": code}) from e

    listed = s3.list_objects_v2(Bucket=bucket, Prefix=args.prefix, MaxKeys=5)
    keys = [obj["Key"] for obj in listed.get("Contents", [])]
    print({"bucket": bucket, "list_prefix": args.prefix, "keys": keys})

    if args.upload_test:
        key = f"{args.prefix.rstrip('/')}/probe-{uuid.uuid4().hex}.txt"
        body = b"s3-connection-ok\n"
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/plain")
        downloaded = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        if downloaded != body:
            raise RuntimeError({"upload_test": "failed", "key": key})
        s3.delete_object(Bucket=bucket, Key=key)
        print({"upload_test": "ok", "key": key})

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print({"error": str(e)}, file=sys.stderr)
        raise
