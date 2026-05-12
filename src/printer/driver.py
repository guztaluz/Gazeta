from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Protocol

import structlog

from src.config import Settings, get_settings

log = structlog.get_logger()


class Driver(Protocol):
    async def print(self, png_bytes: bytes) -> Path: ...


class MockDriver:
    """Saves the PNG to disk and updates output/latest.png. No BLE."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def print(self, png_bytes: bytes) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.output_dir / f"{stamp}.png"
        path.write_bytes(png_bytes)

        latest = self.output_dir / "latest.png"
        if latest.is_symlink() or latest.exists():
            try:
                latest.unlink()
            except OSError:
                pass
        try:
            os.symlink(path.name, latest)
        except OSError:
            latest.write_bytes(png_bytes)

        log.info("mock_print", path=str(path), bytes=len(png_bytes))
        return path


class BlePrinterDriver:
    """Real driver — implemented Friday once the printer arrives."""

    def __init__(self, mac: str) -> None:
        self.mac = mac

    async def print(self, png_bytes: bytes) -> Path:
        raise NotImplementedError("BLE driver lands when the printer arrives")


def get_driver(settings: Settings | None = None) -> Driver:
    s = settings or get_settings()
    if s.printer_driver == "ble":
        if not s.printer_mac:
            raise RuntimeError("PRINTER_DRIVER=ble but PRINTER_MAC is unset")
        return BlePrinterDriver(s.printer_mac)
    return MockDriver(Path(s.output_dir))
