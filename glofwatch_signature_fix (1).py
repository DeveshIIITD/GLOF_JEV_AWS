"""Apply inside your already loaded GLOFWatch notebook:
exec(Path("glofwatch_signature_fix.py").read_text(), globals())
lakes = configure(cfg)

This file only replaces function definitions. It preserves your current cfg
and does not delete databases, signatures, registry snapshots, or image files.
"""


def build_registry(force=False):
    if REGISTRY_PATH.exists() and not force:
        reg_df = pd.read_csv(REGISTRY_PATH, float_precision="round_trip")
        print(f"Loaded cached registry: {len(reg_df)} lakes  ({REGISTRY_PATH})")
        return reg_df
    now = datetime.now(timezone.utc)
    season_year = DISCOVERY_SEASON_YEAR
    print("Baseline season for candidate detection:", season_year)
    rows = []
    for rname in ACTIVE_REGIONS:
        x0, y0, x1, y1 = REGIONS[rname]
        cands = []
        for x in np.arange(x0, x1, TILE_DEG):
            for y in np.arange(y0, y1, TILE_DEG):
                tile = (float(x), float(y), float(min(x + TILE_DEG, x1)), float(min(y + TILE_DEG, y1)))
                try:
                    found = detect_candidates(tile, season_year)
                    cands += found
                    print(f"  {rname} tile {tile[0]:.1f},{tile[1]:.1f}: {len(found)} candidates")
                except Exception as e:
                    print(f"  {rname} tile {tile[:2]} failed: {e!r}")
        clusters = cluster_candidates(cands)
        print(f"{rname}: {len(cands)} polygons -> {len(clusters)} lake clusters")
        for c in clusters:
            lid = "HKH_" + hashlib.sha1(f"{c['lat']:.4f}_{c['lon']:.4f}".encode()).hexdigest()[:8]
            rows.append({"lake_id": lid, "name": f"{rname} lake {lid[-4:]}", "lat": c["lat"], "lon": c["lon"],
                         "region": rname, "area_km2": c["area_km2"], "source": "auto",
                         "footprint_geojson": json.dumps(mapping(c["footprint"].simplify(2e-5)))})
    auto = pd.DataFrame(rows, columns=["lake_id","name","lat","lon","region","area_km2","source","footprint_geojson"])

    seeds = SEEDS_ALL[SEEDS_ALL.region.isin(ACTIVE_REGIONS)] if USE_SEED_LAKES else SEEDS_ALL.iloc[0:0]
    if len(auto) and len(seeds):  # drop auto lakes that duplicate a seed
        keep = []
        for _, a in auto.iterrows():
            d = haversine_km_vec(a.lat, a.lon, seeds.lat.values, seeds.lon.values)
            keep.append(bool((d > CLUSTER_KM).all()))
        auto = auto[keep]
    auto = auto.sort_values("area_km2", ascending=False).head(max(0, MAX_LAKES - len(seeds)))

    reg_df = pd.concat([seeds, auto], ignore_index=True)
    reg_df.to_csv(REGISTRY_PATH, index=False)
    print(f"Registry saved: {len(reg_df)} lakes ({len(seeds)} seeds + {len(auto)} auto)")
    return reg_df

REGISTRY_SIGNATURE_KEYS = {"registry_sha256", "registry_measurements", "signature_version"}

def registry_measurements(registry):
    mapping_by_lake = {}
    for row in registry.to_dict("records"):
        footprint = row.get("footprint_geojson")
        footprint = json.loads(footprint) if isinstance(footprint,str) and footprint.strip() else None
        mapping_by_lake[str(row["lake_id"])] = {
            "lat":float(row["lat"]), "lon":float(row["lon"]), "footprint_geojson":footprint,
        }
    return mapping_by_lake

