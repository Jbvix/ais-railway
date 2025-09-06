# server.py
import os, json, asyncio, random
from collections import deque, Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any


import websockets
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from geofences_from_kmz import GEOFENCES


API_KEY = os.getenv("AISSTREAM_API_KEY", "349ff539f874179f9626af85ec372783f8256e08")
URL = "wss://stream.aisstream.io/v0/stream"
MMSI_LIST = [m.strip() for m in os.getenv("MMSI_LIST", "710025630,710000348,710014960,710015850").split(',') if m.strip()]
KPI_WINDOW_MIN = int(os.getenv("KPI_WINDOW_MIN", "15"))


# Estado em memória
recent_positions: deque = deque(maxlen=100000) # {ts,mmsi,lat,lon,sog}
recent_msgs: deque = deque(maxlen=200000) # (ts,mmsi)
recent_geofence_events: deque = deque(maxlen=10000) # (ts,mmsi,geo,event)


# Geofence (ray casting)
def point_in_polygon(lat: float, lon: float, poly):
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


_geofence_state = defaultdict(dict) # mmsi -> name -> bool


async def ais_consumer():
if not API_KEY:
print("[ERRO] AISSTREAM_API_KEY não definido.")
return
backoff = 1
while True:
try:
async with websockets.connect(
URL, ping_interval=20, ping_timeout=20, max_queue=2000, max_size=2**22
) as ws:
sub = {
"APIKey": API_KEY,
"BoundingBoxes": [[[-90.0, -180.0], [90.0, 180.0]]],
"FilterMessageTypes": ["PositionReport"],
"FiltersShipMMSI": MMSI_LIST,
}
await ws.send(json.dumps(sub))
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
return JSONResponse(data)
