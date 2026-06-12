# unofficial-triki-api-py

An unofficial Python driver using `bleak` to stream IMU accelerometer and gyroscope data from the Żabka Triki BLE gaming controller.

> **Disclaimer:** This is an unofficial, open-source project. It is **not** affiliated with, endorsed by, or sponsored by Żabka Polska. "Żabka", "Żappka", and "Triki" are trademarks of their respective owners. This software is provided strictly for educational purposes and to enable hardware interoperability. No proprietary firmware or applications were decompiled or distributed in the creation of this project.

## Features
- **Asynchronous & Fast:** Built on top of `bleak` for non-blocking native OS Bluetooth support.
- **Auto-Discovery:** Scans and connects to the controller automatically via its advertised BLE name.
- **Live IMU Streaming:** Unpacks and parses the raw BLE byte stream into a clean Python Data Class containing 6-DoF integers (Accel X/Y/Z and Gyro X/Y/Z).
- **Graceful State Management:** Handles the undocumented "wake-up" and "sleep" hex commands to preserve the device's battery when not in use.

## Prerequisites
- Python 3.7 or higher
- Windows, macOS, or Linux (requires an OS with standard Bluetooth Low Energy support)

Install the required BLE library:
```bash
pip install bleak

```

## Quick Start

1. Turn on your Triki device (ensure it is not actively connected to your mobile phone, but paired with your PC).
2. Clone this repository and run the demo script:

```bash
python RunDemo.py

```

### Example Usage (`RunDemo.py`)

```python
import asyncio
from TrikiPy import TrikiDevice

async def main():
    triki = TrikiDevice(BTName="Triki", literal=False)
    
    if await triki.connectTriki():
        print(f"Connected to {triki.getName()}!")
        print(f"Battery: {await triki.getBatteryLevel()}%")
        
        if await triki.startTriki():
            print("Streaming Live IMU Data...")
            for _ in range(20):
                data = await triki.getTrikiData()
                print(f"Accel(X,Y,Z): {data.ax:6}, {data.ay:6}, {data.az:6} | Gyro(X,Y,Z): {data.gx:6}, {data.gy:6}, {data.gz:6}")
                
            await triki.stopTriki()

if __name__ == "__main__":
    asyncio.run(main())

```

## Protocol Documentation (Under the Hood)

For developers looking to port this to other languages (like C++, JS, or Rust), here is the reverse-engineered GATT protocol the Triki device uses to communicate.

The device utilizes the **Nordic UART Service (NUS)** structure:

* **RX UUID (Write):** `6e400002-b5a3-f393-e0a9-e50e24dcca9e`
* **TX UUID (Notify):** `6e400003-b5a3-f393-e0a9-e50e24dcca9e`

### Wake / Sleep Commands

To preserve battery, the internal IMU is asleep by default upon connection. You must write specific byte arrays to the `RX` line to begin the data stream.

* **Wake Up Command:** `0x20 0x10 0x00 0xD0 0x07 0x34 0x00 0x03`
* **Sleep Command:** `0x20 0x00 0x00 0x00 0x00 0x00 0x00`

### Data Packet Structure

Once awake, the device pushes 14-byte data packets over the `TX` line via Notifications. The data is formatted as Little-Endian, 16-bit signed integers (`<h`).

| Byte Index | Length | Description |
| --- | --- | --- |
| `0-1` | 2 bytes | **Header** (Always `0x22 0x00` for stream data) |
| `2-3` | 2 bytes | **Accelerometer X** |
| `4-5` | 2 bytes | **Accelerometer Y** |
| `6-7` | 2 bytes | **Accelerometer Z** |
| `8-9` | 2 bytes | **Gyroscope X** |
| `10-11` | 2 bytes | **Gyroscope Y** |
| `12-13` | 2 bytes | **Gyroscope Z** |

*Note: The device occasionally sends a 5-byte Status/Acknowledge packet starting with `0x21` when state changes occur (e.g., waking up or going to sleep).*

## License

This project is licensed under the MIT License.
