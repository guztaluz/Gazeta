# X6h printer — working BLE protocol (SOLVED)

The printer is the `51 78` "cat printer" command family. After a long debugging
saga, the fix came from capturing the official **Tiny Print** app's Bluetooth
traffic (Android btsnoop HCI log) while it printed a photo perfectly, then
matching its **control commands byte-for-byte**.

## Root cause of the months of faint prints

Our control commands were wrong. The image encoding (`0xA2` raw bitmap rows)
was fine all along — it printed the correct picture, just faint, because the
density/quality commands were off. The fixes:

| command      | was (faint)   | now (dark, = app)            |
|--------------|---------------|------------------------------|
| SET_QUALITY  | `0x32`        | **`0x33`**                    |
| SET_ENERGY   | 0x3000/0xFFFF | **`0x6b12` (27410)**          |
| APPLY (0xBE) | `01`          | **`00 01`**                   |
| FEED         | 25            | **40 (0x28)**                 |

CRC-8 (poly 0x07, table-based) was already correct — our generated control
packets now match the app's captured bytes exactly:

```
SET_QUALITY  51 78 a4 00 01 00 33 99 ff
SET_ENERGY   51 78 af 00 02 00 6b 12 1c ff
APPLY        51 78 be 00 02 00 00 01 07 ff
FEED         51 78 bd 00 01 00 28 d8 ff
```

## The working print sequence (src/printer/protocol.py: image_to_commands)

```
GET_DEV_STATE          51 78 a3 00 01 00 00 00 ff
SET_QUALITY (0x33)     51 78 a4 00 01 00 33 99 ff
SET_ENERGY (0x6b12)    51 78 af 00 02 00 6b 12 1c ff
APPLY_ENERGY (00 01)   51 78 be 00 02 00 00 01 07 ff
LATTICE_START          51 78 a6 ...
per row: 0xA2 raw bitmap  (48 bytes, LSB-first, 1=black)
LATTICE_END            51 78 a6 ...
FEED (40)              51 78 bd 00 01 00 28 d8 ff
SET_PAPER              51 78 a1 ...
GET_DEV_STATE
```

Sent over GATT characteristic **ae01** (write-without-response), chunked at
180 bytes, ~20ms between chunks. No priming, no segmentation, no notification
handshake needed — one continuous job.

## GATT (from scripts/find_printer.py)
- `ae01` write — commands + image data
- `ae02` notify — status replies (not required for printing)

## Notes
- The app sends image data as `0xCF` (a different, RLE-ish command); we use
  `0xA2` raw bitmap, which also works once control bytes are correct. If denser
  prints or speed ever matter, the `0xCF` format could be decoded from the
  capture — but `0xA2` is proven working.
- Capture method (repeatable): Android dev options → Bluetooth HCI snoop log →
  print from Tiny Print → `adb bugreport` → extract `FS/data/log/bt/btsnoop_hci.log`.
