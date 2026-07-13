# An unofficial Python (Bleak) API to stream IMU sensor data from the Zabka Triki gaming controller.
import asyncio
import struct
from dataclasses import dataclass
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

@dataclass
class TrikiData:
    """A clean struct to hold the unpacked IMU data."""
    ax: int
    ay: int
    az: int
    gx: int
    gy: int
    gz: int

class TrikiDevice:
    def __init__(self, BTName: str = "Triki", literal: bool = False):
        """
        Initializes the Triki object.
        
        :param BTName: The string to look for when scanning.
        :param literal: If True, matches the name exactly. If False, checks if name starts with BTName.
        """
        self.BTName = BTName
        self.literal = literal
        
        # Private class variables, initialized to None
        self._FirmwareVersion = None
        self._RXUUID = None
        self._TXUUID = None
        self._LEDUUID = None
        self._Name = None
        
        # Hardcoded universal UUID for Battery Level (Battery Service)
        self._BATTERY_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
        
        # Internal state variables
        self._client = None
        self._data_buffer = bytearray()
        self._data_queue = asyncio.Queue()
        self._is_streaming = False
        self._is_led_active = False

    async def connectTriki(self, timeout: float = 10.0) -> bool:
        """Scans, connects, and populates GATT data. Returns True on success."""
        try:
            # 1. Scan for the device
            devices = await BleakScanner.discover(timeout=timeout)
            target_device = None
            
            for device in devices:
                if device.name:
                    if self.literal and device.name == self.BTName:
                        target_device = device
                        break
                    elif not self.literal and device.name.startswith(self.BTName):
                        target_device = device
                        break
                        
            if not target_device:
                return False

            # 2. Connect
            self._client = BleakClient(target_device.address)
            await self._client.connect()
            
            if not self._client.is_connected:
                return False

            # 3. Read GATT to populate private variables
            for service in self._client.services:
                for char in service.characteristics:
                    # Generic Access Profile -> Device Name
                    if char.uuid.startswith("00002a00"):
                        val = await self._client.read_gatt_char(char.uuid)
                        self._Name = val.decode('utf-8', errors='ignore')
                        
                    # Device Information -> Firmware Revision String
                    elif char.uuid.startswith("00002a26"):
                        val = await self._client.read_gatt_char(char.uuid)
                        self._FirmwareVersion = val.decode('utf-8', errors='ignore')
                        
                    # Nordic UART -> RX
                    elif char.uuid.startswith("6e400002"):
                        self._RXUUID = char.uuid
                        
                    # Nordic UART -> TX
                    elif char.uuid.startswith("6e400003"):
                        self._TXUUID = char.uuid

                    # Custom LED control characteristic
                    elif char.uuid.startswith("6e400004"):
                        self._LEDUUID = char.uuid
                        
            return True
            
        except Exception as e:
            print(f"[Error connecting]: {e}")
            return False

    def _notification_handler(self, sender, data):
        """Internal callback to handle and parse incoming byte streams."""
        self._data_buffer.extend(data)
        
        while len(self._data_buffer) >= 14:
            if self._data_buffer[0] == 0x22 and self._data_buffer[1] == 0x00:
                # Valid 14-byte payload found
                packet = self._data_buffer[:14]
                ax, ay, az, gx, gy, gz = struct.unpack('<hhhhhh', packet[2:14])
                
                # Push the struct into the async queue
                parsed_data = TrikiData(ax, ay, az, gx, gy, gz)
                self._data_queue.put_nowait(parsed_data)
                
                self._data_buffer = self._data_buffer[14:]
                
            elif self._data_buffer[0] == 0x21:
                # Status/Acknowledge payload (5 bytes)
                self._data_buffer = self._data_buffer[5:]
                
            else:
                # Misaligned packet, pop 1 byte and try again
                self._data_buffer.pop(0)

    async def startTriki(self) -> bool:
        """Sends wake command and begins parsing notifications."""
        if not self._client or not self._client.is_connected:
            return False
        if not self._RXUUID or not self._TXUUID:
            return False
            
        try:
            # Start listening
            await self._client.start_notify(self._TXUUID, self._notification_handler)
            
            # Send wake-up command
            wake_command = b'\x20\x10\x00\xd0\x07\x34\x00\x03'
            await self._client.write_gatt_char(self._RXUUID, wake_command, response=False)
            
            self._is_streaming = True
            return True
            
        except Exception:
            return False

    async def getTrikiData(self) -> TrikiData:
        """Awaits and returns the next available IMU data struct from the queue."""
        if not self._is_streaming:
            raise RuntimeError("Triki is not started. Call startTriki() first.")
            
        # This will safely block until a new packet is parsed and available
        return await self._data_queue.get()
    
    async def setLED(self, enabled: bool) -> bool:
        """Allows to turn the device's LED on or off."""
        if not self._client or not self._client.is_connected:
            return False
        if not self._LEDUUID:
            return False

        try:
            await self._client.write_gatt_char(
                self._LEDUUID,
                b"\x01" if enabled else b"\x00",
                response=True
            )
            self._is_led_active = enabled
            return True
        except Exception:
            return False

    async def stopTriki(self) -> bool:
        """Sends sleep command, stops notifications, and disconnects."""
        if not self._client or not self._client.is_connected:
            return False
        
        if self._is_led_active:
            try:
                await self.setLED(False)
                self._is_led_active = False
            except:
                pass

        try:
            # Send sleep command
            if self._RXUUID:
                sleep_command = b'\x20\x00\x00\x00\x00\x00\x00'
                await self._client.write_gatt_char(self._RXUUID, sleep_command, response=False)
                
            # Allow a tiny delay for the device to acknowledge before closing the pipe
            await asyncio.sleep(0.5)
            
            # Stop listening and disconnect
            if self._TXUUID and self._is_streaming:
                await self._client.stop_notify(self._TXUUID)
                
            await self._client.disconnect()
            self._is_streaming = False
            return True
            
        except Exception:
            return False

    # --- Getters ---

    def getName(self) -> str:
        return self._Name
    
    def getLEDstatus(self) -> bool:
        return self._is_led_active

    def getFirmwareVersion(self) -> str:
        return self._FirmwareVersion

    async def getBatteryLevel(self) -> int:
        """Performs a live GATT read to fetch the current battery percentage."""
        if not self._client or not self._client.is_connected:
            return -1
        try:
            val = await self._client.read_gatt_char(self._BATTERY_UUID)
            # Battery is returned as a single unsigned 8-bit int (uint8)
            return int(val[0])
        except Exception:
            return -1

    def __del__(self):
        """
        Destructor to gracefully handle cleanup. 
        Note: Python __del__ is synchronous, so it schedules the async cleanup
        if the event loop is still running.
        """
        if self._client and self._client.is_connected:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.stopTriki())
            except RuntimeError:
                pass # Event loop already closed, cannot safely disconnect over BLE
            
