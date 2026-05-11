import pyautogui
import time
from time import strptime, strftime

t1 = strptime('21:30:00', '%H:%M:%S')
t2 = strptime('23:00:00', '%H:%M:%S')

while True:
    nn = strptime(strftime('%H:%M:%S'), '%H:%M:%S')
    if (nn >= t1 and nn <= t2):
        print("in time")
    else:
        print("out time")

        pyautogui.moveTo(200, 200)  # moves mouse to X of 100, Y of 200.
        pyautogui.scroll(100)
        time.sleep(1)
        pyautogui.scroll(-100)
        time.sleep(1)
        pyautogui.scroll(100)
        time.sleep(1)
        pyautogui.scroll(-100)
        time.sleep(1)
        pyautogui.scroll(100)
        time.sleep(1)
        pyautogui.scroll(-100)
        time.sleep(1)
        pyautogui.scroll(100)
        time.sleep(1)
        pyautogui.scroll(-100)

    time.sleep(20)
