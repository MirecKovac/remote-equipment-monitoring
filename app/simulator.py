"""
simulator.py
------------
Simuluje priemyselné zariadenie (napr. bunku s ABB robotom a pneumatickým
upínačom), ktoré by v reálnej nasadenej verzii komunikovalo cez Modbus TCP
alebo OPC UA. Tu generujeme realistické dáta, aby dashboard fungoval bez
fyzického PLC.

Nahradenie za reálne zariadenie: stačí vymeniť metódu `read()` za volanie
napr. pymodbus (`client.read_holding_registers(...)`) alebo opcua-asyncio
klienta — zvyšok aplikácie (API, websocket, dashboard) ostáva rovnaký.
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum


class MachineStatus(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    FAULT = "FAULT"


@dataclass
class Reading:
    timestamp: float
    temperature_c: float
    pressure_bar: float
    cycle_count: int
    status: MachineStatus


@dataclass
class Simulator:
    temperature_c: float = 45.0
    pressure_bar: float = 6.0
    cycle_count: int = 0
    status: MachineStatus = MachineStatus.RUNNING
    _fault_chance: float = 0.03  # 3 % šanca na poruchu pri každom cykle

    def read(self) -> Reading:
        """Vygeneruje ďalšiu simulovanú vzorku dát zo zariadenia."""
        if self.status != MachineStatus.FAULT:
            # jemný náhodný drift teploty a tlaku okolo prevádzkového bodu
            self.temperature_c += random.uniform(-0.6, 0.6)
            self.temperature_c = max(30.0, min(85.0, self.temperature_c))

            self.pressure_bar += random.uniform(-0.15, 0.15)
            self.pressure_bar = max(4.0, min(8.5, self.pressure_bar))

            self.cycle_count += 1
            self.status = MachineStatus.RUNNING

            # náhodne vygenerovaná porucha (napr. tlak mimo rozsah)
            if random.random() < self._fault_chance or self.pressure_bar > 8.2:
                self.status = MachineStatus.FAULT

        return Reading(
            timestamp=time.time(),
            temperature_c=round(self.temperature_c, 1),
            pressure_bar=round(self.pressure_bar, 2),
            cycle_count=self.cycle_count,
            status=self.status,
        )

    def restart(self) -> None:
        """Simuluje vzdialený reštart zariadenia po poruche (kvitovanie alarmu)."""
        self.status = MachineStatus.IDLE
        self.pressure_bar = 6.0
