"""Read-only API Gateway Lambda for GLOFWatch dashboard.

Environment variables:
  S3_BUCKET: private bucket containing exported lake assessments
  S3_OBJECT_KEY: defaults to processed/latest.json
  ALLOWED_ORIGIN: dashboard origin, e.g. https://main.example.amplifyapp.com

IAM role must permit s3:GetObject on the specified object.
Use API Gateway HTTP API with route GET /lakes/latest and enable CORS.
"""
import json
import os

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
BUCKET = os.environ.get("S3_BUCKET", "")
KEY = os.environ.get("S3_OBJECT_KEY", "processed/latest.json")
ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8000")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": ORIGIN,
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "GET")
    if method not in ("GET", "OPTIONS"):
        return respond(405, {"error": "Method not allowed"})
    if method == "OPTIONS":
        return respond(200, {"ok": True})
    if not BUCKET:
        return respond(500, {"error": "Server configuration missing S3_BUCKET"})

    try:
        obj = s3.get_object(Bucket=BUCKET, Key=KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
    except (ClientError, ValueError, UnicodeDecodeError) as exc:
        # Do not expose internal object keys, IAM or bucket details to clients.
        print("GLOFWatch retrieval failed:", type(exc).__name__)
        return respond(503, {"error": "Lake data temporarily unavailable"})

    if isinstance(data, list):
        lakes = data
    elif isinstance(data, dict):
        lakes = data.get("lakes", data.get("results", []))
    else:
        lakes = []
    if not isinstance(lakes, list):
        return respond(503, {"error": "Invalid stored data schema"})

    return respond(200, {"lakes": lakes, "count": len(lakes)})
