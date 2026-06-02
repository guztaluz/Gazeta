# Gazeta — daily summary thermal printer service.
# Runs the FastAPI app + Playwright (Chromium) renderer + BlueZ for BLE.
# The host (UGOS) has the kernel Bluetooth stack + dongle as hci0 but no BlueZ
# userspace, so we ship bluetoothd inside the container and talk to hci0.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

# System deps:
#  - bluez + dbus: BLE stack inside the container (bleak talks to bluetoothd)
#  - fonts + Chromium runtime libs: Playwright renders the summary PNG
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez dbus \
    fonts-dejavu-core fonts-liberation \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the project (pyproject + package) then install. setuptools needs src/
# present to build the package, so copy before installing.
COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts
RUN pip install --upgrade pip && pip install ".[ble]" \
    && playwright install --with-deps chromium

# Entrypoint starts dbus + bluetoothd, then the service.
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
