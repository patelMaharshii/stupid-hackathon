import cv2
import numpy as np
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.3)

def count_fingers(hand_landmarks):
    finger_tips = [8, 12, 16, 20]  
    fingers_up = 0
    landmarks = hand_landmarks.landmark
    
    for tip in finger_tips:
        if landmarks[tip].y < landmarks[tip - 2].y: 
            fingers_up += 1
    
    return fingers_up

def detect_thumb(hand_landmarks):
    landmarks = hand_landmarks.landmark
    if landmarks[4].y < landmarks[1].y:  
        return 1
    return 0

print("Starting webcam... Press 'c' to capture and analyze, 'q' to quit")
cap = cv2.VideoCapture(0)

# Set camera properties (helps on macOS)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Failed to grab frame")
        break
    
    # Show live preview
    cv2.imshow('Live Feed - Press C to capture', frame)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('c'):
        print("Analyzing frame...")
        frame_resized = cv2.resize(frame, (640, 480))
        results = hands.process(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
        
        if results.multi_hand_landmarks:
            fingers_up = 0
            thumb_up = 0
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame_resized, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                fingers_up += count_fingers(hand_landmarks)
                fingers_up += detect_thumb(hand_landmarks)
                
            cv2.putText(frame_resized, f'Fingers: {fingers_up}', (50, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            # if thumb_up == 1:
            #     cv2.putText(frame_resized, 'Thumb: 1', (50, 150), 
            #                 cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                
            print(f"Detected Fingers, Thumb: {fingers_up},{thumb_up}")

        else:
            print("No hands detected.")
        
        cv2.imshow('Analysis Result', frame_resized)
    
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
