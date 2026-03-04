import win32api, win32gui, win32con
from ctypes import windll
import time
import threading
from pynput import keyboard
from PIL import ImageGrab
import numpy as np

windll.user32.SetProcessDPIAware()
WIDTH = win32api.GetSystemMetrics(0)
HEIGHT = win32api.GetSystemMetrics(1)

cx = WIDTH // 2
cy = HEIGHT // 2

RADIUS = 3
THICKNESS = 1

class InputState:
    def __init__(self):
        self.lock = threading.Lock()

state = InputState()

def on_press(key):
    global RADIUS, THICKNESS
    try:
        with state.lock:
            if key == keyboard.Key.f5:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return False  # stop listener cleanly
            if key == keyboard.Key.f6:
                RADIUS += 2
                if RADIUS > 15:
                    win32gui.InvalidateRect(hwnd, None, True)
                    win32gui.UpdateWindow(hwnd)
                    RADIUS = 3
            if key == keyboard.Key.f7:
                THICKNESS += 1
                if THICKNESS > 5:
                    win32gui.InvalidateRect(hwnd, None, True)
                    win32gui.UpdateWindow(hwnd)
                    THICKNESS = 1

    except Exception as e:
        print("Keyboard error:", e)

keyboard.Listener(on_press=on_press).start()

# ===============================
# Window Procedure
# ===============================
def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0

    if msg == win32con.WM_PAINT:
        hdc, paintStruct = win32gui.BeginPaint(hwnd)

        # Clear background (transparent black)
        brush = win32gui.CreateSolidBrush(win32api.RGB(0, 0, 0))
        win32gui.FillRect(hdc, (0, 0, WIDTH, HEIGHT), brush)
        win32gui.DeleteObject(brush)

        win32gui.EndPaint(hwnd, paintStruct)
        return 0

    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


# ===============================
# Register Window Class
# ===============================
wc = win32gui.WNDCLASS()
wc.lpfnWndProc = wnd_proc
wc.lpszClassName = "Dynamic Crosshair V2"
wc.hInstance = win32api.GetModuleHandle(None)

class_atom = win32gui.RegisterClass(wc)

# ===============================
# Create Overlay Window
# ===============================
hwnd = win32gui.CreateWindowEx(
    win32con.WS_EX_LAYERED |
    win32con.WS_EX_TOPMOST |
    win32con.WS_EX_TRANSPARENT,  # click-through
    class_atom,
    None,
    win32con.WS_POPUP,
    0, 0,
    WIDTH, HEIGHT,
    None,
    None,
    wc.hInstance,
    None
)

# Set transparency (black becomes fully transparent)
win32gui.SetLayeredWindowAttributes(
    hwnd,
    win32api.RGB(0, 0, 0),  # colorkey
    0,
    win32con.LWA_COLORKEY
)

win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
win32gui.UpdateWindow(hwnd)

# ===============================
# Crosshair Drawing Function
# ===============================
def draw_crosshair(color_rgb):
    hdc = win32gui.GetDC(hwnd)

    pen = win32gui.CreatePen(
        win32con.PS_SOLID,
        THICKNESS,
        win32api.RGB(*color_rgb)
    )

    old_pen = win32gui.SelectObject(hdc, pen)

    # Horizontal
    win32gui.MoveToEx(hdc, cx - RADIUS, cy)
    win32gui.LineTo(hdc, cx + RADIUS, cy)

    # Vertical
    win32gui.MoveToEx(hdc, cx, cy - RADIUS)
    win32gui.LineTo(hdc, cx, cy + RADIUS)

    win32gui.SelectObject(hdc, old_pen)
    win32gui.DeleteObject(pen)
    win32gui.ReleaseDC(hwnd, hdc)


# ==============================
# Color Processing
# ==============================

def Luminance2Color(rgb):
    r, g, b = rgb
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum > 150:
        return (0, 0, 128) # Navy blue
    elif lum < 100:
        return (255, 255, 197) # Bright yellow
    else:
        return (57, 255, 20) # Cyan
    
def smooth_color(prev, curr, alpha=0.85):
    return tuple(
        int(alpha*p + (1-alpha)*c)
        for p, c in zip(prev, curr)
    )


# ===============================
# Main Logic
# ===============================

prev_col = (255, 255, 255)

try:
    while True:
        win32gui.PumpWaitingMessages()

        roi_bbox = (cx - 10, cy - 10, cx + 10, cy + 10)
        roi = ImageGrab.grab(bbox=roi_bbox)

        curr_col = tuple(np.asarray(roi, dtype=np.float32).mean(axis=(0, 1)).astype(int))
    
        smoothed = smooth_color(prev_col, curr_col)
        prev_col = smoothed

        color = Luminance2Color(smoothed)

        # Draw new crosshair
        draw_crosshair(color)

        time.sleep(0.016)  # ~60 FPS

except Exception as e:
    print("Error in main logic: ", e)