import time
from collections import deque
from threading import Thread

import cv2
import numpy as np
import win32gui
from mss import mss
from pynput import keyboard


def list_window_titles():
    window_titles = []

    def enum_window_titles(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                window_titles.append(title)

    win32gui.EnumWindows(enum_window_titles, None)
    return window_titles


def capture_window(hwnd):
    # Get window dimensions
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    # Capture the window using mss
    with mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        img = np.array(sct.grab(monitor))

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


# List available window titles
available_windows = list_window_titles()
print("Available windows:")
for i, window in enumerate(available_windows, start=1):
    print(f"{i}. {window}")

# Prompt the user to select a window
selected_window = int(input("Enter the number of the window you want to record: "))
window_title = available_windows[selected_window - 1]

# Set up screen recording parameters
duration = 10  # Duration of the replay buffer in seconds
additional_duration = 5  # Additional duration to record after key press
fps = 30  # Frames per second
scale_factor = 0.5  # Scale down the recorded frames by 2x
fourcc = cv2.VideoWriter_fourcc(*'X264')

# Initialize the replay buffer
replay_buffer = deque(maxlen=duration * fps)

# Recording states
not_recording = 0
recording = 1
stopping = 2
done = 3

# Initialize the recording state
recording_state = not_recording


def on_key_press():
    global recording_state
    if recording_state == not_recording:
        recording_state = recording
        print("Recording started.")
        Thread(target=stop_recording_after_delay).start()


def stop_recording_after_delay():
    global recording_state
    time.sleep(additional_duration)
    recording_state = done
    print("Recording stopped.")


# Find the window handle
hwnd = win32gui.FindWindow(None, window_title)

if hwnd:
    # Create the global key handler
    with keyboard.GlobalHotKeys({'e': on_key_press}) as listener:
        # Start capturing the window
        while True:
            # Capture the window content
            img = capture_window(hwnd)
            img = cv2.resize(img, None, fx=scale_factor, fy=scale_factor)

            # Add the frame to the replay buffer
            replay_buffer.append(img)

            if recording_state == recording:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_filename = f"recording_{timestamp}.mp4"
                out = cv2.VideoWriter(output_filename, fourcc, fps, (img.shape[1], img.shape[0]))
                for frame in replay_buffer:
                    out.write(frame)
                recording_state = stopping

            elif recording_state == stopping:
                out.write(img)

            if recording_state == done:
                out.release()
                print(f"Recording saved as {output_filename}")
                recording_state = not_recording

            # Wait for a short duration to maintain the desired frame rate
            time.sleep(1 / fps)
else:
    print(f"Window with title '{window_title}' not found.")
