"""S3 artifact/state handoff using the normal AWS role/credential chain."""
from pathlib import Path
from urllib.parse import urlparse
import json
import mimetypes
# from .config import atomic_json
from bridge import backup_database

def aws_session(cfg):
    import boto3
    return boto3.Session(region_name=cfg.aws_region)

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(clean(value), indent=2, allow_nan=False))
    tmp.replace(path)

def ensure_bucket(cfg,create=False):
    if not cfg.s3_bucket:
        raise ValueError("Set s3_bucket in config/project.json")
    client = aws_session(cfg).client("s3")
    if create:
        from botocore.exceptions import ClientError
        try:
            client.head_bucket(Bucket=cfg.s3_bucket)
        except ClientError as error:
            if error.response["Error"]["Code"] not in ("404","NoSuchBucket","NotFound"):
                raise
            kwargs = {"Bucket":cfg.s3_bucket}
            if cfg.aws_region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {"LocationConstraint":cfg.aws_region}
            client.create_bucket(**kwargs)
        client.put_public_access_block(Bucket=cfg.s3_bucket,PublicAccessBlockConfiguration={
            "BlockPublicAcls":True,"IgnorePublicAcls":True,"BlockPublicPolicy":True,"RestrictPublicBuckets":True})
        client.put_bucket_encryption(Bucket=cfg.s3_bucket,ServerSideEncryptionConfiguration={
            "Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]})
        client.put_bucket_versioning(Bucket=cfg.s3_bucket,VersioningConfiguration={"Status":"Enabled"})
    else:
        client.head_bucket(Bucket=cfg.s3_bucket)
    return client

def put_file(cfg,path,key):
    path = Path(path)
    client = ensure_bucket(cfg)
    args = {"ContentType":mimetypes.guess_type(path.name)[0] or "application/octet-stream"}
    if path.suffix == ".json": args["CacheControl"] = "no-store"
    client.upload_file(str(path),cfg.s3_bucket,key,ExtraArgs=args)
    return f"s3://{cfg.s3_bucket}/{key}"

def upload_tree(cfg,path,prefix):
    path = Path(path)
    if not path.is_dir(): raise FileNotFoundError(path)
    return [put_file(cfg,file,prefix.rstrip("/")+"/"+file.relative_to(path).as_posix())
            for file in sorted(path.rglob("*")) if file.is_file() and not any(part.startswith(".") for part in file.relative_to(path).parts)]

def download_tree(cfg,s3_uri,destination):
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError("Expected s3://bucket/prefix/")
    prefix = parsed.path.lstrip("/").rstrip("/")+"/"
    destination = Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    client = aws_session(cfg).client("s3")
    count = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=parsed.netloc,Prefix=prefix):
        for item in page.get("Contents",[]):
            key = item["Key"]
            if key.endswith("/"): continue
            target = (destination/key[len(prefix):]).resolve()
            if not target.is_relative_to(destination): raise ValueError("Invalid S3 artifact path")
            target.parent.mkdir(parents=True,exist_ok=True)
            client.download_file(parsed.netloc,key,str(target))
            count += 1
    if not count: raise FileNotFoundError(f"No artifacts found under {s3_uri}")
    return count

def publish(cfg,backup=True):
    snapshot = json.loads(cfg.latest_path.read_text())
    if snapshot.get("schema_version") != "glofwatch-v1" or not isinstance(snapshot.get("lakes"),list):
        raise ValueError("Invalid latest snapshot")
    # Upload archival material before replacing the public feed's current object.
    run = snapshot["generated_at"].replace(":","").replace("+", "_")
    urls = [put_file(cfg,cfg.latest_path,cfg.s3_prefix+f"/runs/{run}/latest.json"),
            put_file(cfg,cfg.features_path,cfg.s3_prefix+f"/runs/{run}/fresh_features.jsonl")]
    if backup:
        database = backup_database(cfg)
        if database: urls.append(put_file(cfg,database,cfg.s3_prefix+"/state/glof_monitor.sqlite"))
        for name in ["lake_registry.csv","measurement_signature.json"]:
            path = cfg.work_path/name
            if path.is_file(): urls.append(put_file(cfg,path,cfg.s3_prefix+"/state/"+name))
    urls.append(put_file(cfg,cfg.latest_path,cfg.key))
    return urls
