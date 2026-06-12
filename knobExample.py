# Note: Tested on Windows 10
print("Starting... \nThe traingle will turn green on successfull connection. \nPress ESC to safely quit.")
import asyncio
import math
import pygame
import threading
import queue

from TrikiPy import TrikiDevice, TrikiKnob

# Thread-safe queue used to safely pass angle data from BLE thread to Pygame loop
dataQueue = queue.Queue()

# Global flag used to control shutdown of both threads cleanly
isRunning = True

triangleColor = (221, 17, 80)

# ==========================================
# 1. BACKGROUND BLUETOOTH THREAD
# ==========================================
def run_ble_thread():
    """Starts the asyncio event loop inside a separate thread."""
    asyncio.run(ble_main())

async def ble_main():
    global isRunning
    global triangleColor

    triki = TrikiDevice(BTName="Triki", literal=False)
    knob = TrikiKnob()  # Ensure TrikiKnob is updated with the correct fix logic

    print("[BLE] Connecting...")

    if not await triki.connectTriki():
        print("[BLE] Failed to connect.")
        isRunning = False
        return

    print(f"[BLE] Connected to {triki.getName()}!")
    triangleColor = (36, 204, 30)

    if not await triki.startTriki():
        print("[BLE] Failed to start streaming.")
        isRunning = False
        return

    print("[BLE] --- Live Data Started ---")

    try:
        while isRunning:
            # Wait for incoming BLE packet with timeout so we can periodically
            # check if the program is still supposed to run.
            try:
                data = await asyncio.wait_for(triki.getTrikiData(), timeout=0.5)
                angle = knob.updateStatus(data)
                print("Angle: "+str(angle))

                # Keep only the most recent value to avoid lag buildup in the queue
                while not dataQueue.empty():
                    try:
                        dataQueue.get_nowait()
                    except queue.Empty:
                        break

                # Push latest angle to the shared queue
                dataQueue.put(angle)

            except asyncio.TimeoutError:
                continue  # No new data received; loop again and check isRunning

    finally:
        print("\n[BLE] Stopping...")
        await triki.stopTriki()
        print("[BLE] Disconnected gracefully.")


# ==========================================
# 2. MAIN PYGAME THREAD
# ==========================================
def main():
    global isRunning
    global triangleColor

    # Start BLE thread first so data begins streaming immediately
    ble_thread = threading.Thread(target=run_ble_thread, daemon=True)
    ble_thread.start()

    # Initialize Pygame
    pygame.init()
    WIDTH, HEIGHT = 400, 400
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Triki Knob Visualization")

    # Clock used to cap FPS and prevent unnecessary CPU usage
    clock = pygame.time.Clock()
    center = (WIDTH // 2, HEIGHT // 2)
    currentAngle = 0.0

    print("Pygame Window Ready. Press ESC to quit.")

    try:
        while isRunning:
            # Handle window events (keeps OS event loop responsive)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    isRunning = False

            # Retrieve latest angle from BLE thread if available
            try:
                currentAngle = dataQueue.get_nowait()
            except queue.Empty:
                pass  # No new data; reuse last known angle

            # Geometry calculations for triangle orientation
            displayAngle = currentAngle % 360
            rad = math.radians(displayAngle - 90)  # Align 0° to upward direction

            dx = math.cos(rad)
            dy = math.sin(rad)
            px = -dy  # Perpendicular vector
            py = dx

            cx, cy = center
            length = 120
            width = 40
            backOffset = 30

            tip = (cx + dx * length, cy + dy * length)
            baseLeft = (cx - dx * backOffset + px * width / 2,
                        cy - dy * backOffset + py * width / 2)
            baseRight = (cx - dx * backOffset - px * width / 2,
                         cy - dy * backOffset - py * width / 2)

            # Rendering
            screen.fill((30, 30, 30))
            pygame.draw.circle(screen, (100, 100, 100), center, 4)
            pygame.draw.polygon(screen, triangleColor, [tip, baseLeft, baseRight])
            pygame.display.flip()

            # Limit to 60 FPS for smooth animation
            clock.tick(60)

    finally:
        isRunning = False
        pygame.quit()

        # Give BLE thread time to shut down cleanly
        ble_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