# A class to easily use the device as knob            
class TrikiKnob:
    def __init__(self, statusMin = -100000, statusMax = 100000, outputMin = 0, outputMax = 360, tolerance = 100):
        """
        Initalizes the object.
        :param statusMin: Minimal internal knob status value
        :param statusMax: Maximum interval knob status value
        :param outputMin: Minimal output value
        :param outputMax: Maximum output value
        :param tolerance: Minimum change of status to assume rotation happened
        """
        self.statusMin = statusMin
        self.statusMax = statusMax
        self.status = statusMin
        self.outputMin = outputMin
        self.outputMax = outputMax
        self.value = statusMin
        self.lastIMUdata = 0
        self.tolerance = tolerance
        
    def resetStatus(self):
        """
        Reset position of the knob.
        """
        self.status = self.statusMin
        
    def updateStatus(self, IMUData: TrikiData) -> float:
        """
        Update position of the knob.
        Returns position of the knob.
        :param IMUdata: IMU data of the device.
        """
        delta = abs(self.lastIMUdata-IMUData.az)
        if delta<self.tolerance:
            return self.value
        
        self.lastIMUdata = IMUData.az
        
        if self.status == self.statusMax and IMUData.az > 0:
            self.status = self.statusMin
        if self.status == self.statusMin and IMUData.az < 0:
            self.status = self.statusMax
        
        self.status += IMUData.az
        
        if self.status > self.statusMax:
            self.status = self.statusMax
        if self.status < self.statusMin:
            self.status = self.statusMin
            
        clampedValue = max(self.statusMin, min(self.statusMax, self.status))
    
        normalizedValue = (clampedValue - self.statusMin) / (self.statusMax - self.statusMin)
    
        self.value = normalizedValue * (self.outputMax - self.outputMin) + self.outputMin
                
        return self.value
        
    def getLastValue(self) -> float:
        """
        Read last position of the knob.
        """
        return self.value
