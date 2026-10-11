"""One persistent project configuration shared by all notebook kernels."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import tempfile

def find_root(start=None):
    override = os.getenv("GLOFWATCH_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    start = Path(start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        if (path/"glofwatch"/"__init__.py").is_file() and (path/"notebooks").is_dir():
            return path
    raise FileNotFoundError("Open the extracted glofwatch-aws-notebooks folder first")

def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name+".", suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda:file.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()

@dataclass
class ProjectConfig:
    root: Path
    aws_region: str = "ap-south-1"
    s3_bucket: str = ""
    s3_prefix: str = "glofwatch"
    gee_project: str = ""
    mode: str = "live"
    deeplab_filename: str = "deeplabv3_50.keras"
    model_dir: str = "models"
    work_dir: str = ".work"
    segmentation_data_dir: str = "data/segmentation"
    qwen_artifact_dir: str = "models/qwen_jev"
    qwen_model_id: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    qwen_revision: str | None = None
    segmentation_threshold: float = 0.5
    active_lake_ids: tuple = ("UK_GL_01", "UK_GL_02", "SK_GL_01")
    registry_file: str | None = None
    download_budget: int = 24
    backfill_days: int = 120
    optical_kernel: str = "glof-tf"
    qwen_kernel: str = "glof-torch"

    def __post_init__(self):
        self.root = Path(self.root).resolve()
        self.active_lake_ids = tuple(self.active_lake_ids)
        if Path(self.deeplab_filename).name != self.deeplab_filename or not self.deeplab_filename.endswith(".keras"):
            raise ValueError("deeplab_filename must be a .keras filename, without a directory")
        if self.mode not in ("live","demo"):
            raise ValueError("mode must be live or demo")
        if not 0 < self.segmentation_threshold < 1 or self.download_budget < 1 or self.backfill_days < 15:
            raise ValueError("Invalid threshold, download budget or backfill days")
        if not self.active_lake_ids or len(set(self.active_lake_ids)) != len(self.active_lake_ids):
            raise ValueError("active_lake_ids must be nonempty and unique")
        self.s3_prefix = self.s3_prefix.strip("/")
        if not self.s3_prefix or ".." in self.s3_prefix.split("/"):
            raise ValueError("s3_prefix must be a nonempty object prefix")

    def resolve(self,path):
        path = Path(path).expanduser()
        return path if path.is_absolute() else self.root/path

    @property
    def deeplab_path(self): return self.resolve(self.model_dir)/self.deeplab_filename
    @property
    def qwen_path(self): return self.resolve(self.qwen_artifact_dir)
    @property
    def work_path(self): return self.resolve(self.work_dir)
    @property
    def dataset_path(self): return self.resolve(self.segmentation_data_dir)
    @property
    def registry_path(self): return self.resolve(self.registry_file) if self.registry_file else None
    @property
    def latest_path(self): return self.work_path/"latest.json"
    @property
    def features_path(self): return self.work_path/"fresh_features.jsonl"
    @property
    def key(self): return self.s3_prefix+"/processed/latest.json"

    def save(self):
        value = asdict(self)
        value.pop("root")
        atomic_json(self.root/"config"/"project.json",value)

def load_config(root=None):
    root = Path(root).resolve() if root else find_root()
    path = root/"config"/"project.json"
    if not path.is_file():
        raise FileNotFoundError("Run notebook 00 to create config/project.json")
    return ProjectConfig(root=root,**json.loads(path.read_text()))
