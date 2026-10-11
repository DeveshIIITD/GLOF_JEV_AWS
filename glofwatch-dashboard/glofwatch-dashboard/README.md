# GLOFWatch — Himalayan GLOF Monitor Dashboard

A responsive, interactive front end for a **research** glacial-lake monitoring prototype. Built using plain **HTML, CSS, and JavaScript** so it runs without npm, a build system, or a paid cloud account.

> **Safety:** This is NOT an operational flood warning system. All built-in lake locations, metrics, and risk levels are **simulated demo data**. The example segmentation graphic is an illustration, not evidence. Do not represent modeled indicators as validated GLOF predictions.

## Included features

- Twelve fictional demo lake observations, with risk-level filtering and search
- Interactive Leaflet map with **Regular / Satellite** buttons above the map (schematic fallback when offline)
- Risk watchlist, responsive KPI cards, 7/30/90-day time-series chart with tooltips
- Selected-lake detail view, refresh button, CSV download
- AWS API Gateway integration, with explicit error fallback to simulated data
- Example Python AWS Lambda reading assessments from private Amazon S3
- Static AWS Amplify Hosting deployment configuration

## Separate animated schematic page

Open `schematic.html`, or select **Schematic** under **Data & system** in the **MAIN** navigation. This is a separate HTML page. The dashboard does not append the architecture at the bottom.

- Eleven locally bundled animated GIF icons illustrate satellite inputs, sensors, weather, aggregation, segmentation, judging, routing, monitoring, review, escalation and AWS serving.
- **Pause GIFs / Play GIFs** switches between animated GIFs and matching PNGs. Reduced-motion preferences pause animations by default.
- The diagram uses responsive grid cards and connectors in their gaps. Narrow layouts stack the pipeline vertically; content can scroll vertically without a fixed-height canvas.
- `schematic.html`, `schematic.css`, `schematic.js` and `assets/` are included in the Amplify build.
- Sensor ingestion, JEV / Qwen judging and SNS delivery are proposed integrations. The diagram does not run those services or trigger warnings.

To regenerate the original diagram icons, install Pillow and run `python tools/generate_schematic_assets.py` from any folder. The GIFs and static alternatives already ship in `assets/schematic/`.

Validation for this revision: JavaScript syntax, relative file links, dashboard return links, fragment targets, navigation order, unique IDs and every GIF/PNG asset were checked. Browser layout verification was unavailable in this session; review `schematic.html` on your target screen before presenting it.

## Regular and Satellite map views

Use the **Regular / Satellite** buttons above the lake map. Regular displays OpenStreetMap roads and place names; Satellite displays Esri World Imagery. Switching only replaces the background layer, keeping markers, popups, selected lake, zoom and position. The choice is remembered in this browser when local storage is available and retained during data refreshes.

Both map views require internet access. The buttons are disabled when Leaflet cannot load or no valid lake coordinates are available. Tile loading failures show a message beside the controls. Satellite imagery is a basemap with varying acquisition dates; it is not live satellite imagery or your model output.

