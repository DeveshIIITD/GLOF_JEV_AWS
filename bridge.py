"""The handoff between TensorFlow, PyTorch, S3, and the dashboard."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
import os
import tempfile
from dataclasses import dataclass, asdict
import sys
# sys.path.insert(0, "shared/GLOF/")
# import sys
# from pathlib import Path
from sklearn.metrics import log_loss

PROMPT_VERSION = "glof-features-v1"
CLASS_NAMES = ("NO_ONSET_WITHIN_72H", "ONSET_0_TO_24H", "ONSET_24_TO_72H")
FEATURE_COLUMNS = [
    "area_km2", "baseline_km2", "pct_vs_baseline", "pct_vs_prev", "days_since_prev", "z",
    "n_history", "footprint_valid_frac", "optical_age_days",
    "sar_pct_change", "sar_z", "sar_n_baseline", "sar_age_days",
    "wx_rain_24h_mm", "wx_rain_72h_mm", "wx_forecast_rain_24h_mm", "wx_forecast_rain_72h_mm",
    "wx_temp_c", "wx_temp_max_72h_c", "eq_max_mag_near_72h", "eq_nearest_km_24h",
    "gpm_rain_24h_mm", "possible_ice_cover"
]
# current_dir = Path(__file__).resolve().parent
# 2. Add it to the top priority index
# if str(current_dir) not in sys.path:
#     sys.path.insert(0, str(current_dir))
# from .config import atomic_json
# from features import clean, canonical, utc, measurement_gate, monitor_to_training_rows

LEVEL_TO_RISK = {"GREEN":"low","YELLOW":"watch","ORANGE":"high","RED":"high"}

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

def save_cycle(cfg, results, clock, histories=None, ingest_stats=None, demo=False):
    rows = monitor_to_training_rows(results,clock)
    Path(cfg.work_path).mkdir(parents=True,exist_ok=True)
    # Atomic replacement prevents the next kernel from seeing a partial batch.
    tmp = Path(cfg.features_path).with_suffix(".tmp")
    tmp.write_text("".join(canonical(row)+"\n" for row in rows),encoding="utf-8")
    tmp.replace(Path(cfg.features_path))
    pd.DataFrame(rows).to_csv(Path(cfg.work_path)/"training_labels_UNVERIFIED.csv",index=False)
    lakes = []
    for (lake,assessment),row in zip(results,rows):
        metrics = assessment.get("metrics",{})
        warnings = measurement_gate(row,clock)
        # A zero anomaly score without measurements must not look like a safe lake.
        quality = "INSUFFICIENT_DATA" if warnings else "RECENT_CHANGE_MEASUREMENTS"
        lakes.append(clean({
            "lake_id":str(lake["lake_id"]),"name":lake["name"],"region":lake.get("region"),
            "lat":lake["lat"],"lon":lake["lon"],"level":assessment["level"],
            "risk": "unknown" if warnings else LEVEL_TO_RISK[assessment["level"]],
            "score":assessment["score"],"score_kind":"ANOMALY_POINTS",
            "area_km2":metrics.get("area_km2"),"area_change_pct":metrics.get("pct_vs_baseline"),
            "assessed_at":row["assessed_at"],"features_available_at":row["features_available_at"],
            "optical_time":metrics.get("optical_time"),"sar_time":metrics.get("sar_time"),
            "history":(histories or {}).get(lake["lake_id"],[]),"reasons":assessment["reasons"],
            "data_quality":quality,"warnings":warnings,"metrics":metrics,"qwen":None,
            "observations_synthetic":demo,
        }))
    snapshot = {"schema_version":"glofwatch-v1","generated_at":utc(clock).isoformat(),
                "observation_mode":"SYNTHETIC_DEMO" if demo else "LIVE_MEASUREMENTS",
                "qwen_status":"NOT_RUN","ingest_stats":ingest_stats or {},"lakes":lakes,"count":len(lakes)}
    atomic_json(cfg.latest_path,clean(snapshot))
    archive = Path(cfg.work_path)/"snapshots"/(utc(clock).strftime("%Y%m%dT%H%M%S%fZ")+".json")
    atomic_json(archive,clean(snapshot))
    return snapshot

def read_feature_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

def merge_qwen(snapshot,predictions):
    snapshot = json.loads(json.dumps(snapshot,allow_nan=False))
    expected = {(lake["lake_id"],lake["assessed_at"]) for lake in snapshot["lakes"]}
    keys = [(p["lake_id"],p["assessed_at"]) for p in predictions]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Qwen predictions must match the lake IDs AND assessment clocks of this snapshot")
    lookup = dict(zip(keys,predictions))
    for lake in snapshot["lakes"]:
        prediction = lookup[(lake["lake_id"],lake["assessed_at"])]
        if prediction.get("answers"):
            a = prediction["answers"]
            p24, p72 = a["glof_next_24h"]["noul"],a["glof_next_72h"]["noul"]
            if not 0 <= p24 <= p72 <= 1:
                raise ValueError("Qwen horizon outputs are invalid")
        lake["qwen"] = clean(prediction)
    states = sorted({p["status"] for p in predictions})
    snapshot["qwen_status"] = ", ".join(states)
    return snapshot

def predict_snapshot(cfg,skip_qwen=False):
    snapshot = json.loads(cfg.latest_path.read_text())
    rows = read_feature_rows(cfg.features_path)
    if skip_qwen:
        snapshot["qwen_status"] = "SKIPPED"
    else:
        from .qwen import load_trained_head,predict_glof
        if not (cfg.qwen_path/"glof_jev_head.pt").is_file():
            raise FileNotFoundError("Run notebook 04 or upload your matching Qwen head + metadata first")
        tokenizer,model,metadata = load_trained_head(cfg.qwen_path)
        clock = snapshot["generated_at"] if snapshot["observation_mode"] == "SYNTHETIC_DEMO" else datetime.now(timezone.utc)
        predictions = predict_glof(rows,tokenizer,model,metadata,now=clock)
        snapshot = merge_qwen(snapshot,predictions)
    atomic_json(cfg.latest_path,snapshot)
    return snapshot

def backup_database(cfg):
    source = cfg.work_path/"glof_monitor.sqlite"
    target = cfg.work_path/"backups"/"glof_monitor.sqlite"
    if not source.is_file():
        return None
    target.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(source) as origin,sqlite3.connect(target) as destination:
        origin.backup(destination)
    return target

def demo_cycle(cfg,clock=None):
    """Fictional measurements for checking software integration without external services."""
    clock = utc(clock or datetime.now(timezone.utc))
    results, histories = [],{}
    for i,(level,score,pct) in enumerate([("GREEN",0,2),("YELLOW",2,24),("ORANGE",5,-62)]):
        lake = {"lake_id":f"DEMO_{i+1:02d}","name":f"Fictional demo lake {i+1}",
                "region":"Synthetic software demo","lat":30.1+i*.1,"lon":79.1+i*.2}
        base = .6+i*.2
        area = base*(1+pct/100)
        metrics = {"area_km2":area,"baseline_km2":base,"pct_vs_baseline":pct,"pct_vs_prev":pct,
                   "days_since_prev":5,"z":pct/5,"n_history":6,"footprint_valid_frac":.95,
                   "optical_time":(clock-pd.Timedelta(days=2)).isoformat(),
                   "sar_time":(clock-pd.Timedelta(days=3)).isoformat(),"sar_n_baseline":5,
                   "sar_pct_change":pct*.8,"sar_z":pct/10,
                   "wx_rain_24h_mm":12.,"wx_rain_72h_mm":25.,"wx_forecast_rain_24h_mm":14.,
                   "wx_forecast_rain_72h_mm":30.,"wx_temp_c":4.,"wx_temp_max_72h_c":7.,
                   "possible_ice_cover":False}
        results.append((lake,{"level":level,"score":score,"reasons":["Simulated software-test measurements"],"metrics":metrics}))
        histories[lake["lake_id"]] = [{"date":(clock-pd.Timedelta(days=20-j*3)).isoformat(),
                                      "area_km2":base if j<6 else area} for j in range(7)]
    return save_cycle(cfg,results,clock,histories,{"processed":0,"reliable":0,"backlog":0},demo=True)


"""Measurement contract and label validation. No TensorFlow/PyTorch imports.
"""


def utc(value):
    t = pd.Timestamp(value)
    if pd.isna(t):
        raise ValueError("A required timestamp is missing")
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def bool_value(value):
    if value is None or pd.isna(value): return None
    if isinstance(value, (bool, np.bool_)): return bool(value)
    if str(value).strip().lower() in {"true", "1", "1.0"}: return True
    if str(value).strip().lower() in {"false", "0", "0.0"}: return False
    raise ValueError(f"Invalid boolean: {value!r}")


def clean(value):
    if isinstance(value, dict): return {str(k): clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)): return [clean(v) for v in value]
    if value is None or value is pd.NA: return None
    if isinstance(value, (bool, np.bool_)): return bool(value)
    if isinstance(value, (int, np.integer)): return int(value)
    if isinstance(value, (float, np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp, datetime)): return utc(value).isoformat()
    return value


def canonical(value):
    return json.dumps(clean(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def derive_target(row):
    at, available = utc(row["assessed_at"]), utc(row["features_available_at"])
    if available > at:
        raise ValueError(f"{row['sample_id']}: features were not available at the prediction clock")
    event = row.get("event_start_utc")
    if pd.notna(event) and str(event).strip():
        delta = (utc(event) - at).total_seconds() / 3600
        if delta <= 0:
            raise ValueError(f"{row['sample_id']}: post-onset row; use a separate detection dataset")
        if delta <= 24: return 1
        if delta <= 72: return 2
    end = row.get("label_verified_until_utc")
    if pd.isna(end) or utc(end) < at + pd.Timedelta(hours=72):
        raise ValueError(f"{row['sample_id']}: cannot infer a negative without verified 72-hour coverage")
    return 0


def validate_data(data, allow_synthetic):
    df = data.copy()
    required = {"sample_id", "lake_id", "episode_id", "assessed_at", "features_available_at",
        "event_start_utc", "label_verified_until_utc", "label_status", "label_source", "is_synthetic"}
    missing = required - set(df.columns)
    if missing: raise ValueError(f"Missing metadata columns: {sorted(missing)}")
    if df.empty or df.sample_id.isna().any() or df.sample_id.duplicated().any():
        raise ValueError("Need nonempty data with unique sample_id values")
    for col in ["lake_id", "episode_id", "label_source"]:
        if df[col].isna().any() or df[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing {col}")
    df["is_synthetic"] = df.is_synthetic.map(bool_value)
    if df.is_synthetic.isna().any(): raise ValueError("is_synthetic must be explicitly true/false")
    if df.is_synthetic.any() and not allow_synthetic:
        raise ValueError("Synthetic rows are forbidden in real training mode")
    expected_status = np.where(df.is_synthetic, "SYNTHETIC", "VERIFIED")
    if not (df.label_status.to_numpy() == expected_status).all():
        raise ValueError("Unverified labels: complete independent labelling before training")
    if df.is_synthetic.any() and not df.is_synthetic.all():
        raise ValueError("Keep synthetic demonstrations and real event training separate")
    for col in FEATURE_COLUMNS:
        if col not in df: df[col] = np.nan
        if col == "possible_ice_cover":
            df[col] = df[col].map(bool_value).map({True:1.0, False:0.0})
        else:
            df[col] = pd.to_numeric(df[col], errors="raise")
        if np.isinf(df[col].to_numpy(float)).any(): raise ValueError(f"Infinite values in {col}")
    for col in ["area_km2", "baseline_km2", "optical_age_days", "sar_age_days", "days_since_prev",
        "n_history", "sar_n_baseline", "eq_nearest_km_24h", "gpm_rain_24h_mm",
        "wx_rain_24h_mm", "wx_rain_72h_mm", "wx_forecast_rain_24h_mm", "wx_forecast_rain_72h_mm"]:
        if (df[col].dropna() < 0).any(): raise ValueError(f"Negative values in {col}")
    if not df.footprint_valid_frac.dropna().between(0,1).all():
        raise ValueError("footprint_valid_frac must be between zero and one")
    df["target_id"] = [derive_target(r) for r in df.to_dict("records")]
    if "event_class" in df and df.event_class.notna().any():
        expected = df.target_id.map(dict(enumerate(CLASS_NAMES)))
        if not df.event_class.fillna(expected).eq(expected).all():
            raise ValueError("Provided event_class disagrees with onset/coverage timestamps")
    if set(df.target_id) != {0,1,2}: raise ValueError("This training task needs examples of all three outcomes")
    df["target_name"] = df.target_id.map(dict(enumerate(CLASS_NAMES)))
    return df


def make_synthetic_sample(seed=42, n_lakes=60, episodes_per_lake=12):
    rng = np.random.default_rng(seed)
    rows = []
    for lake in range(n_lakes):
        lake_base = float(np.exp(rng.uniform(np.log(.03), np.log(2.0))))
        for episode in range(episodes_per_lake):
            at = pd.Timestamp("2025-05-01T00:00:00Z") + pd.Timedelta(days=episode*8 + lake%5)
            pct = float(np.clip(rng.normal(4,16), -65, 65))
            base = lake_base * float(rng.uniform(.9,1.1))
            rain24 = float(rng.gamma(1.1,18)); rain72 = rain24 + float(rng.gamma(1.4,18))
            forecast24 = float(rng.gamma(1.1,22))
            forecast72 = forecast24 + float(rng.gamma(1.5,23))
            temp = float(rng.uniform(-7,15))
            sarpct = float(np.clip(pct + rng.normal(0,10),-80,80))
            latent = -3.2 + 0.045 * max(pct,0) + 0.022 * forecast72 + .045 * max(temp,0) + rng.normal(0,1.1)
            toy_p = 1 / (1 + np.exp(-np.clip(latent,-20,20)))
            occurrence = bool(rng.random() < toy_p)
            onset = None
            if occurrence:
                onset_hours = float(rng.uniform(.1,24) if rng.random() < .5 else rng.uniform(24.01,72))
                onset = (at + pd.Timedelta(hours=onset_hours)).isoformat()
            row = {
                "sample_id": f"SYN_L{lake:03d}_E{episode:02d}", "lake_id": f"SYN_L{lake:03d}",
                "episode_id": f"SYN_L{lake:03d}_E{episode:02d}", "assessed_at": at.isoformat(),
                "features_available_at": at.isoformat(), "event_start_utc": onset,
                "label_verified_until_utc": (at + pd.Timedelta(hours=96)).isoformat(),
                "label_status": "SYNTHETIC", "label_source": "TOY_STOCHASTIC_GENERATOR_V1_NOT_REAL",
                "is_synthetic": True,
                "area_km2": base * (1+pct/100), "baseline_km2": base,
                "pct_vs_baseline": pct, "pct_vs_prev": pct + rng.normal(0,6),
                "days_since_prev": float(rng.uniform(4,12)), "z": pct/5,
                "n_history": int(rng.integers(4,15)), "footprint_valid_frac": float(rng.uniform(.75,1)),
                "optical_age_days": float(rng.uniform(.2,10)), "sar_pct_change": sarpct,
                "sar_z": sarpct/10, "sar_n_baseline": int(rng.integers(4,12)),
                "sar_age_days": float(rng.uniform(.2,10)), "wx_rain_24h_mm": rain24,
                "wx_rain_72h_mm": rain72, "wx_forecast_rain_24h_mm": forecast24,
                "wx_forecast_rain_72h_mm": forecast72, "wx_temp_c": temp,
                "wx_temp_max_72h_c": temp + rng.uniform(0,5),
                "eq_max_mag_near_72h": float(rng.uniform(2.5,5.5)) if rng.random()<.1 else np.nan,
                "eq_nearest_km_24h": float(rng.uniform(15,230)) if rng.random()<.1 else np.nan,
                "gpm_rain_24h_mm": max(0,rain24 + float(rng.normal(0,5))), "possible_ice_cover": temp < -2}
            # Missing context is deliberately present; absence is not a measured zero.
            if rng.random() < .08:
                row["gpm_rain_24h_mm"] = np.nan
            if rng.random() < .04:
                row["wx_forecast_rain_24h_mm"] = row["wx_forecast_rain_72h_mm"] = np.nan
            for key in FEATURE_COLUMNS:
                if isinstance(row[key], (float, np.floating)):
                    row[key] = round(float(row[key]),4)
            row["event_class"] = CLASS_NAMES[derive_target(row)]
            rows.append(row)
    return pd.DataFrame(rows)


def split_dataset(df, mode="group", seed=42):
    result = df.copy()
    names = ("train", "validation", "calibration", "test")
    if mode == "group":
        groups = np.array(sorted(result.lake_id.astype(str).unique()))
        if len(groups) < 20: raise ValueError("Need at least 20 lake groups for this four-way example split")
        np.random.default_rng(seed).shuffle(groups)
        cuts = [int(len(groups)*.60), int(len(groups)*.75), int(len(groups)*.85)]
        assignment = {g:name for name,chunk in zip(names,np.split(groups,cuts)) for g in chunk}
        result["split"] = result.lake_id.astype(str).map(assignment)
    elif mode == "chronological":
        ts = pd.to_datetime(result.assessed_at, utc=True)
        times = np.array(sorted(ts.unique()))
        if len(times) < 8: raise ValueError("Not enough distinct clocks for chronological splitting")
        cuts = [times[int(len(times)*fraction)] for fraction in (.60,.75,.85)]
        result["split"] = np.select([ts<cuts[0],ts<cuts[1],ts<cuts[2]],names[:3],default="test")
        keep = np.ones(len(result),dtype=bool)
        for name,boundary in zip(names[:3],cuts):
            keep &= ~((result.split == name) & (ts + pd.Timedelta(hours=72) >= boundary))
        print("Purged horizon-boundary rows:",int((~keep).sum()))
        result = result.loc[keep].copy()
    elif mode == "provided":
        if "split" not in result: raise ValueError("Supply a split column")
        if not result.split.isin(names).all(): raise ValueError("Unexpected split names")
    else:
        raise ValueError("Unknown SPLIT_MODE")
    if result.groupby("episode_id").split.nunique().max() > 1:
        raise ValueError("An episode crosses splits; assign whole event/control episodes together")
    if mode != "chronological" and result.groupby("lake_id").split.nunique().max() > 1:
        raise ValueError("Lake leakage across splits")
    for name in names:
        subset = result[result.split == name]
        if set(subset.target_id) != {0,1,2}:
            raise ValueError(f"{name} lacks a target class; collect more independent episodes")
    return result.reset_index(drop=True)


def feature_prompt(row):
    features = {}
    for name in FEATURE_COLUMNS:
        value = row.get(name)
        if name == "possible_ice_cover":
            features[name] = bool_value(value)
        else:
            try: number = float(value)
            except (TypeError,ValueError): number = np.nan
            features[name] = round(number,4) if np.isfinite(number) else None
    return ("Glacial lake measurements available now. Predict the FIRST new outburst onset in "
        "the next 72 hours. Units: area km2, change percent, rain mm, temperature C, age days, "
        "distance km. Null=unknown. Optical and SAR use separate baselines. Shrinkage may be "
        "seasonal or past drainage; future onset is a different target.\nFEATURES=" + canonical(features) +
        "\nDECISION FEATURES:")


def softmax_np(logits,temperature=1.0):
    scores = np.asarray(logits,dtype=np.float64) / float(temperature)
    scores -= scores.max(axis=1,keepdims=True)
    ex = np.exp(scores)
    return ex/ex.sum(axis=1,keepdims=True)


def fit_temperature(logits,labels):
    candidates = np.geomspace(.2,5.0,161)
    losses = [log_loss(labels,softmax_np(logits,t),labels=[0,1,2]) for t in candidates]
    best = int(np.argmin(losses))
    return float(candidates[best]),float(losses[best])


def monitor_to_training_rows(results,cycle_clock):
    at = utc(cycle_clock)
    rows = []
    for lake,res in results:
        m = res.get("metrics",{})
        row = {key:m.get(key) for key in FEATURE_COLUMNS}
        for source,target in [("optical_time","optical_age_days"),("sar_time","sar_age_days")]:
            value = m.get(source)
            row[target] = None if value is None else (at-utc(value)).total_seconds()/86400
        row.update(sample_id=f"{lake['lake_id']}__{at.strftime('%Y%m%dT%H%M%SZ')}",
            lake_id=str(lake["lake_id"]),episode_id=None,assessed_at=at.isoformat(),
            features_available_at=at.isoformat(),event_start_utc=None,label_verified_until_utc=None,
            label_status="UNVERIFIED",label_source=None,is_synthetic=False,event_class=None)
        rows.append(clean(row))
    return rows


def measurement_gate(row,now):
    warnings = []
    try:
        at = utc(row.get("assessed_at"))
        available = utc(row.get("features_available_at"))
    except (ValueError, TypeError):
        return ["Missing or invalid assessment/availability timestamp"]
    if available > at:
        warnings.append("Features are future-dated")
    age_h = (utc(now)-at).total_seconds()/3600
    if age_h < 0 or age_h > 12: warnings.append("Assessment missing the current 12-hour freshness window")
    if row.get("features_available_at") is not None and pd.notna(row.get("features_available_at")):
        if utc(row["features_available_at"]) > at: warnings.append("Features are future-dated")
    def num(key):
        try: x = float(row.get(key)); return x if np.isfinite(x) else None
        except (ValueError,TypeError): return None
    oa,sa = num("optical_age_days"),num("sar_age_days")
    coverage,n = num("footprint_valid_frac"),num("n_history")
    opt_ok = (oa is not None and 0<=oa<=15 and coverage is not None and 0.8<=coverage<=1.0 and
        n is not None and n>=3 and (num("baseline_km2") or 0)>0 and num("pct_vs_baseline") is not None)
    sar_ok = (sa is not None and 0<=sa<=12 and (num("sar_n_baseline") or 0)>=3 and
        num("sar_pct_change") is not None and num("sar_z") is not None)
    if not opt_ok and not sar_ok: warnings.append("No usable recent lake-change measurement")
    return warnings