import asyncio
from TrikiPy import TrikiDevice

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
        print("\n--- Live Data Started ---")
        
        # 4. Fetch the next 20 samples asynchronously
        for _ in range(20):
            data = await triki.getTrikiData()
            print(f"Accel(X,Y,Z): {data.ax:6}, {data.ay:6}, {data.az:6}  |  Gyro(X,Y,Z): {data.gx:6}, {data.gy:6}, {data.gz:6}")
            
        # 5. Stop and disconnect
        print("\nStopping...")
        await triki.stopTriki()
        print("Disconnected gracefully.")

if __name__ == "__main__":
    asyncio.run(main())