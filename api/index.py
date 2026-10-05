import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# CORS: kisi bhi origin se POST allow
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


# Crash hone par bhi CORS headers jayein
@app.exception_handler(Exception)
async def all_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},
        headers=CORS_HEADERS,
    )


# Telemetry data load
DATA_FILE = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
with open(DATA_FILE, "r", encoding="utf-8") as f:
    telemetry = json.load(f)

# Agar list kisi object ke andar wrapped hai to bahar nikaalo
if isinstance(telemetry, dict):
    telemetry = next(v for v in telemetry.values() if isinstance(v, list))


def percentile(values, p):
    values = sorted(values)
    if not values:
        return 0
    position = (len(values) - 1) * p / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def compute(body: dict):
    regions = body.get("regions", [])
    threshold = float(body.get("threshold_ms", 0))
    result = {}

    for region in regions:
        records = [r for r in telemetry if r["region"] == region]
        if not records:
            continue

        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for x in latencies if x > threshold),
        }
    return result


# Teeno URL par kaam karega: /, /api, /api/latency
@app.post("/")
@app.post("/api")
@app.post("/api/latency")
async def get_metrics(request: Request):
    body = await request.json()
    return compute(body)