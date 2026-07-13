import asyncio
from TrikiPy import TrikiDevice
import time

async def main():
    # 1. Initialize the class
    triki = TrikiDevice(BTName="Triki", literal=False)
    
    print("Connecting...")
    
    # 2. Connect and fetch constants
    success = await triki.connectTriki()
    if not success:
        print("Failed to connect.")
        return
        
    print(f"Connected to {triki.getName()}!")
    print(f"Firmware: {triki.getFirmwareVersion()}")
    print(f"Battery Level: {await triki.getBatteryLevel()}%")
    
    # 3. Start Streaming
    if await triki.startTriki():
        
        # Turn LED on and off
        print("Flashing LED...")
        await triki.setLED(True)
        print("LED status: "+str(triki.getLEDstatus()))
        time.sleep(2)
        await triki.setLED(False)
        print("LED status: "+str(triki.getLEDstatus()))
        time.sleep(2)
        await triki.setLED(True)
        print("LED status: "+str(triki.getLEDstatus()))
        time.sleep(1)
        await triki.setLED(False)
        print("LED status: "+str(triki.getLEDstatus()))
        time.sleep(1)
        
        print("Continuing...")
        print("\n--- Live Data Started ---")
        
        await triki.setLED(True)
        
        # 4. Fetch the next 200 samples asynchronously
        for _ in range(200):
            data = await triki.getTrikiData()
            print(f"Accel(X,Y,Z): {data.ax:6}, {data.ay:6}, {data.az:6}  |  Gyro(X,Y,Z): {data.gx:6}, {data.gy:6}, {data.gz:6}")
            
        # 5. Stop and disconnect
        print("\nStopping...")
        
        #await triki.setLED(False) # stopTriki() turns the LED off
        await triki.stopTriki()
        print("Disconnected gracefully.")

if __name__ == "__main__":
    asyncio.run(main())