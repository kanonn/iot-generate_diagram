"""
Mouse Movement Simulator - Keep your computer awake
模拟鼠标移动，防止电脑休眠

Usage:
    python mouse_mover.py

Requirements:
    pip install pyautogui

Press Ctrl+C to stop
"""

import pyautogui
import random
import time
import sys

# Safety feature - move mouse to corner to abort
pyautogui.FAILSAFE = True

def simulate_mouse():
    print("=" * 50)
    print("  Mouse Movement Simulator")
    print("  マウス移動シミュレーター")
    print("=" * 50)
    print("\nPress Ctrl+C to stop / 停止するには Ctrl+C を押してください")
    print("Move mouse to top-left corner to emergency stop")
    print("-" * 50)
    
    click_counter = 0
    move_counter = 0
    
    try:
        while True:
            # Get current mouse position
            current_x, current_y = pyautogui.position()
            screen_width, screen_height = pyautogui.size()
            
            # Random movement distance (small movements)
            move_x = random.randint(-100, 100)
            move_y = random.randint(-80, 80)
            
            # Calculate new position (keep within screen bounds)
            new_x = max(50, min(screen_width - 50, current_x + move_x))
            new_y = max(50, min(screen_height - 50, current_y + move_y))
            
            # Move mouse smoothly
            duration = random.uniform(0.3, 0.8)
            pyautogui.moveTo(new_x, new_y, duration=duration)
            move_counter += 1
            
            # Occasionally click (roughly every 5-10 movements)
            if random.randint(1, 8) == 1:
                # Small pause before click
                time.sleep(random.uniform(0.1, 0.3))
                pyautogui.click()
                click_counter += 1
                print(f"[{time.strftime('%H:%M:%S')}] Clicked at ({new_x}, {new_y}) | Moves: {move_counter}, Clicks: {click_counter}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Moved to ({new_x}, {new_y}) | Moves: {move_counter}")
            
            # Wait random interval (30-90 seconds)
            wait_time = random.randint(30, 90)
            print(f"    Next action in {wait_time} seconds...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("  Stopped by user")
        print(f"  Total moves: {move_counter}, Total clicks: {click_counter}")
        print("=" * 50)
        sys.exit(0)

if __name__ == "__main__":
    # Check if pyautogui is installed
    try:
        import pyautogui
    except ImportError:
        print("Error: pyautogui not installed")
        print("Please run: pip install pyautogui")
        sys.exit(1)
    
    simulate_mouse()