Provider references: [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/), [Esri World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9), [Leaflet layer API](https://leafletjs.com/reference.html#tilelayer).

## Run locally

**Option 1 — Double-click `index.html`.** The demonstration dashboard renders without a web server. The interactive Leaflet map and custom fonts need internet access; otherwise the schematic map remains usable.

**Option 2 — Start a local server** (recommended before connecting a live API):

```bash
cd glofwatch-dashboard
python -m http.server 8000
```

Then open http://localhost:8000.

No `npm install` is required.

## Connect your Colab results to AWS

Suggested data flow:

```text
Colab model inference / monitoring notebook
  → JSON export
  → private S3 bucket: processed/latest.json
  → Python AWS Lambda GET handler
  → API Gateway HTTP API: GET /lakes/latest
  → GLOFWatch browser dashboard
```

1. Export your notebook results to a JSON array. Each row may contain `lake_id`, `level`, `score`, `assessed_at`, and `metrics` (or `metrics_json`). The UI recognizes numeric `area_km2`, `area_change_pct`, `lat`, and `lon` when present. It displays unavailable values as `—`; it does **not** invent missing coordinates or history for real data.
2. Upload the JSON object to a **private** S3 bucket using Colab with least-privilege IAM permissions. Never put cloud credentials in frontend code or Git.
3. Create a Python Lambda function with the content of [`aws/lambda_function.py`](aws/lambda_function.py). Set its environment variables `S3_BUCKET`, `S3_OBJECT_KEY=processed/latest.json`, and `ALLOWED_ORIGIN` (the exact browser origin, without trailing slash). Its execution role needs `s3:GetObject` on that object. Set an appropriate timeout, logs, and throttling.
4. Expose that Lambda through API Gateway HTTP API using the route `GET /lakes/latest`. Configure **CORS on API Gateway** for your dashboard origin with `GET`, `OPTIONS`, and `Content-Type` as appropriate. API Gateway's HTTP API CORS configuration can override CORS headers in the Lambda response.
5. In [`config.js`](config.js), set your public API base URL:

```js
window.GLOF_API_URL = 'https://your-id.execute-api.ap-south-1.amazonaws.com';
```

The browser requests `GET {GLOF_API_URL}/lakes/latest`. Alternatively you can set this URL including `/lakes/latest` and it won't be appended twice.

**Never put an AWS access key, secret, S3 signed URL with private data, or IAM credentials in `config.js`.** This dashboard expects a public read-only API or an API with an independently implemented appropriate authentication flow. AWS resources may incur charges.

### API example

See [`data/example-api-response.json`](data/example-api-response.json):

```json
{
  "lakes": [{
    "lake_id": "EXAMPLE-01",
    "name": "Example Research Lake",
    "region": "Demo study area",
    "lat": 28.1,
    "lon": 85.2,
    "level": "watch",
    "score": 51,
    "area_km2": 0.75,
    "area_change_pct": 1.7,
    "assessed_at": "2026-10-08T08:00:00Z",
    "history": [
      {"date":"2026-10-06","area_km2":0.73},
      {"date":"2026-10-07","area_km2":0.74}
    ]
  }]
}
```

The API may instead return a plain array, `{ "results": [...] }`, or `{ "items": [...] }`. For compatibility with the earlier notebook export, each object can contain:

```json
{
  "lake_id": "EXAMPLE-01",
  "level": "watch",
  "score": 51,
  "assessed_at": "2026-10-08T08:00:00Z",
  "metrics_json": "{\"area_km2\":0.75,\"area_change_pct\":1.7,\"lat\":28.1,\"lon\":85.2}"
}
```

Risk categories can be passed as `high`, `watch`, `low`; other common synonyms are normalized. When level is absent but score is provided, the *UI demo convention* uses `>=70` for `high` and `>=40` for `watch`. **These are interface categories, not a scientifically validated GLOF risk scale.**

## Deploy to AWS Amplify Hosting

1. Push this folder to GitHub (e.g. as its own repository, or update the build paths if it is a subfolder in a larger repository).
2. Open AWS Amplify → **Deploy an app** → GitHub → select your repository and branch.
3. The included `amplify.yml` copies only the static site into `dist/`.
4. Optional: in Amplify hosting environment variables, set `GLOF_API_URL` to your **public API base URL**. The build writes that URL to `dist/config.js` as a JavaScript string. Do not place secrets in hosting environment variables destined for client-side code.
5. Once deployed, update `ALLOWED_ORIGIN` in Lambda and CORS in API Gateway to match your HTTPS Amplify URL.
6. Verify the frontend and API work end to end, including the browser developer console for CORS errors.

For deployments using GitHub Pages or S3 static hosting, keep `config.js` in the site root with the appropriate public endpoint.

## File layout

```text
glofwatch-dashboard/
├── index.html                 # Dashboard page
├── schematic.html             # Separate animated architecture page
├── schematic.css              # Responsive diagram grids and connectors
├── schematic.js               # Animation toggle and page navigation
├── assets/schematic/          # Local animated GIFs and static PNGs
├── styles.css                 # Responsive styles
├── app.js                     # App state, UI, map and chart logic
├── config.js                  # Public API endpoint configuration
├── aws/
│   └── lambda_function.py     # Example S3-backed Lambda
├── data/
│   └── example-api-response.json
├── amplify.yml                # Static Amplify Hosting build
└── README.md
```

## Technical notes

- Leaflet 1.9.4 loads dynamically via the unpkg CDN; regular tiles come from OpenStreetMap and satellite tiles from Esri World Imagery. Keep provider attribution visible and use a suitably licensed provider endpoint for your deployment. Follow OpenStreetMap tile usage policies and attribution requirements for deployed apps. For sustained public traffic, choose a suitable map tile provider.
- If Leaflet is unavailable, an explicitly labeled **schematic** background appears. Its fallback locator positions are illustrative only.
- The dashboard does **not** automatically run satellite inference. Your Colab notebook must export fresh results, or inference must be scheduled on suitable infrastructure.
- If a live API response has no history array, the chart explains that time-series data is unavailable instead of fabricating observations.
- For production deployments, add authentication/authorization, API quotas, input validation, monitoring, and scientific review. Configure budgets for AWS usage.
- The 12 demo lake names and locations are not claims about real lakes or hazards.

## Hackathon note

Check the event's originality and prior-project reuse rules before presenting previously developed notebooks as newly created hackathon work. Preserve accurate commit history and attribution.
