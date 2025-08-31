import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("no camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("no frame.")
        break

    cv2.imshow("Camera Test", frame)

  
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
