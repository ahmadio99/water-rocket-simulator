from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import math
import random

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------
# WebSocket manager
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ---------------------------
# Models
# ---------------------------
class LaunchParams(BaseModel):
    bottle_volume_l: float
    bottle_diameter_cm: float
    nozzle_diameter_cm: float
    water_volume_l: float
    air_pressure_psi: float
    soap_amount: float
    wind_speed_ms: float
    temperature_c: float
    player: str
    events_enabled: bool = True

# ---------------------------
# Live events
# ---------------------------
def roll_live_events() -> List[str]:
    events = []
    if random.random() < 0.20:
        events.append("🌬 Windvlaag — plotselinge zijwind!")
    if random.random() < 0.15:
        events.append("💦 Lekkage — druk valt sneller weg!")
    if random.random() < 0.08:
        events.append("🔥 Turbo Boost — extra stuwkracht!")
    if random.random() < 0.10:
        events.append("🌩 Stormmodus — turbulentie actief!")
    return events

# ---------------------------
# Realistic physics (water + air thrust phases, drag, gravity)
# ---------------------------
def simulate_flight(p: LaunchParams) -> Dict[str, Any]:
    rho_water = 1000.0
    rho_air = 1.225
    g = 9.81
    Cd = 0.5

    bottle_volume = p.bottle_volume_l / 1000.0
    water_volume = max(min(p.water_volume_l / 1000.0, bottle_volume), 0.0)
    nozzle_area = math.pi * ((p.nozzle_diameter_cm / 100.0) / 2.0) ** 2
    bottle_area = math.pi * ((p.bottle_diameter_cm / 100.0) / 2.0) ** 2

    p_abs_init = (p.air_pressure_psi * 6894.76) + 101325.0

    dry_mass = 0.15 + 0.1 * p.soap_amount
    m_water = rho_water * water_volume
    init_air_volume = bottle_volume - water_volume
    m_air = max(init_air_volume, 0.0) * rho_air
    mass = dry_mass + m_water + m_air

    x, y = 0.0, 0.0
    vx, vy = 0.0, 0.0
    t = 0.0
    dt = 0.005
    t_max = 60.0

    times, xs, ys = [], [], []

    gamma = 1.4
    def pressure_water_phase(p0, air_vol_now, air_vol_init):
        if air_vol_init <= 0:
            return 101325.0
        return 101325.0 + (p0 - 101325.0) * (air_vol_init / max(air_vol_now, 1e-9)) ** gamma

    def pressure_air_phase(p0, vol_ratio):
        return p0 * (vol_ratio ** (-gamma))

    p_abs = p_abs_init
    air_vol_init = max(init_air_volume, 1e-9)

    airborne = False  # NEW: track if rocket has left the ground

    while t < t_max:
        thrust = 0.0

        if m_water > 1e-8 and nozzle_area > 0.0:
            air_vol_now = bottle_volume - (m_water / rho_water)
            p_abs = pressure_water_phase(p_abs_init, air_vol_now, air_vol_init)
            dp = max(p_abs - 101325.0, 0.0)
            if dp > 0:
                thrust = nozzle_area * math.sqrt(2.0 * dp * rho_water)
                m_dot_w = rho_water * nozzle_area * math.sqrt(2.0 * dp / rho_water)
                dm_w = min(m_dot_w * dt, max(m_water * 0.25, 1e-6))
                m_water -= dm_w
                mass = dry_mass + m_water + m_air
            else:
                m_water = 0.0
                mass = dry_mass + m_air

        elif m_air > 1e-8 and nozzle_area > 0.0:
            vol_ratio = bottle_volume / air_vol_init
            p_air = pressure_air_phase(p_abs_init, vol_ratio)
            dp = max(p_air - 101325.0, 0.0)
            if dp > 0:
                thrust = nozzle_area * dp
                m_dot_a = nozzle_area * rho_air * math.sqrt(2.0 * dp / rho_air)
                dm_a = min(m_dot_a * dt, max(m_air * 0.25, 1e-6))
                m_air -= dm_a
                mass = dry_mass + m_air
            else:
                m_air = 0.0
                mass = dry_mass
        else:
            mass = dry_mass

        v_rel_x = vx - p.wind_speed_ms
        v_rel_y = vy
        v_rel = math.hypot(v_rel_x, v_rel_y)
        drag = 0.5 * rho_air * v_rel**2 * Cd * bottle_area
        drag_x = -drag * (v_rel_x / (v_rel + 1e-9))
        drag_y = -drag * (v_rel_y / (v_rel + 1e-9))

        ax = drag_x / mass
        ay = (thrust / mass) + (drag_y / mass) - g

        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt

        if y > 0:
            airborne = True  # mark as airborne once it leaves the ground

        times.append(round(t, 3))
        xs.append(x)
        ys.append(max(y, 0.0))

        t += dt
        # Only break if we've been airborne and are back on ground descending
        if airborne and y <= 0 and vy <= 0:
            break

    return {
        "t": times,
        "x": xs,
        "y": ys,
        "max_altitude_m": round(max(ys), 2) if ys else 0.0,
        "range_m": round(xs[-1], 2) if xs else 0.0
    }


# ---------------------------
# Routes
# ---------------------------
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("static/index.html")

@app.post("/launch")
async def launch(params: LaunchParams):
    result = simulate_flight(params)

    # Broadcast to Launch Log
    await manager.broadcast({
        "channel": "launch_log",
        "data": {
            "player": params.player,
            "max_altitude_m": result["max_altitude_m"],
            "range_m": result["range_m"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    })

    # Events (optional, controlled by client toggle)
    events: List[str] = []
    if params.events_enabled:
        events = roll_live_events()
        for e in events:
            await manager.broadcast({
                "channel": "chat",
                "data": {
                    "user": "SYSTEM",
                    "text": f"{params.player}: {e}"
                }
            })

    return JSONResponse({
        "ok": True,
        "trajectory": result,
        "summary": {
            "max_altitude_m": result["max_altitude_m"],
            "range_m": result["range_m"],
            "events": events
        }
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat":
                await manager.broadcast({
                    "channel": "chat",
                    "data": {
                        "user": data.get("user", "anon"),
                        "text": data.get("text", "")
                    }
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
