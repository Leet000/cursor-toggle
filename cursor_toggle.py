"""
Cursor Toggle (Windows)
-----------------------
On start it asks you to press the key (or key combo) you want to use.
That key then hides / shows the mouse cursor.
Press CTRL+ALT+Q to quit (cursor is always restored on exit).

No extra packages needed, just Python 3 on Windows.
Run with:   python cursor_toggle.py
"""
import ctypes
import ctypes.wintypes as wt
import atexit
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ---- Constants -------------------------------------------------------------
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008
MOD_NOREPEAT = 0x4000

QUIT_MODS = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
QUIT_VK = 0x51            # Q

SPI_SETCURSORS = 0x0057
WM_HOTKEY = 0x0312
WM_TIMER = 0x0113
HOTKEY_TOGGLE = 1
HOTKEY_QUIT = 2
SW_MINIMIZE = 6

# Keys that can't be used as the main key (mouse buttons, modifiers, Win keys)
FORBIDDEN_VKS = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                 0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5,
                 0x5B, 0x5C, 0xFF}

# Keys that need the "extended" flag to get the right name
EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
                0x2D, 0x2E, 0x6F, 0x90}

# All standard system cursors that we replace with a blank one
CURSOR_IDS = [
    32512,  # arrow
    32513,  # I-beam
    32514,  # wait
    32515,  # crosshair
    32516,  # up arrow
    32642,  # size NW-SE
    32643,  # size NE-SW
    32644,  # size W-E
    32645,  # size N-S
    32646,  # size all
    32648,  # not allowed
    32649,  # hand
    32650,  # app starting
    32651,  # help
]

user32.CreateCursor.restype = wt.HANDLE
user32.CreateCursor.argtypes = [wt.HINSTANCE, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int,
                                ctypes.c_void_p, ctypes.c_void_p]
user32.SetSystemCursor.argtypes = [wt.HANDLE, wt.DWORD]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

hidden = False


# ---- Cursor hide / show ------------------------------------------------------
def make_blank_cursor():
    """Create a fully transparent 32x32 cursor."""
    and_mask = (ctypes.c_ubyte * 128)(*([0xFF] * 128))  # keep background
    xor_mask = (ctypes.c_ubyte * 128)(*([0x00] * 128))  # draw nothing
    return user32.CreateCursor(None, 0, 0, 32, 32, and_mask, xor_mask)


def hide_cursor():
    global hidden
    for cid in CURSOR_IDS:
        # SetSystemCursor takes ownership of the handle, so make a new one each time
        user32.SetSystemCursor(make_blank_cursor(), cid)
    hidden = True


def show_cursor():
    global hidden
    # Reloads the user's real cursor scheme from the registry
    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
    hidden = False


def toggle():
    if hidden:
        show_cursor()
    else:
        hide_cursor()


# ---- Keybind capture ---------------------------------------------------------
def is_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def any_key_down():
    return any(is_down(vk) for vk in range(0x08, 0xFF))


def describe(vk, mods):
    sc = user32.MapVirtualKeyW(vk, 0)  # VK -> scan code
    name = None
    if sc:
        lparam = sc << 16
        if vk in EXTENDED_VKS:
            lparam |= 1 << 24
        buf = ctypes.create_unicode_buffer(64)
        if user32.GetKeyNameTextW(lparam, buf, 64):
            name = buf.value
    if not name:
        name = f"VK 0x{vk:02X}"
    prefix = ""
    if mods & MOD_CONTROL:
        prefix += "Ctrl+"
    if mods & MOD_ALT:
        prefix += "Alt+"
    if mods & MOD_SHIFT:
        prefix += "Shift+"
    return prefix + name


def capture_keybind():
    """Wait for the user to press a key (optionally with Ctrl/Alt/Shift held)."""
    print("Press the key you want to use to hide/show the cursor.")
    print("(You can hold Ctrl / Alt / Shift while pressing it.)")

    # Wait until everything is released (e.g. the Enter used to start the script)
    while any_key_down():
        time.sleep(0.02)

    while True:
        for vk in range(0x08, 0xFF):
            if vk in FORBIDDEN_VKS:
                continue
            if is_down(vk):
                mods = 0
                if is_down(0x11):
                    mods |= MOD_CONTROL
                if is_down(0x12):
                    mods |= MOD_ALT
                if is_down(0x10):
                    mods |= MOD_SHIFT
                # Wait for release so the key press doesn't leak into anything
                while any_key_down():
                    time.sleep(0.02)
                return vk, mods
        time.sleep(0.01)


# ---- Main ---------------------------------------------------------------------
def main():
    atexit.register(show_cursor)

    while True:
        vk, mods = capture_keybind()
        label = describe(vk, mods)

        if vk == QUIT_VK and (mods & (MOD_CONTROL | MOD_ALT)) == (MOD_CONTROL | MOD_ALT):
            print("That's the quit combo, pick another key.\n")
            continue

        if user32.RegisterHotKey(None, HOTKEY_TOGGLE, mods | MOD_NOREPEAT, vk):
            print(f"\nKeybind set: {label}")
            break
        print(f"Could not register [{label}] (already used by another program?). Try another.\n")

    user32.RegisterHotKey(None, HOTKEY_QUIT, QUIT_MODS, QUIT_VK)
    print(f"Running. [{label}] toggles the cursor. Ctrl+Alt+Q quits.")
    print("This window will minimize now, leave it running.")

    time.sleep(1.5)
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, SW_MINIMIZE)

    # While hidden, re-apply the blank cursor ~4x per second so programs that
    # reset the cursor on mouse move can't bring it back.
    user32.SetTimer(None, 0, 250, None)

    msg = wt.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_TOGGLE:
                    toggle()
                elif msg.wParam == HOTKEY_QUIT:
                    break
            elif msg.message == WM_TIMER and hidden:
                hide_cursor()
    finally:
        user32.UnregisterHotKey(None, HOTKEY_TOGGLE)
        user32.UnregisterHotKey(None, HOTKEY_QUIT)
        show_cursor()


if __name__ == "__main__":
    main()
