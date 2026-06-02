# Deploying Gazeta to the UGREEN NAS

The NAS (UGOS Pro, 192.168.0.19) has Docker, Python, and — confirmed — the
kernel Bluetooth stack with the CSR dongle bound as `hci0`. UGOS has no BlueZ
userspace, so we ship `bluetoothd` inside the container (see Dockerfile).

## One-time prerequisites (already verified)
- `lsusb` shows `0a12:0001 Cambridge Silicon Radio Bluetooth Dongle`
- `/sys/class/bluetooth/hci0` exists (kernel bound the dongle)
- `docker --version` → 26.1.0

## Step 1 — Deploy the code + build the container

From your Mac, in the repo:

```bash
./scripts/deploy_nas.sh
```

This rsyncs the repo (including `.env` and `secrets/`, which are gitignored but
needed at runtime) to `/volume1/docker/gazeta` on the NAS and runs
`docker compose up -d --build`. First build is slow (Chromium + apt deps).

## Step 2 — Get the printer's Linux MAC (IMPORTANT)

`PRINTER_MAC` in `.env` is currently a macOS CoreBluetooth UUID, which is
meaningless on Linux. Re-scan from inside the container to get the real MAC:

```bash
ssh guztaluz@192.168.0.19
docker exec -it gazeta python scripts/find_printer.py
```

Look for the `X6h-...` device — its address will be a real MAC like
`AB:CD:12:34:56:78`. Put that in `.env`:

```bash
cd /volume1/docker/gazeta
# edit .env -> PRINTER_MAC=AB:CD:12:34:56:78
docker compose restart
```

(Make sure the printer is powered on and not connected to anything else.)

## Step 3 — Test a print

```bash
curl -X POST http://192.168.0.19:8080/print/summary
```

Paper should come out of the printer. Watch logs if not:

```bash
docker logs -f gazeta
```

## Step 4 — Schedule the morning print (cron on the NAS)

```bash
ssh guztaluz@192.168.0.19
crontab -e
# add:
0 7 * * * curl -fsS -X POST http://localhost:8080/print/summary || logger -t gazeta "summary failed"
```

Now the daily Gazeta prints at 07:00 every day, no Mac required.

## NoteKeep
Once deployed, NoteKeep posts to `http://192.168.0.19:8080/print/note`
(see NOTEKEEP_INTEGRATION.md). The base URL is the NAS IP.

## Troubleshooting Bluetooth in the container
- `docker exec -it gazeta hciconfig -a` — should show `hci0`. If not, the
  container can't see the adapter; confirm `privileged: true` and
  `network_mode: host` in docker-compose.yml.
- `docker exec -it gazeta bluetoothctl show` — bluetoothd should report the
  controller.
- If `hci0` is DOWN: `docker exec -it gazeta hciconfig hci0 up`.
- CSR clone (`0a12:0001`) flakiness: the container's BlueZ is recent, which is
  what the clone needs. If scans are unreliable, retry; BLE on these dongles
  occasionally needs a second attempt.
