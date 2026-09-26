"""
simulator.py
------------
Simuluje priemyselnú výrobnú linku (napr. bunku s ABB robotom a pneumatickým
upínačom). Podporuje štart/stop, nastaviteľné cieľové hodnoty (setpointy)
a náhodné poruchy. V produkcii by sa metóda `read()` nahradila reálnym
čítaním cez Modbus TCP / OPC UA — zvyšok aplikácie ostáva rovnaký.
"""

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MachineStatus(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    FAULT = "FAULT"
    STOPPED = "STOPPED"


@dataclass
class Reading:
    timestamp: float
    temperature_c: float
    pressure_bar: float
    cycle_count: int
    status: MachineStatus
    setpoint_temp: float
    setpoint_pressure: float


class Simulator:
    def __init__(self, name: str, setpoint_temp: float = 45.0, setpoint_pressure: float = 6.0):
        self.name = name
        self.temperature_c = setpoint_temp
        self.pressure_bar = setpoint_pressure
        self.setpoint_temp = setpoint_temp
        self.setpoint_pressure = setpoint_pressure
        self.cycle_count = 0
        self.status = MachineStatus.STOPPED
        self._fault_chance = 0.03

    def read(self) -> Reading:
        """Vygeneruje ďalšiu vzorku dát. Ak je linka zastavená, hodnoty sa
        nemenia a nevznikajú poruchy."""
        if self.status == MachineStatus.STOPPED:
            return self._snapshot()

        if self.status != MachineStatus.FAULT:
            self.temperature_c += (self.setpoint_temp - self.temperature_c) * 0.1
            self.temperature_c += random.uniform(-0.4, 0.4)

            self.pressure_bar += (self.setpoint_pressure - self.pressure_bar) * 0.1
            self.pressure_bar += random.uniform(-0.1, 0.1)

            self.cycle_count += 1
            self.status = MachineStatus.RUNNING

            if random.random() < self._fault_chance or self.pressure_bar > self.setpoint_pressure + 2.2:
                self.status = MachineStatus.FAULT

        return self._snapshot()

    def _snapshot(self) -> Reading:
        return Reading(
            timestamp=time.time(),
            temperature_c=round(self.temperature_c, 1),
            pressure_bar=round(self.pressure_bar, 2),
            cycle_count=self.cycle_count,
            status=self.status,
            setpoint_temp=self.setpoint_temp,
            setpoint_pressure=self.setpoint_pressure,
        )

    def start(self) -> None:
        if self.status == MachineStatus.STOPPED:
            self.status = MachineStatus.IDLE

    def stop(self) -> None:
        self.status = MachineStatus.STOPPED

    def restart(self) -> None:
        """Vzdialené kvitovanie poruchy — linka prejde do IDLE a pokračuje."""
        if self.status != MachineStatus.STOPPED:
            self.status = MachineStatus.IDLE
            self.pressure_bar = self.setpoint_pressure

    def set_setpoints(self, temperature: Optional[float], pressure: Optional[float]) -> None:
        if temperature is not None:
            self.setpoint_temp = temperature
        if pressure is not None:
            self.setpoint_pressure = pressure
