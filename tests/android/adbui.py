"""Tiny helper for driving the Android emulator: read the screen's UI tree, tap by visible text."""
import re, subprocess, time
import os
SDK = os.environ.get('ANDROID_HOME', '/opt/homebrew/share/android-commandlinetools')
ADB = os.path.join(SDK, 'platform-tools', 'adb')
def sh(*a): return subprocess.run([ADB, *a], capture_output=True, text=True).stdout
def nodes():
    sh('shell', 'rm', '-f', '/sdcard/ui.xml'); sh('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
    xml = sh('shell', 'cat', '/sdcard/ui.xml')
    out = []
    for m in re.finditer(r'<node [^>]*>', xml):
        n = m.group(0)
        g = lambda k: (re.search(k + r'="([^"]*)"', n) or [None, ''])[1]
        b = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', g('bounds'))
        if b: out.append({'text': g('text'), 'desc': g('content-desc'), 'id': g('resource-id'), 'b': tuple(map(int, b.groups()))})
    return out
def texts(): return [n['text'] or n['desc'] for n in nodes() if n['text'] or n['desc']]
def tap_text(t, exact=False, wait=10):
    end = time.time() + wait
    while time.time() < end:
        for n in nodes():
            label = n['text'] or n['desc']
            if label and (label == t if exact else t.lower() in label.lower()):
                x1, y1, x2, y2 = n['b']; sh('shell', 'input', 'tap', str((x1 + x2) // 2), str((y1 + y2) // 2)); return label
        time.sleep(1)
    raise SystemExit(f'not found on screen: {t!r}; visible: {texts()[:15]}')
def back(): sh('shell', 'input', 'keyevent', 'KEYCODE_BACK')
def shot(path): open(path, 'wb').write(subprocess.run([ADB, 'exec-out', 'screencap', '-p'], capture_output=True).stdout)
