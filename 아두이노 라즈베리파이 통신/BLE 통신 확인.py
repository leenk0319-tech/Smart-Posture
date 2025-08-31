import asyncio
from bleak import BleakClient, BleakScanner

ESP32_MAC = "40:4C:CA:41:4E:0E"  
CHAR_UUID = "abcd1234-1234-1234-1234-abcdef123456"

async def run():
    print("Scanning for ESP32 device...")
    devices = await BleakScanner.discover()
    found = any(d.address.upper() == ESP32_MAC for d in devices)
    if not found:
        print("ESP32 not found during scan!")
        return

    print(f"Connecting to {ESP32_MAC}...")
    async with BleakClient(ESP32_MAC) as client:
        print("Connected!")

        def notification_handler(sender, data):
            try:
                message = data.decode()
                print(f"Received from ESP32: {message}")
            except Exception as e:
                print("Error decoding data:", e)

        await client.start_notify(CHAR_UUID, notification_handler)
        print("Notification started. Waiting for weight threshold signal...")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping notifications...")
            await client.stop_notify(CHAR_UUID)
            print("Notifications stopped.")

asyncio.run(run())
