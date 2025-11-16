import cv2
import numpy as np
import mediapipe as mp
import random
import time
import subprocess
import platform

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
    finger_tips = [4, 8, 12, 16, 20]
    positions = []
    
    for tip_id in finger_tips:
        x = int(landmarks[tip_id].x * frame_width)
        y = int(landmarks[tip_id].y * frame_height)
        positions.append((x, y))
    
    return positions

def force_window_focus_mac(window_name):
    """Aggressively try to keep window in focus on macOS"""
    try:
        # AppleScript to bring Python to front
        script = '''
        tell application "System Events"
            set frontmost of first process whose name contains "Python" to true
        end tell
        '''
        subprocess.run(['osascript', '-e', script], capture_output=True)
    except:
        pass

print("Starting webcam... Press 'q' to quit")
print("Hold up your fingers and watch the program TRY to count them... 😈")
print("WARNING: This app will aggressively fight for your attention!")

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
last_focus_steal = time.time()
circled_fingers = []
completed = False

# Create window
window_name = 'Stupid Finger Counter - YOU ARE TRAPPED! 😈'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

# Try to make it fullscreen and always on top (limited on macOS)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

frame_count = 0

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to grab frame")
        break

    frame_count += 1
    
    # ** EVIL FEATURE: Steal focus back every 0.5 seconds **
    if time.time() - last_focus_steal > 0.5 and not completed:
        if platform.system() == 'Darwin':  # macOS
            force_window_focus_mac(window_name)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        last_focus_steal = time.time()

    frame_resized = cv2.resize(frame, (1920, 1080))
    results = hands.process(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        all_finger_positions = []
        fingers_up = 0
        
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame_resized, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            fingers_up += count_fingers(hand_landmarks)
            fingers_up += detect_thumb(hand_landmarks)
            
            positions = get_finger_positions(hand_landmarks, 1920, 1080)
            all_finger_positions.extend(positions)

        # ** DUMB FEATURE 1: 50% chance to randomly forget every second **
        if time.time() - last_forget_time > 1.0:
            if random.random() < 0.5 and not completed:
                print("🤡 Oops! Forgot what I was counting. Starting over...")
                current_count = 0
                frames_correct = 0
                target_count = None
                circled_fingers = []
                cv2.putText(frame_resized, "FORGOT! Restarting...", (100, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
                # Extra annoying focus steal when it forgets
                if platform.system() == 'Darwin':
                    force_window_focus_mac(window_name)
            last_forget_time = time.time()

        if target_count is None:
            target_count = fingers_up
            print(f"Trying to count to {target_count}...")

        if fingers_up == target_count and not completed:
            frames_correct += 1
            progress = (frames_correct / required_frames) * 100
            
            if random.random() < 0.05:
                cv2.putText(frame_resized, "Wait... thinking... 🤔", (100, 400),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 165, 0), 4)
                time.sleep(random.uniform(0.5, 2))
            
            cv2.putText(frame_resized, f"Counting: {current_count}/{target_count}", (100, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 6)
            cv2.putText(frame_resized, f"Progress: {progress:.0f}%", (100, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 0), 4)
            
            if frames_correct >= required_frames:
                if current_count < len(all_finger_positions):
                    circled_fingers.append(all_finger_positions[current_count])
                    print(f"✓ Counted finger #{current_count + 1}!")
                
                current_count += 1
                frames_correct = 0
                
                if random.random() < 0.2:
                    print(f"Wait... is that {random.randint(1, 20)}? I'm confused!")
                
                if current_count >= target_count:
                    completed = True
                    print(f"🎉 Finally counted all {current_count} fingers! YOU'RE FREE!")
        else:
            frames_correct = 0
            if not completed:
                cv2.putText(frame_resized, "Hold still!", (100, 400),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)

        if random.random() < 0.05 and not completed:
            gibberish = random.choice(["Is that a hand?", "Potato detected!", 
                                      "Error: Too many fingers", "Counting backwards now!",
                                      "Wait, what was I doing?", "Did you just move?!",
                                      "Stop trying to escape!", "PAY ATTENTION TO ME!"])
            cv2.putText(frame_resized, gibberish, (100, 800),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 255), 4)

    else:
        cv2.putText(frame_resized, "No hands detected!", (100, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
        if not completed:
            current_count = 0
            frames_correct = 0
            target_count = None
            circled_fingers = []

    # Draw circles
    for idx, (x, y) in enumerate(circled_fingers):
        color = (0, 255, 0)
        cv2.circle(frame_resized, (x, y), 50, color, 6)
        cv2.putText(frame_resized, str(idx + 1), (x - 20, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, color, 5)

    if completed:
        cv2.putText(frame_resized, f"CONGRATULATIONS! You counted {current_count} fingers!", 
                    (200, 500), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 5)
        cv2.putText(frame_resized, "Press 'q' to escape this nightmare", 
                    (400, 600), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    else:
        # Flashing warning message
        if frame_count % 60 < 30:  # Flash every second
            cv2.putText(frame_resized, "⚠️ STOP TRYING TO ESCAPE! ⚠️", 
                        (300, 1000), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
        cv2.putText(frame_resized, "Count your fingers or press 'q' to give up!", 
                    (350, 950), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    cv2.imshow(window_name, frame_resized)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("You escaped! (or gave up...)")
        break

cap.release()
cv2.destroyAllWindows()
