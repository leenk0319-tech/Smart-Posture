import asyncio
import math
from bleak import BleakClient, BleakScanner
from picamera2 import Picamera2
import cv2
from gpiozero import LED
import mediapipe as mp

# ==================== LEDs ====================
led_cva = LED(17)             # Turtle neck
led_shoulder = LED(27)        # Shoulder tilt
led_weight_left = LED(22)     # BLE LEFT
led_weight_right = LED(23)    # BLE RIGHT

# ==================== Mediapipe ====================
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ==================== Camera ====================
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": "XRGB8888", "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

# ==================== Thresholds ====================
CVA_THRESHOLD = 53
SHOULDER_THRESHOLD = 8

# ==================== BLE Settings ====================
ESP32_MAC = "40:4C:CA:41:4E:0E"
CHAR_UUID = "abcd1234-1234-1234-1234-abcdef123456"

# ==================== BLE ===================
ble_state = "BALANCED"  # "LEFT", "RIGHT", "BALANCED"

# ==================== BLE Notification Handler ====================
def notification_handler(sender, data):
    global ble_state
    msg = data.decode().strip()
    print(f"[BLE] Received: {msg}")

    if msg in ["LEFT", "RIGHT", "BALANCED"]:
        ble_state = msg

# ==================== BLE Task ====================
async def ble_task():
    global ble_state
    while True:
        try:
            print("Scanning for ESP32...")
            devices = await BleakScanner.discover(timeout=10.0)
            target = next((d for d in devices if d.address.upper() == ESP32_MAC), None)
            if not target:
                print("ESP32 not found, retrying in 3s...")
                await asyncio.sleep(3)
                continue

            print("Device found, connecting...")
            client = BleakClient(target, timeout=10.0, use_cached=False)
            try:
                await client.connect()
                print("Connected to ESP32")
                await client.start_notify(CHAR_UUID, notification_handler)

                while await client.is_connected():
                    await asyncio.sleep(1)

            except Exception as e:
                print("BLE connection failed:", e)
            finally:
                if client:
                    try:
                        await client.disconnect()
                    except:
                        pass

        except Exception as e:
            print("BLE task error:", e)
            await asyncio.sleep(3)
# ==================== Shoulder Tilt Calculation ====================
def calculate_shoulder_tilt(landmarks):
    left = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    dy = left.y - right.y
    dx = left.x - right.x
    return abs(math.degrees(math.atan2(dy, dx if dx != 0 else 1e-6)))

# ==================== Main Pose Loop ====================
async def main_loop():
    global ble_state
    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        try:
            while True:
                frame = picam2.capture_array()
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = pose.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Reset posture LEDs
                led_cva.off()
                led_shoulder.off()

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark

                    # --- CVA (Turtle neck) ---
                    ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value]
                    shoulder_r = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
                    dx = ear.x - shoulder_r.x
                    dy = ear.y - shoulder_r.y
                    dz = ear.z - shoulder_r.z
                    angle_rad = math.atan2(dy, math.sqrt(dx**2 + dz**2))
                    cva_deg = abs(angle_rad * 180 / math.pi)
                    if cva_deg < CVA_THRESHOLD:
                        led_cva.on()

                    # --- Shoulder tilt ---
                    tilt_angle = calculate_shoulder_tilt(landmarks)
                    if tilt_angle > SHOULDER_THRESHOLD:
                        led_shoulder.on()

                    # Draw landmarks
                    mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
                    )

                # --- BLE weight LEDs ---
                if ble_state == "LEFT":
                    led_weight_left.on()
                    led_weight_right.off()
                elif ble_state == "RIGHT":
                    led_weight_left.off()
                    led_weight_right.on()
                else:  # BALANCED
                    led_weight_left.off()
                    led_weight_right.off()

                # Display
                cv2.imshow("Posture Monitor", image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                await asyncio.sleep(0)

        finally:
          
            led_cva.off()
            led_shoulder.off()
            led_weight_left.off()
            led_weight_right.off()
            cv2.destroyAllWindows()
# ==================== Run BLE + Pose Concurrently ====================
async def main():
    await asyncio.gather(
        ble_task(),
        main_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
