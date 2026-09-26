"""
main.py
-------
Remote Equipment Monitoring Dashboard
======================================
Vzdialený monitoring a riadenie viacerých priemyselných liniek naraz.

Spustenie:
    pip install -r requirements.txt
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import database
from .simulator import MachineStatus, Simulator

POLL_INTERVAL_SECONDS = 2

# Dve simulované linky. Pridanie ďalšej = jeden riadok tu.
lines: Dict[str, Simulator] = {
    "line1": Simulator(name="Linka 1 — montáž"),
    "line2": Simulator(name="Linka 2 — balenie"),
}
_last_status: Dict[str, MachineStatus] = {line_id: sim.status for line_id, sim in lines.items()}


class ConnectionManager:
    """Drží WebSocket klientov oddelene podľa linky, ktorú sledujú."""

    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocket]] = {line_id: [] for line_id in lines}

    async def connect(self, line_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[line_id].append(websocket)

    def disconnect(self, line_id: str, websocket: WebSocket) -> None:
        if websocket in self.connections.get(line_id, []):
            self.connections[line_id].remove(websocket)

    async def broadcast(self, line_id: str, message: dict) -> None:
        stale = []
        for connection in self.connections.get(line_id, []):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(line_id, connection)


manager = ConnectionManager()


async def polling_loop() -> None:
    """Na pozadí číta dáta z každej linky, ukladá históriu, deteguje nové
    poruchy a posiela update pripojeným dashboardom danej linky."""
    while True:
        for line_id, sim in lines.items():
            reading = sim.read()
            database.insert_reading(line_id, reading)

            if reading.status == MachineStatus.FAULT and _last_status[line_id] != MachineStatus.FAULT:
                message = (
                    f"Porucha zariadenia: tlak {reading.pressure_bar} bar, "
                    f"teplota {reading.temperature_c} °C"
                )
                database.insert_alarm(line_id, reading.timestamp, message)

            _last_status[line_id] = reading.status

            await manager.broadcast(
                line_id,
                {
                    "type": "reading",
                    "timestamp": reading.timestamp,
                    "temperature_c": reading.temperature_c,
                    "pressure_bar": reading.pressure_bar,
                    "cycle_count": reading.cycle_count,
                    "status": reading.status.value,
                    "setpoint_temp": reading.setpoint_temp,
                    "setpoint_pressure": reading.setpoint_pressure,
                },
            )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    task = asyncio.create_task(polling_loop())
    yield
    task.cancel()


app = FastAPI(title="Remote Equipment Monitoring Dashboard", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _line_or_404(line_id: str) -> Simulator:
    if line_id not in lines:
        raise ValueError(f"Neznáma linka: {line_id}")
    return lines[line_id]


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/lines")
async def get_lines():
    return [{"id": line_id, "name": sim.name} for line_id, sim in lines.items()]


@app.get("/api/status")
async def get_status(line: str = "line1"):
    sim = _line_or_404(line)
    return {
        "temperature_c": sim.temperature_c,
        "pressure_bar": sim.pressure_bar,
        "cycle_count": sim.cycle_count,
        "status": sim.status.value,
        "setpoint_temp": sim.setpoint_temp,
        "setpoint_pressure": sim.setpoint_pressure,
    }


@app.get("/api/history")
async def get_history(line: str = "line1", limit: int = 100):
    _line_or_404(line)
    return database.get_history(line_id=line, limit=limit)


@app.get("/api/alarms")
async def get_alarms(line: str = "line1", limit: int = 20):
    _line_or_404(line)
    return database.get_alarms(line_id=line, limit=limit)


@app.get("/api/export")
async def export_csv(line: str = "line1"):
    _line_or_404(line)
    csv_text = database.export_history_csv(line_id=line)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{line}_history.csv"'},
    )


@app.post("/api/restart")
async def restart_line(line: str = "line1"):
    sim = _line_or_404(line)
    sim.restart()
    database.acknowledge_alarms(line_id=line)
    await manager.broadcast(line, {"type": "restart_ack"})
    return {"ok": True, "status": sim.status.value}


@app.post("/api/start")
async def start_line(line: str = "line1"):
    sim = _line_or_404(line)
    sim.start()
    return {"ok": True, "status": sim.status.value}


@app.post("/api/stop")
async def stop_line(line: str = "line1"):
    sim = _line_or_404(line)
    sim.stop()
    return {"ok": True, "status": sim.status.value}


class SetpointPayload(BaseModel):
    temperature: Optional[float] = None
    pressure: Optional[float] = None


@app.post("/api/setpoint")
async def set_setpoint(payload: SetpointPayload, line: str = "line1"):
    sim = _line_or_404(line)
    sim.set_setpoints(payload.temperature, payload.pressure)
    return {"ok": True, "setpoint_temp": sim.setpoint_temp, "setpoint_pressure": sim.setpoint_pressure}


@app.websocket("/ws/{line_id}")
async def websocket_endpoint(websocket: WebSocket, line_id: str):
    if line_id not in lines:
        await websocket.close(code=4004)
        return
    await manager.connect(line_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(line_id, websocket)
