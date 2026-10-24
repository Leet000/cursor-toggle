# Cursor Toggle

Hide or show the Windows mouse cursor with a hotkey of your choice.
Useful for screenshots, recording and games.

## How to use
1. Download `cursor_toggle.exe` from the Releases page.
2. Run it and press the key you want to use. (I suggest running as administrator so it works while game is in fullscreen.)
3. Press that key to hide or show the cursor.
4. Press Ctrl+Alt+Q to quit.

## Notes
- If your game runs as administrator, run this as administrator too.
- Games that draw their own cursor can't be affected.
- Windows or antivirus may warn about the exe because it is unsigned.
  You can read the source code in this repository or build it yourself:
  `py -m PyInstaller --onefile cursor_toggle.py`
