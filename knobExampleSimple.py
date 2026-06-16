import asyncio
from TrikiPy import TrikiDevice, TrikiKnob

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
    
    # 3. Create knob object
    knob = TrikiKnob()
    knob.resetStatus()
    
    # 4. Start Streaming
    if await triki.startTriki():
        print("\n--- Live Knob Data Started ---")
        
        # 5. Fetch the next 400 samples asynchronously
        for _ in range(400):
            data = await triki.getTrikiData()
            rotation = knob.updateStatus(data)
            print("Knob rotation in degrees: "+str(rotation))
            
            
        # 6. Stop and disconnect
        print("\nStopping...")
        await triki.stopTriki()
        print("Disconnected gracefully.")

if __name__ == "__main__":
    asyncio.run(main())