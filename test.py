import cv2
import numpy as np
import mediapipe as mp
import random
import time
import subprocess
import platform
import pygame
import os

# Initialize pygame for audio
pygame.mixer.init()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
# Optimize MediaPipe settings
hands = mp_hands.Hands(
    static_image_mode=False, 
    max_num_hands=2, 
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    model_complexity=0
)

def download_rickroll_assets():
    """Download Rick Roll GIF and audio if not already present"""
    gif_path = "rickroll.gif"
    audio_path = "rickroll.mp3"
    return gif_path, audio_path

def load_gif_frames(gif_path, max_frames=30):
    """Load GIF frames using OpenCV - limit to 30 frames for performance"""
    if not os.path.exists(gif_path):
        print(f"Warning: {gif_path} not found. Rick Roll GIF disabled.")
        return []
    
    cap = cv2.VideoCapture(gif_path)
    frames = []
    frame_count = 0
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_resized = cv2.resize(frame, (400, 400))
        frames.append(frame_resized)
        frame_count += 1
    
    cap.release()
    print(f"Loaded {len(frames)} GIF frames")
    return frames

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

def scale_landmarks(hand_landmarks, scale_x, scale_y):
    """Create a copy of landmarks scaled to display resolution"""
    from mediapipe.framework.formats import landmark_pb2
    
    scaled_landmarks = landmark_pb2.NormalizedLandmarkList()
    
    for landmark in hand_landmarks.landmark:
        new_landmark = scaled_landmarks.landmark.add()
        new_landmark.x = landmark.x
        new_landmark.y = landmark.y
        new_landmark.z = landmark.z
    
    return scaled_landmarks

def force_window_focus_mac(window_name):
    """Aggressively try to keep window in focus on macOS"""
    try:
        script = '''
        tell application "System Events"
            set frontmost of first process whose name contains "Python" to true
        end tell
        '''
        subprocess.run(['osascript', '-e', script], capture_output=True, timeout=0.1)
    except:
        pass

print("Starting webcam... Press 'q' to quit")
print("Hold up your fingers and watch the program TRY to count them... 😈")
print("WARNING: This app will aggressively fight for your attention!")
print("Loading Rick Roll assets...")

# Load Rick Roll assets
gif_path, audio_path = download_rickroll_assets()
rickroll_frames = load_gif_frames(gif_path)
rickroll_audio_loaded = os.path.exists(audio_path)

if rickroll_audio_loaded:
    pygame.mixer.music.load(audio_path)
    print("Rick Roll audio loaded! 🎵")
else:
    print(f"Warning: {audio_path} not found. Place rickroll.mp3 in the script directory.")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

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
rickroll_active = False
rickroll_start_time = 0
rickroll_duration = 5
gif_frame_index = 0
audio_playing = False

# Create window
window_name = 'Stupid Finger Counter - YOU ARE TRAPPED!'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

frame_count = 0
is_mac = platform.system() == 'Darwin'