def validate_measurement_signature(path, current, saved_registry_path, adopt_unversioned_db=False):
    path = Path(path)
    if not path.exists():
        if DB_PATH.exists() and not adopt_unversioned_db:
            raise ValueError("Selected DB has no signature. Adopt only measurements made with compatible settings")
        atomic_json(path,current)
        return
    previous = json.loads(path.read_text())
    changes = {key:{"saved":previous.get(key,"<missing>"), "current":current.get(key,"<missing>")}
               for key in sorted(set(previous)|set(current))
               if key not in REGISTRY_SIGNATURE_KEYS and previous.get(key,"<missing>") != current.get(key,"<missing>")}
    if changes:
        print("Changed measurement settings:",json.dumps(changes,indent=2))
        raise ValueError("Changed measurement settings: " + ", ".join(changes) +
                         ". Restore those settings or use a separate work directory.")
    old_lakes = previous.get("registry_measurements")
    if old_lakes is None:
        # Recover the old registry only when its exact full fingerprint proves its identity.
        saved_registry_path = Path(saved_registry_path)
        if saved_registry_path.exists():
            saved = pd.read_csv(saved_registry_path,float_precision="round_trip")
            saved_hash = hashlib.sha256(canonical(saved.to_dict("records")).encode()).hexdigest()
            if saved_hash == previous.get("registry_sha256"):
                old_lakes = registry_measurements(saved)
        if old_lakes is None and previous.get("registry_sha256") == current["registry_sha256"]:
            old_lakes = current["registry_measurements"]
        if old_lakes is None:
            print("Saved registry hash:",previous.get("registry_sha256"))
            print("Current registry hash:",current["registry_sha256"])
            raise ValueError("Cannot verify the previous registry for this legacy database. "
                             "Restore its saved lake_registry.csv or use a separate work directory.")
    new_lakes = current["registry_measurements"]
    changed_lakes = []
    for lake_id in old_lakes.keys() & new_lakes.keys():
        before, after = old_lakes[lake_id],new_lakes[lake_id]
        same_location = (abs(before["lat"]-after["lat"]) <= 1e-10 and
                         abs(before["lon"]-after["lon"]) <= 1e-10)
        same_footprint = canonical(before["footprint_geojson"]) == canonical(after["footprint_geojson"])
        if not same_location or not same_footprint:
            changed_lakes.append(lake_id)
    if changed_lakes:
        raise ValueError("Coordinates or footprints changed for: " + ", ".join(sorted(changed_lakes)) +
                         ". Restore the registry or use a separate work directory.")
    # Retain omitted lakes too, so later re-adding them cannot bypass a geometry check.
    retained = dict(old_lakes)
    retained.update({key:value for key,value in new_lakes.items() if key not in retained})
    current["registry_measurements"] = retained
    if previous != current:
        atomic_json(path,current)

def initialize_earth_engine(cfg, interactive=False):
    if not cfg.gee_project:
        raise ValueError("Set GEE_PROJECT to your registered Earth Engine project")
    key = os.getenv("GEE_SERVICE_ACCOUNT_FILE") or os.getenv("GEE_SEVRICE_ACCOUNT_FILE")
    if key:
        key_data = json.loads(Path(key).read_text())
        credentials = ee.ServiceAccountCredentials(key_data["client_email"], key)
        ee.Initialize(credentials=credentials, project=cfg.gee_project)
    else:
        try:
            ee.Initialize(project=cfg.gee_project)
        except Exception:
            if not interactive:
                raise RuntimeError("Run the authentication cell or set GEE_SERVICE_ACCOUNT_FILE") from None
            ee.Authenticate(auth_mode="notebook")
            ee.Initialize(project=cfg.gee_project)

