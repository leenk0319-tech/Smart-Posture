from picamera2 import Picamera2
import cv2
import mediapipe as mp
import math

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

CVA_THRESHOLD = 52  # adjusted threshold for slight angle

with mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as pose:
    while True:
        frame = picam2.capture_array()
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            # Forward Head Posture (right side)
            ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value]
            shoulder_r = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

            dx = ear.x - shoulder_r.x
            dy = ear.y - shoulder_r.y
            dz = ear.z - shoulder_r.z

            angle_rad = math.atan2(dy, math.sqrt(dx**2 + dz**2))
            cva_deg = abs(angle_rad * 180.0 / math.pi)

            cv2.putText(image, f'CVA: {int(cva_deg)} deg',
                        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if cva_deg < CVA_THRESHOLD:
                cv2.putText(image, "Forward Head Posture!",
                            (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                print("Forward Head Posture")

            # Shoulder tilt
            shoulder_l = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            shoulder_diff = (shoulder_l.y - shoulder_r.y) * image.shape[0]

            if abs(shoulder_diff) > 20:
                if shoulder_diff > 0:
                    cv2.putText(image, "Right Shoulder Higher",
                                (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    print("Right Shoulder Higher")
                else:
                    cv2.putText(image, "Left Shoulder Higher",
                                (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    print("Left Shoulder Higher")

            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        cv2.imshow("Posture Monitor", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()
