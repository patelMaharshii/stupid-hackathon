import cv2
import numpy as np
import mediapipe as mp
import random
import time

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

def get_finger_positions(hand_landmarks, frame_width, frame_height):
    """Get the pixel positions of all fingertips"""
    landmarks = hand_landmarks.landmark
    finger_tips = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
    positions = []
    
    for tip_id in finger_tips:
        x = int(landmarks[tip_id].x * frame_width)
        y = int(landmarks[tip_id].y * frame_height)
        positions.append((x, y))
    
    return positions

print("Starting webcam... Press 'q' to quit")
print("Hold up your fingers and watch the program TRY to count them... 😈")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

# Tracking variables
current_count = 0
target_count = None
frames_correct = 0
required_frames = 10
last_forget_time = time.time()
circled_fingers = []  # Store positions of circled fingers

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to grab frame")
        break

    frame_resized = cv2.resize(frame, (640, 480))
    results = hands.process(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        # Collect all finger positions
        all_finger_positions = []
        fingers_up = 0
        
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame_resized, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            fingers_up += count_fingers(hand_landmarks)
            fingers_up += detect_thumb(hand_landmarks)
            
            # Get positions of fingertips
            positions = get_finger_positions(hand_landmarks, 640, 480)
            all_finger_positions.extend(positions)

        # ** DUMB FEATURE 1: 50% chance to randomly forget every second **
        if time.time() - last_forget_time > 1.0:
            if random.random() < 0.5:
                print("🤡 Oops! Forgot what I was counting. Starting over...")
                current_count = 0
                frames_correct = 0
                target_count = None
                circled_fingers = []  # CLEAR ALL CIRCLES!
                cv2.putText(frame_resized, "FORGOT! Restarting...", (50, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            last_forget_time = time.time()

        # Set target if not set
        if target_count is None:
            target_count = fingers_up
            print(f"Trying to count to {target_count}...")

        # Check if current detection matches target
        if fingers_up == target_count:
            frames_correct += 1
            progress = (frames_correct / required_frames) * 100
            
            # ** DUMB FEATURE 2: Sometimes add random delay while "thinking" **
            if random.random() < 0.05:
                cv2.putText(frame_resized, "Wait... thinking... 🤔", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
                time.sleep(random.uniform(0.5, 2))
            
            cv2.putText(frame_resized, f"Counting: {current_count}/{target_count}", (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(frame_resized, f"Progress: {progress:.0f}%", (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            
            # Successfully counted one more!
            if frames_correct >= required_frames:
                # Add a circle for the newly counted finger
                if current_count < len(all_finger_positions):
                    circled_fingers.append(all_finger_positions[current_count])
                    print(f"✓ Counted finger #{current_count + 1}!")
                
                current_count += 1
                frames_correct = 0
                
                # ** DUMB FEATURE 3: Random wrong celebration **
                if random.random() < 0.2:
                    print(f"Wait... is that {random.randint(1, 20)}? I'm confused!")
                
                # Check if we've counted all fingers
                if current_count >= target_count:
                    cv2.putText(frame_resized, f"DONE! Total: {current_count}", (50, 250),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                    print(f"🎉 Finally counted all {current_count} fingers!")
                    cv2.putText(frame_resized, "Keep holding... or restart!", (50, 300),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            # Fingers changed - reset
            frames_correct = 0
            cv2.putText(frame_resized, "Hold still!", (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # ** DUMB FEATURE 4: Occasionally show gibberish **
        if random.random() < 0.05:
            gibberish = random.choice(["Is that a hand?", "Potato detected!", 
                                      "Error: Too many fingers", "Counting backwards now!",
                                      "Wait, what was I doing?"])
            cv2.putText(frame_resized, gibberish, (50, 400),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)

    else:
        cv2.putText(frame_resized, "No hands detected!", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        current_count = 0
        frames_correct = 0
        target_count = None
        circled_fingers = []  # Clear circles when no hands

    # ** DRAW ALL CIRCLED FINGERS **
    for idx, (x, y) in enumerate(circled_fingers):
        # Draw a big colorful circle around each counted finger
        color = (0, 255, 0)  # Green for successfully counted
        cv2.circle(frame_resized, (x, y), 30, color, 4)
        # Add number inside circle
        cv2.putText(frame_resized, str(idx + 1), (x - 10, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow('Stupid Finger Counter', frame_resized)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