# Processing and display resolutions
PROCESS_WIDTH = 640
PROCESS_HEIGHT = 360
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to grab frame")
        break

    frame_count += 1
    
    # Less frequent focus stealing
    if time.time() - last_focus_steal > 2.0 and not completed:
        if is_mac:
            force_window_focus_mac(window_name)
        else:
            cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        last_focus_steal = time.time()

    # Resize to display resolution
    frame_display = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    
    # Check if Rick Roll visuals should stop
    if rickroll_active and (time.time() - rickroll_start_time > rickroll_duration):
        rickroll_active = False
    
    # Check if audio has finished playing
    if audio_playing and not pygame.mixer.music.get_busy():
        audio_playing = False
    
    # Process with MediaPipe at lower resolution for speed
    frame_process = cv2.resize(frame_display, (PROCESS_WIDTH, PROCESS_HEIGHT))
    results = hands.process(cv2.cvtColor(frame_process, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks:
        all_finger_positions = []
        fingers_up = 0
        
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw landmarks on DISPLAY resolution frame
            # MediaPipe will automatically scale normalized coordinates (0-1) to frame size
            mp_draw.draw_landmarks(frame_display, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Count fingers using normalized coordinates (works at any resolution)
            fingers_up += count_fingers(hand_landmarks)
            fingers_up += detect_thumb(hand_landmarks)
            
            # Get finger positions at DISPLAY resolution
            positions = get_finger_positions(hand_landmarks, DISPLAY_WIDTH, DISPLAY_HEIGHT)
            all_finger_positions.extend(positions)

        # Forget logic
        if time.time() - last_forget_time > 1.0:
            if random.random() < 0.5 and not completed:
                print("🤡 Oops! Forgot what I was counting. RICK ROLL TIME!")
                current_count = 0
                frames_correct = 0
                target_count = None
                circled_fingers = []
                
                rickroll_active = True
                rickroll_start_time = time.time()
                gif_frame_index = 0
                
                if rickroll_audio_loaded and not audio_playing:
                    pygame.mixer.music.play()
                    audio_playing = True
                    print("🎵 Rick Roll audio started!")
                
                if is_mac:
                    force_window_focus_mac(window_name)
                    
            last_forget_time = time.time()

        if target_count is None:
            target_count = fingers_up
            print(f"Trying to count to {target_count}...")

        if fingers_up == target_count and not completed:
            frames_correct += 1
            progress = (frames_correct / required_frames) * 100
            
            if random.random() < 0.05:
                cv2.putText(frame_display, "Wait... thinking...", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2)
                time.sleep(random.uniform(0.5, 2))
            
            cv2.putText(frame_display, f"Counting: {current_count}/{target_count}", (50, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
            cv2.putText(frame_display, f"Progress: {progress:.0f}%", (50, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2)
            
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
                    if audio_playing:
                        pygame.mixer.music.stop()
                        audio_playing = False
        else:
            frames_correct = 0
            if not completed:
                cv2.putText(frame_display, "Hold still!", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)

        if random.random() < 0.02 and not completed:
            gibberish = random.choice(["Is that a hand?", "Potato detected!", 
                                      "Error: Too many fingers", "Counting backwards now!",
                                      "Wait, what was I doing?", "Did you just move?!",
                                      "Stop trying to escape!", "PAY ATTENTION TO ME!"])
            cv2.putText(frame_display, gibberish, (50, 400),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

    else:
        cv2.putText(frame_display, "No hands detected!", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
        if not completed:
            current_count = 0
            frames_correct = 0
            target_count = None
            circled_fingers = []

    # Rick Roll overlay
    if rickroll_active and len(rickroll_frames) > 0:
        gif_frame = rickroll_frames[gif_frame_index % len(rickroll_frames)]
        
        positions = [(830, 50)]
        
        for pos_x, pos_y in positions:
            y1, y2 = pos_y, pos_y + 400
            x1, x2 = pos_x, pos_x + 400
            if y2 <= DISPLAY_HEIGHT and x2 <= DISPLAY_WIDTH:
                frame_display[y1:y2, x1:x2] = gif_frame
        
        cv2.putText(frame_display, "NEVER GONNA GIVE YOU UP!", (200, 360),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        
        gif_frame_index += 1
    
    if audio_playing and not rickroll_active:
        cv2.putText(frame_display, "♪ Rick Roll playing... ♪", (400, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 100), 2)

    # Draw circles for counted fingers
    for idx, (x, y) in enumerate(circled_fingers):
        color = (0, 255, 0)
        cv2.circle(frame_display, (x, y), 30, color, 4)
        cv2.putText(frame_display, str(idx + 1), (x - 10, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    if completed:
        cv2.putText(frame_display, f"CONGRATULATIONS! You counted {current_count} fingers!", 
                    (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 255), 3)
        cv2.putText(frame_display, "Press 'q' to escape this nightmare", 
                    (200, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    else:
        if frame_count % 60 < 30:
            cv2.putText(frame_display, "STOP TRYING TO ESCAPE!", 
                        (200, 650), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame_display, "Count your fingers or press 'q' to give up!", 
                    (200, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow(window_name, frame_display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("You escaped! (or gave up...)")
        break

cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
