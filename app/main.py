"""
main.py
-------
Remote Equipment Monitoring Dashboard
======================================
Vzdialený monitoring a riadenie priemyselného zariadenia (simulované, ale
architektonicky pripravené na reálny PLC/robot cez Modbus/OPC UA).

Spustenie:
    pip install -r requirements.txt
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Potom otvor http://localhost:8000 v prehliadači.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .simulator import MachineStatus, Simulator

simulator = Simulator()
POLL_INTERVAL_SECONDS = 2


class ConnectionManager:
    """Drží zoznam pripojených WebSocket klientov a rozposiela im dáta naraz."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        stale = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()
_last_status = MachineStatus.RUNNING


async def polling_loop() -> None:
    """Bežiaci na pozadí: číta dáta zo (simulovaného) zariadenia každých pár
    sekúnd, ukladá históriu, deteguje nové poruchy a posiela update všetkým
    pripojeným dashboardom cez WebSocket."""
    global _last_status
    while True:
        reading = simulator.read()
        database.insert_reading(reading)

        if reading.status == MachineStatus.FAULT and _last_status != MachineStatus.FAULT:
            message = (
                f"Porucha zariadenia: tlak {reading.pressure_bar} bar, "
                f"teplota {reading.temperature_c} °C"
            )
            database.insert_alarm(reading.timestamp, message)

        _last_status = reading.status

        await manager.broadcast(
            {
                "type": "reading",
                "timestamp": reading.timestamp,
                "temperature_c": reading.temperature_c,
                "pressure_bar": reading.pressure_bar,
                "cycle_count": reading.cycle_count,
                "status": reading.status.value,
            }
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


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def get_status():
    return {
        "temperature_c": simulator.temperature_c,
        "pressure_bar": simulator.pressure_bar,
        "cycle_count": simulator.cycle_count,
        "status": simulator.status.value,
    }


@app.get("/api/history")
async def get_history(limit: int = 100):
    return database.get_history(limit=limit)


@app.get("/api/alarms")
async def get_alarms(limit: int = 20):
    return database.get_alarms(limit=limit)


@app.post("/api/restart")
async def restart_machine():
    """Vzdialený zásah – reštart/kvitovanie poruchy bez fyzickej prítomnosti
    pri zariadení. Presne toto je funkcia, ktorú náborári pri 'remote' rolách
    chcú vidieť: schopnosť bezpečne zasiahnuť do procesu na diaľku."""
    simulator.restart()
    database.acknowledge_alarms()
    await manager.broadcast({"type": "restart_ack"})
    return {"ok": True, "status": simulator.status.value}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # držíme spojenie otvorené; klient v tejto appke nič neposiela
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
