# server.py — FastAPI + AIS ingest (Railway)
# Versão corrigida (sem erros de sintaxe) + /diag para troubleshooting
# Use com requirements: fastapi, uvicorn[standard], websockets>=11,<13

import os
import json
import asyncio
import random
from collections import deque, Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import websockets
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from geofences_from_kmz import GEOFENCES

# ------------------ Config ------------------ #
API_KEY = os.getenv("AISSTREAM_API_KEY", "349ff539f874179f9626af85ec372783f8256e08")
URL = "wss://stream.aisstream.io/v0/stream"
MMSI_LIST = [m.strip() for m in os.getenv("MMSI_LIST", "710025630,710000348,710014960,710015850").split(',') if m.strip()]
KPI_WINDOW_MIN = int(os.getenv("KPI_WINDOW_MIN", "15"))

# ------------------ Estado ------------------ #
recent_positions: deque = deque(maxlen=100000)   # {ts,mmsi,lat,lon,sog}
recent_msgs: deque = deque(maxlen=200000)        # (ts,mmsi)
recent_geofence_events: deque = deque(maxlen=10000)  # (ts,mmsi,geo,event)

diag: Dict[str, Any] = {
    "startup_called": False,
    "last_connect_attempt": None,
    "last_connected_ok": None,
    "last_error": None,
    "ws_active": False,
}

# ------------------ Geofence ------------------ #
def point_in_polygon(lat: float, lon: float, poly):
    """Ray casting; poly no formato [(lat, lon), ...]."""
    inside = False
    n = len(poly)
    if n < 3:
        return False
    for i in range(n):
        lat1, lon1 = poly[i]
        lat2, lon2 = poly[(i + 1) % n]
        if ((lon1 > lon) != (lon2 > lon)):
            latx = lat1 + (lat2 - lat1) * (lon - lon1) / (lon2 - lon1)
            if latx > lat:
                inside = not inside
    return inside

_geofence_state = defaultdict(dict)  # mmsi -> name -> bool

# ------------------ AIS Consumer ------------------ #
async def ais_consumer():
    if not API_KEY:
        diag["last_error"] = "AISSTREAM_API_KEY não definido"
        print("[AIS][ERRO] AISSTREAM_API_KEY não definido (configure no Railway > Variables)")
        return
    backoff = 1
    while True:
        try:
            diag["last_connect_attempt"] = datetime.now(timezone.utc).isoformat()
            print(f"[AIS] Tentando conectar... (MMSIs={len(MMSI_LIST)})")
            async with websockets.connect(
                URL,
                ping_interval=20,
                ping_timeout=20,
                max_queue=2000,
                max_size=2**22,
            ) as ws:
                sub = {
                    "APIKey": API_KEY,
                    "BoundingBoxes": [[[-90.0, -180.0], [90.0, 180.0]]],
                    "FilterMessageTypes": ["PositionReport"],
                    "FiltersShipMMSI": MMSI_LIST,
                }
                await ws.send(json.dumps(sub))
                diag["ws_active"] = True
                diag["last_connected_ok"] = datetime.now(timezone.utc).isoformat()
                diag["last_error"] = None
                print("[AIS] Conectado e assinando...")
                backoff = 1
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if msg.get("MessageType") != "PositionReport":
                            continue
                        pos = msg["Message"]["PositionReport"]
                        meta = msg["MetaData"]
                        ts = datetime.now(timezone.utc).isoformat()
                        mmsi = str(meta.get("MMSI"))
                        if mmsi not in MMSI_LIST:
                            continue
                        lat = float(pos.get("Latitude", 0.0))
                        lon = float(pos.get("Longitude", 0.0))
                        sog = float(pos.get("Sog", 0.0))
                        recent_msgs.append((ts, mmsi))
                        recent_positions.append({"ts": ts, "mmsi": mmsi, "lat": lat, "lon": lon, "sog": sog})
                        # geofence
                        for gf in GEOFENCES:
                            name = gf['name']
                            inside = point_in_polygon(lat, lon, gf['polygon'])
                            prev = _geofence_state[mmsi].get(name)
                            if prev is None:
                                _geofence_state[mmsi][name] = inside
                                continue
                            if inside != prev:
                                _geofence_state[mmsi][name] = inside
                                event = 'ENTER' if inside else 'EXIT'
                                recent_geofence_events.append((ts, mmsi, name, event))
                    except Exception as e:
                        diag["last_error"] = f"Process msg: {e.__class__.__name__}: {e}"
        except Exception as e:
            diag["last_error"] = f"Conexão: {e.__class__.__name__}: {e}"
            print(f"[AIS][ERRO] {e.__class__.__name__}: {e}")
        finally:
            diag["ws_active"] = False
        await asyncio.sleep(backoff + random.uniform(0, 0.5))
        backoff = min(backoff * 2, 30)

# ------------------ KPIs ------------------ #

def compute_kpis() -> Dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=KPI_WINDOW_MIN)
    msgs = [(ts, m) for (ts, m) in list(recent_msgs) if datetime.fromisoformat(ts) >= cutoff]
    total = len(msgs)
    by_mmsi = Counter(m for _, m in msgs)
    active = len(by_mmsi)
    top5 = by_mmsi.most_common(5)
    by_type = Counter(ev for *_, ev in recent_geofence_events)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_minutes": KPI_WINDOW_MIN,
        "total_messages": total,
        "active_mmsi": active,
        "top5": top5,
        "events_by_type": dict(by_type),
    }

# ------------------ FastAPI ------------------ #
app = FastAPI(title="AIS Suape API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def _startup():
    diag["startup_called"] = True
    print(f"[API] Startup | MMSIs={len(MMSI_LIST)} | API_KEY set={bool(API_KEY)}")
    asyncio.create_task(ais_consumer())

@app.get("/health")
async def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/diag")
async def diag_status():
    return JSONResponse({
        **diag,
        "api_key_configured": bool(API_KEY),
        "mmsi_count": len(MMSI_LIST),
    })

@app.get("/geofences")
async def geofences():
    return JSONResponse(GEOFENCES)

@app.get("/kpis")
async def kpis():
    return JSONResponse(compute_kpis())

@app.get("/events")
async def events(limit: int = 200):
    data = list(recent_geofence_events)[-limit:]
    return JSONResponse(data)

@app.get("/positions")
async def positions(limit: int = 1000):
    data = list(recent_positions)[-limit:]
    return JSONResponse(data)