def configure(cfg, load_weights=True):
    global BASE_DIR, QUICK_DIR, DB_PATH, REGISTRY_PATH, model, lakes_active
    global SEGMENTATION_THRESHOLD, DOWNLOAD_BUDGET, BACKFILL_DAYS, _loaded_model_sha
    BASE_DIR = Path(cfg.work_path).expanduser().resolve()
    QUICK_DIR = BASE_DIR / "quicklooks"
    DB_PATH = Path(cfg.db_path).expanduser().resolve()
    REGISTRY_PATH = BASE_DIR / "lake_registry.csv"
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    QUICK_DIR.mkdir(exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_BUDGET, BACKFILL_DAYS = int(cfg.download_budget), int(cfg.backfill_days)
    if DOWNLOAD_BUDGET <= 0 or BACKFILL_DAYS <= 0:
        raise ValueError("download_budget and backfill_days must be positive")
    SEGMENTATION_THRESHOLD = float(cfg.segmentation_threshold)
    model_sha = sha256_file(cfg.deeplab_path)
    sidecar = Path(cfg.deeplab_path).with_suffix(".metadata.json")
    if sidecar.exists():
        metadata = json.loads(sidecar.read_text())
        if metadata.get("model_sha256") != model_sha:
            raise ValueError("DeepLab metadata belongs to different weights")
        SEGMENTATION_THRESHOLD = float(metadata["threshold"])
    if not 0 < SEGMENTATION_THRESHOLD < 1:
        raise ValueError("The segmentation threshold must be between zero and one")
    if load_weights and (model is None or globals().get("_loaded_model_sha") != model_sha):
        configure_gpu()
        model = load_segmentation(cfg.deeplab_path)
        _loaded_model_sha = model_sha

    mode = cfg.get("registry_mode", "seeds")
    if mode == "csv":
        registry = pd.read_csv(Path(cfg.registry_path), float_precision="round_trip")
    elif mode == "discover":
        REGISTRY_PATH = BASE_DIR / "discovered_lake_registry.csv"
        registry = build_registry(force=False)
    elif mode == "seeds":
        registry = SEEDS_ALL.copy()
    else:
        raise ValueError("registry_mode must be seeds, csv or discover")
    required = {"lake_id", "name", "lat", "lon", "region"}
    if not required.issubset(registry.columns) or registry.lake_id.duplicated().any():
        raise ValueError("Registry requires unique lake_id, name, lat, lon, region")
    ids = cfg.get("active_lake_ids", ())
    if ids:
        registry = registry[registry.lake_id.isin(ids)]
        if set(registry.lake_id) != set(ids):
            raise ValueError("An active_lake_id is absent from the registry")
    registry = registry.head(int(cfg.get("max_lakes", MAX_LAKES))).copy()
    if registry.empty or not registry.lat.between(-90,90).all() or not registry.lon.between(-180,180).all():
        raise ValueError("Registry is empty or has invalid coordinates")

    signature = json.loads(canonical({
        "model_sha256": model_sha, "threshold": SEGMENTATION_THRESHOLD,
        "bands": MODEL_BANDS, "input_mode": INPUT_MODE,
        "chip_m": CHIP_M, "pixel_m": PIXEL_M,
        "footprint_buffer_m": FOOTPRINT_BUFFER_M, "seed_radius_m": SEED_RADIUS_M,
        "bad_scl": list(BAD_SCL), "min_footprint_valid": MIN_FOOTPRINT_VALID,
        "registry_sha256": hashlib.sha256(canonical(registry.to_dict("records")).encode()).hexdigest(),
        "registry_measurements":registry_measurements(registry), "signature_version":2,
        "baseline_days": D.BASELINE_DAYS, "min_history": D.MIN_HISTORY,
        "sar_window_days": SAR_WINDOW_DAYS, "sar_water_db": SAR_WATER_DB,
        "sar_min_cover": SAR_MIN_COVER, "sar_min_baseline": SAR_MIN_BASELINE_IMAGES,
        "sar_min_rel_sigma": SAR_MIN_REL_SIGMA,
    }))
    signature_path = DB_PATH.with_name(DB_PATH.name + ".measurement_signature.json")
    validate_measurement_signature(signature_path, signature, BASE_DIR/"lake_registry.csv",
                                   cfg.get("adopt_unversioned_db",False))
    lakes_active = registry.to_dict("records")
    write_csv_atomic(registry, BASE_DIR / "lake_registry.csv")
    init_db()
    return lakes_active

def save_cycle(cfg, results, clock, histories=None, ingest_stats=None):
    rows = monitor_to_training_rows(results, clock)
    for row in rows:
        row.update(sampling_mode="live", feature_availability_policy="RECORDED_LIVE",
                   input_usable=not measurement_gate(row, clock))
    work = Path(cfg.work_path)
    history_path = work / "training_features_history_UNVERIFIED.csv"
    draft_path = work / "training_labels_UNVERIFIED.csv"
    # Import a previous latest batch once before replacing it.
    if draft_path.exists():
        previous = pd.read_csv(draft_path)
        if not previous.empty and "sample_id" in previous:
            for record in previous.to_dict("records"):
                record.setdefault("sampling_mode", "live")
                record.setdefault("feature_availability_policy", "RECORDED_LIVE")
                record["input_usable"] = not measurement_gate(record, record["assessed_at"])
                if bool_value(record.get("is_synthetic")) is not True:
                    accumulate_rows([record], history_path)
    accumulate_rows(rows, history_path)
    write_csv_atomic(pd.DataFrame(rows), draft_path)
    features_path = Path(cfg.features_path)
    tmp = features_path.with_name(features_path.name + ".tmp")
    tmp.write_text("".join(canonical(row)+"\n" for row in rows))
    tmp.replace(features_path)
    level_risk = {"GREEN":"low", "YELLOW":"watch", "ORANGE":"high", "RED":"high"}
    lakes = []
    for (lake, result), row in zip(results, rows):
        metrics = result.get("metrics", {})
        warnings = measurement_gate(row, clock)
        lakes.append(clean({
            "lake_id": lake["lake_id"], "name": lake["name"], "region": lake.get("region"),
            "lat": lake["lat"], "lon": lake["lon"], "level": result["level"],
            "risk": "unknown" if warnings else level_risk[result["level"]],
            "score": result["score"], "score_kind":"ANOMALY_POINTS",
            "area_km2": metrics.get("area_km2"), "area_change_pct":metrics.get("pct_vs_baseline"),
            "assessed_at":row["assessed_at"], "features_available_at":row["features_available_at"],
            "optical_time":metrics.get("optical_time"), "sar_time":metrics.get("sar_time"),
            "history":(histories or {}).get(lake["lake_id"], []), "reasons":result["reasons"],
            "data_quality":"INSUFFICIENT_DATA" if warnings else "RECENT_CHANGE_MEASUREMENTS",
            "warnings":warnings, "metrics":metrics, "qwen":None, "observations_synthetic":False,
        }))
    snapshot = {"schema_version":"glofwatch-v1", "generated_at":utc(clock).isoformat(),
                "observation_mode":"LIVE_MEASUREMENTS", "qwen_status":"NOT_RUN",
                "ingest_stats":ingest_stats or {}, "lakes":lakes, "count":len(lakes)}
    atomic_json(cfg.latest_path, snapshot)
    atomic_json(work/"snapshots"/(utc(clock).strftime("%Y%m%dT%H%M%S%fZ")+".json"), snapshot)
    return snapshot

def collect(cfg, interactive=False):
    initialize_earth_engine(cfg, interactive=interactive)
    lakes = configure(cfg)
    stats = ingest_cycle(lakes, datetime.now(timezone.utc))
    results = assess_cycle(lakes, datetime.now(timezone.utc), send_notifications=False)
    completed_at = datetime.now(timezone.utc)
    histories = {}
    for lake in lakes:
        table = q("SELECT scene_time, lake_area_km2 FROM observations WHERE lake_id=? AND reliable=1 ORDER BY scene_time", (lake["lake_id"],))
        histories[lake["lake_id"]] = [{"date":r.scene_time, "area_km2":r.lake_area_km2} for r in table.itertuples()]
    snapshot = save_cycle(cfg, results, completed_at, histories, stats)
    return stats, results, snapshot

def load_historical_context(path):
    if path is None:
        return {}
    frame = pd.read_csv(path)
    required = {"lake_id", "context_at", "available_at"}
    if not required.issubset(frame.columns):
        raise ValueError("Historical context needs lake_id, context_at, available_at")
    frame["context_at"] = pd.to_datetime(frame.context_at, utc=True, errors="raise")
    frame["available_at"] = pd.to_datetime(frame.available_at, utc=True, errors="raise")
    if frame[["context_at", "available_at"]].isna().any().any():
        raise ValueError("Historical context timestamps cannot be missing")
    if (frame.available_at > frame.context_at).any():
        raise ValueError("Historical context contains information unavailable at its assessment clock")
    if frame.duplicated(["lake_id", "context_at"]).any():
        raise ValueError("Duplicate historical context lake/clock")
    allowed = [name for name in FEATURE_COLUMNS if name.startswith(("wx_", "eq_")) or name == "gpm_rain_24h_mm"]
    return {(str(row["lake_id"]), utc(row["context_at"]).isoformat()):
            {name:clean(row.get(name)) for name in allowed} for row in frame.to_dict("records")}

def historical_clock_rows(lakes, clock, context):
    clock = utc(clock)
    optical_cutoff = clock - pd.Timedelta(hours=S2_AVAILABILITY_LAG_HOURS)
    sar_cutoff = clock - pd.Timedelta(hours=S1_AVAILABILITY_LAG_HOURS)
    def sar_job(lake):
        try:
            result = sar_check(lake, sar_cutoff)
            if result.get("available") and (clock-utc(result["s1_time"])).total_seconds()/86400 > 12:
                return {"available":False, "reason":"SAR too old at the assessment clock"}
            return result
        except Exception as error:
            return {"available":False, "error":repr(error)}
    with ThreadPoolExecutor(EE_WORKERS) as pool:
        sars = list(pool.map(sar_job, lakes))
    rows = []
    for lake, sar in zip(lakes, sars):
        obs = latest_reliable_obs(lake["lake_id"], optical_cutoff)
        if obs and (clock-utc(obs["scene_time"])).total_seconds()/86400 > D.RECENT_OPTICAL_DAYS:
            obs = None
        hist = reliable_history(lake["lake_id"], obs["scene_time"]) if obs else pd.DataFrame()
        result = assess(obs, hist, sar, {}, clock)
        result["metrics"].update(context.get((str(lake["lake_id"]), clock.isoformat()), {}))
        row = monitor_to_training_rows([(lake, result)], clock)[0]
        row.update(sample_id=f"HIST__{lake['lake_id']}__{clock.strftime('%Y%m%dT%H%M%SZ')}",
                   sampling_mode="historical", feature_availability_policy="ASSUMED_SATELLITE_LAGS",
                   optical_time=result["metrics"].get("optical_time"),
                   sar_time=result["metrics"].get("sar_time"),
                   s2_availability_lag_hours=S2_AVAILABILITY_LAG_HOURS,
                   s1_availability_lag_hours=S1_AVAILABILITY_LAG_HOURS,
                   input_usable=not measurement_gate(row, clock))
        rows.append(row)
    return rows

def build_historical_candidates(cfg):
    global BACKFILL_DAYS, SAVE_QUICKLOOKS
    start, end = utc(HIST_START), utc(HIST_END)
    if end < start or end > utc(datetime.now(timezone.utc)):
        raise ValueError("Historical dates must be ordered and in the past")
    if HIST_STEP_HOURS <= 0 or MAX_HISTORICAL_CLOCKS_PER_RUN <= 0 or HIST_WARMUP_DAYS < D.BASELINE_DAYS:
        raise ValueError("Positive sampling controls and warmup >= baseline_days are required")
    if S2_AVAILABILITY_LAG_HOURS < 0 or S1_AVAILABILITY_LAG_HOURS < 0:
        raise ValueError("Availability lag cannot be negative")
    clocks = pd.date_range(start, end, freq=pd.Timedelta(hours=HIST_STEP_HOURS))
    work = Path(HIST_WORK_DIR)
    work.mkdir(parents=True, exist_ok=True)
    hist_cfg = MapDict(cfg.copy())
    hist_cfg.update(work_path=work, db_path=work/"historical_monitor.sqlite", adopt_unversioned_db=False)
    # Freeze the selected registry; historical configure cannot trigger fresh discovery.
    frozen = Path(cfg.work_path)/"lake_registry.csv"
    hist_cfg.update(registry_mode="csv", registry_path=frozen)
    # Include padding for a stale latest optical scene and assumed product latency.
    padding = D.RECENT_OPTICAL_DAYS + int(np.ceil(max(S2_AVAILABILITY_LAG_HOURS, S1_AVAILABILITY_LAG_HOURS)/24))
    hist_cfg["backfill_days"] = int(np.ceil((end-start).total_seconds()/86400)) + HIST_WARMUP_DAYS + padding + 1
    path = work/"historical_training_UNVERIFIED.csv"
    old_quicklooks = SAVE_QUICKLOOKS
    try:
        SAVE_QUICKLOOKS = False
        lakes = configure(hist_cfg)
        profile = {"s2_lag_hours":S2_AVAILABILITY_LAG_HOURS, "s1_lag_hours":S1_AVAILABILITY_LAG_HOURS,
                   "context_sha256":sha256_file(HIST_CONTEXT_CSV) if HIST_CONTEXT_CSV else None,
                   "measurement_signature":json.loads(DB_PATH.with_name(DB_PATH.name+".measurement_signature.json").read_text())}
        profile_path = work/"dataset_profile.json"
        if profile_path.exists():
            previous_profile = json.loads(profile_path.read_text())
            before = {key:value for key,value in previous_profile.items() if key!="measurement_signature"}
            after = {key:value for key,value in profile.items() if key!="measurement_signature"}
            old_settings = {key:value for key,value in previous_profile.get("measurement_signature",{}).items()
                            if key not in REGISTRY_SIGNATURE_KEYS}
            new_settings = {key:value for key,value in profile["measurement_signature"].items()
                            if key not in REGISTRY_SIGNATURE_KEYS}
            if before != after or old_settings != new_settings:
                raise ValueError("Historical feature profile changed. Use a new historical work directory")
        atomic_json(profile_path, profile)
        stats = None
        for pass_number in range(MAX_BACKFILL_PASSES):
            stats = ingest_cycle(lakes, end)
            print("Historical backfill", pass_number+1, stats)
            if stats["backlog"] == 0 and stats.get("listing_failed",0) == 0:
                break
        if stats["backlog"] or stats.get("listing_failed",0):
            print("Historical imagery incomplete; rerun this cell before assessment sampling.")
            return {"status":"BACKFILL_PENDING", "path":str(path), "stats":stats}
        context = load_historical_context(HIST_CONTEXT_CSV)
        existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
        done = set(existing.sample_id) if not existing.empty else set()
        processed = 0
        for clock in clocks:
            pending_lakes = [lake for lake in lakes if f"HIST__{lake['lake_id']}__{clock.strftime('%Y%m%dT%H%M%SZ')}" not in done]
            if not pending_lakes:
                continue
            if processed >= MAX_HISTORICAL_CLOCKS_PER_RUN:
                break
            rows = historical_clock_rows(pending_lakes, clock, context)
            accumulate_rows(rows, path)
            done.update(row["sample_id"] for row in rows)
            processed += 1
            print(f"Checkpoint {clock.isoformat()}: saved {len(rows)} candidate rows")
        total = len(lakes)*len(clocks)
        finished = sum(f"HIST__{lake['lake_id']}__{clock.strftime('%Y%m%dT%H%M%SZ')}" in done for clock in clocks for lake in lakes)
        status = "COMPLETE" if finished == total else "SAMPLING_PENDING"
        print(f"Historical candidates: {finished}/{total}; {status}; {path}")
        return {"status":status, "path":str(path), "completed":finished, "planned":total}
    finally:
        SAVE_QUICKLOOKS = old_quicklooks
        configure(cfg)                       # restore live DB and globals even after an error
