"""Real Android checks: the phone's back key against the live app in Android Chrome.
Run: sh tests/android/start_emulator.sh, then python3 tests/android/test_android_back.py"""
import time
from playwright.sync_api import sync_playwright
from adbui import sh, shot
results = []
def check(label, cond, extra=''):
    results.append(cond); print(('PASS ' if cond else 'FAIL ') + label, '' if cond else extra)
def real_back(page, wait_title=None):
    sh('shell', 'input', 'keyevent', 'KEYCODE_BACK')  # the phone's actual back key
    if wait_title: page.wait_for_function("t => document.querySelector('#title').textContent === t", arg=wait_title, timeout=5000)
    else: page.wait_for_timeout(800)
now = int(time.time() * 1000); D = 86400000
S = lambda w, r: {'weight': w, 'reps': r, 'done': True}
SEED = {'unit': 'lb', 'active': None, 'exercises': ['Bench Press'], 'theme': 'system',
        'templates': [{'name': 'Push Day', 'exercises': ['Bench Press', 'Dips']}],
        'sessions': [{'name': 'Upper', 'start': now - (6 - i) * 2 * D, 'end': now - (6 - i) * 2 * D + 3600000,
                      'exercises': [{'name': 'Bench Press', 'sets': [S(155 + i * 5, 5)]}]} for i in range(6)]}
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp('http://localhost:9222')
    page = next(pg for c in b.contexts for pg in c.pages if 'lift-log' in pg.url)
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    page.evaluate("s => localStorage.setItem('liftlog.v1', JSON.stringify(s))", SEED); page.reload()
    depth = lambda: page.evaluate("history.state && history.state.depth")
    title = lambda: page.text_content('#title')
    print('device:', page.evaluate('navigator.userAgent')[:60], '| screen', page.evaluate('innerWidth'), 'x', page.evaluate('innerHeight'))

    page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click(); page.wait_for_timeout(400)
    check('chart opens', title() == 'Bench Press' and depth() == 1)
    shot('/tmp/shots/android-chart.png')
    real_back(page, 'Exercises')
    check('Android back: chart -> Exercises list', title() == 'Exercises' and depth() == 0)

    page.click('nav button[data-tab=history]')
    n = len(page.evaluate("JSON.parse(localStorage.getItem('liftlog.v1')).sessions"))
    page.locator('button:text-is("Delete")').first.click(); page.wait_for_selector('#sheet.open'); page.wait_for_timeout(300)
    shot('/tmp/shots/android-dialog.png')
    real_back(page); page.wait_for_selector('#sheet', state='hidden')
    check('Android back: closes dialog without deleting', title() == 'History' and depth() == 0
          and len(page.evaluate("JSON.parse(localStorage.getItem('liftlog.v1')).sessions")) == n)

    page.click('nav button[data-tab=settings]'); page.click('text=+ New template'); page.fill('#tpl-name', 'Draft'); page.wait_for_timeout(300)
    real_back(page); page.wait_for_selector('#sheet.open')
    check('Android back: edited template asks before discarding', page.text_content('#sheet-title') == 'Discard changes?' and page.is_visible('#tpl-name'))
    real_back(page); page.wait_for_selector('#sheet', state='hidden')
    check('Android back again: keeps editing', page.input_value('#tpl-name') == 'Draft' and depth() == 1)
    page.click('button:text-is("Cancel")'); page.wait_for_selector('#sheet.open'); page.click('#sheet-ok')
    page.wait_for_function("document.querySelector('#title').textContent === 'Settings'")
    check('discard returns to Settings', depth() == 0)

    print('ERRORS:', errors or 'none')
    b.close()
print(f'{sum(results)}/{len(results)} passed')
raise SystemExit(0 if all(results) else 1)
