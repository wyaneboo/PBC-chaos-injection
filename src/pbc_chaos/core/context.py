"""Run and client context objects shared across pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pbc_chaos.config.settings import SimulatorSettings


@dataclass(frozen=True)
class RunContext:
    settings: SimulatorSettings
    run_id: str
    output_dir: Path
    seed: int


@dataclass(frozen=True)
class ClientContext:
    run: RunContext
    client_id: str
    client_name: str
    financial_year: int
    locale: str
    currency: str
    seed: int

