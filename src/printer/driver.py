from __future__ import annotations

import asyncio
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Protocol

import structlog

from src.config import Settings, get_settings

log = structlog.get_logger()


def _write_latest(output_dir: Path, png_bytes: bytes) -> Path:
    """Write a timestamped PNG and refresh the output/latest.png symlink."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"{stamp}.png"
    path.write_bytes(png_bytes)

    latest = output_dir / "latest.png"
    if latest.is_symlink() or latest.exists():
        try:
            latest.unlink()
        except OSError:
            pass
    try:
        os.symlink(path.name, latest)
    except OSError:
        latest.write_bytes(png_bytes)
    return path


class Driver(Protocol):
    async def print(self, png_bytes: bytes) -> Path: ...


class MockDriver:
    """Saves the PNG to disk and updates output/latest.png. No BLE."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def print(self, png_bytes: bytes) -> Path:
        path = _write_latest(self.output_dir, png_bytes)
        log.info("mock_print", path=str(path), bytes=len(png_bytes))
        return path


class BlePrinterDriver:
    """Sends a PNG to the printer over BLE using the 51 78 protocol that
    demonstrably printed the calibration page. Writes chunked command bytes to
    the ae01 characteristic with a small inter-chunk delay (no notification
    handshake — this firmware doesn't send completion notifications).

    Also saves a copy of the PNG to output/ so /preview/latest works.
    """

    WRITE_CHAR = "0000ae01-0000-1000-8000-00805f9b34fb"
    CHUNK_SIZE = 180
    CHUNK_DELAY_S = 0.02
    FLUSH_DELAY_S = 2.0

    def __init__(
        self,
        mac: str,
        output_dir: Path | None = None,
        energy: int | None = None,
    ) -> None:
        self.mac = mac
        self.output_dir = output_dir
        self.energy = energy

    async def print(self, png_bytes: bytes) -> Path:
        from PIL import Image

        from src.printer import protocol as p

        img = Image.open(io.BytesIO(png_bytes))
        energy = self.energy if self.energy is not None else p.DEFAULT_ENERGY

        # Single print job, control commands matching the captured app exactly
        # (SET_QUALITY 0x33, SET_ENERGY 0x6b12, APPLY 00 01, FEED 40). No priming.
        payload = p.image_to_commands(img, energy=energy)
        await self._print_one(payload)
        log.info("ble_print", mac=self.mac, rows=img.height, bytes=len(payload))

        if self.output_dir is not None:
            return _write_latest(self.output_dir, png_bytes)
        return Path("(not saved)")

    async def _print_one(self, payload: bytes) -> None:
        from bleak import BleakClient

        async with BleakClient(self.mac, timeout=20.0) as client:
            for i in range(0, len(payload), self.CHUNK_SIZE):
                await client.write_gatt_char(
                    self.WRITE_CHAR, payload[i:i + self.CHUNK_SIZE], response=False
                )
                await asyncio.sleep(self.CHUNK_DELAY_S)
            await asyncio.sleep(self.FLUSH_DELAY_S)


def get_driver(settings: Settings | None = None) -> Driver:
    s = settings or get_settings()
    if s.printer_driver == "ble":
        if not s.printer_mac:
            raise RuntimeError("PRINTER_DRIVER=ble but PRINTER_MAC is unset")
        return BlePrinterDriver(s.printer_mac, Path(s.output_dir))
    return MockDriver(Path(s.output_dir))
