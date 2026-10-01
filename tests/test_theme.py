"""Light/dark mode test: System default, manual choice, contrast, no flash. Run: python3 tests/test_theme.py"""
import json, time
from playwright.sync_api import sync_playwright
import helpers
from helpers import check, finish, sheet_ok, SHOTS

now = int(time.time() * 1000); D = 86400000
S = lambda w, r: {'weight': w, 'reps': r, 'done': True}
SEED = {'unit': 'lb', 'active': None, 'exercises': ['Bench Press'],
        'templates': [{'name': 'Push Day', 'exercises': ['Bench Press', 'Dips']}],
        'sessions': [{'name': 'Upper', 'start': now - (6 - i) * 2 * D, 'end': now - (6 - i) * 2 * D + 3600000,
                      'exercises': [{'name': 'Bench Press', 'sets': [S(155 + i * 5, 5)]}]} for i in range(6)]}

# WCAG contrast of the app's actual color pairs, read from the live CSS
CONTRAST = """() => {
  const v = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const lum = (h) => { const c = [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255)
    .map(x => x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const pairs = [['--text', '--bg', 4.5], ['--text', '--card', 4.5], ['--muted', '--bg', 4.5], ['--muted', '--card', 4.5],
    ['--accent', '--bg', 4.5], ['--accent', '--card', 4.5], ['#ffffff', '--accent-fill', 4.5], ['#ffffff', '--danger-fill', 4.5],
    ['--danger', '--card', 4.5], ['--ok', '--card', 4.5], ['--series-1', '--card', 3]];
  const col = (n) => n.startsWith('#') ? n : v(n);
  return pairs.map(([f, b, need]) => [f + ' on ' + b, +ratio(col(f), col(b)).toFixed(2), need]).filter(([, r, need]) => r < need);
}"""
mode = lambda page: page.evaluate("document.documentElement.dataset.theme")
meta = lambda page: page.get_attribute('meta[name=theme-color]', 'content')
bg = lambda page: page.evaluate("getComputedStyle(document.body).backgroundColor")

def open_app(b, scheme, seed=SEED):
    page = b.new_page(viewport={'width': 390, 'height': 844}, color_scheme=scheme, has_touch=True)
    page.on('pageerror', lambda e: helpers.ERRORS.append(str(e)))
    page.goto(helpers.URL)
    page.evaluate("s => { localStorage.clear(); if (s) localStorage.setItem('liftlog.v1', JSON.stringify(s)); }", seed)
    page.reload()
    return page

def saved_theme(page): return json.loads(page.evaluate("localStorage.getItem('liftlog.v1')"))['theme']

with sync_playwright() as p:
    b = helpers.launch(p)

    # The theme is applied by a script in <head>, before the page body is drawn (no flash)
    html = open(helpers.URL.replace('file://', '')).read()
    check('theme applied before page is drawn', html.index('applyTheme(savedTheme)') < html.index('<body>'))

    # System default follows the phone, including old data saved before this setting existed
    for scheme, expect, color in [('light', 'light', 'rgb(242, 243, 245)'), ('dark', 'dark', 'rgb(17, 20, 24)')]:
        page = open_app(b, scheme, seed=None)
        check(f'fresh install, phone in {scheme} mode: app is {expect}', mode(page) == expect and bg(page) == color)
        page.close()
    page = open_app(b, 'light')
    check('older saved data defaults to System', mode(page) == 'light' and 'theme' not in SEED)
    page.click('nav button[data-tab=settings]')
    check('Settings shows System selected', page.get_attribute('.seg button:text-is("System")', 'aria-pressed') == 'true')
    # System follows the phone switching modes while the app is open
    page.emulate_media(color_scheme='dark'); page.wait_for_timeout(100)
    check('System: follows phone switching to dark', mode(page) == 'dark' and meta(page) == '#111418')
    page.emulate_media(color_scheme='light'); page.wait_for_timeout(100)
    check('System: follows phone switching back to light', mode(page) == 'light' and meta(page) == '#f2f3f5')

    # Manual choice overrides the phone and survives a relaunch
    page.click('.seg button:text-is("Dark")')
    check('choosing Dark while phone is light', mode(page) == 'dark' and saved_theme(page) == 'dark' and meta(page) == '#111418')
    page.emulate_media(color_scheme='light'); page.wait_for_timeout(100)
    check('Dark stays dark when phone changes', mode(page) == 'dark')
    page.reload()
    check('Dark remembered after relaunch', mode(page) == 'dark')
    page.click('nav button[data-tab=settings]'); page.click('.seg button:text-is("Light")')
    page.emulate_media(color_scheme='dark'); page.wait_for_timeout(100)
    check('Light stays light when phone is dark', mode(page) == 'light' and saved_theme(page) == 'light')
    page.click('.seg button:text-is("System")')
    check('back to System follows phone again', mode(page) == 'dark' and saved_theme(page) == 'system')
    page.close()

    # Readability: every text/background pair in both modes passes WCAG AA
    for scheme in ['light', 'dark']:
        page = open_app(b, scheme)
        low = page.evaluate(CONTRAST)
        check(f'{scheme} mode: all color pairs readable', low == [], low)
        # Screenshots of each screen for a visual check
        shots = {}
        page.screenshot(path=SHOTS / f'theme-{scheme}-history.png'); 
        page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click(); page.wait_for_timeout(300)
        box = page.locator('#chart svg').bounding_box(); page.mouse.move(box['x'] + box['width'] * 0.6, box['y'] + 100)
        page.screenshot(path=SHOTS / f'theme-{scheme}-chart.png')
        page.click('nav button[data-tab=workout]'); page.locator('.card:has(h2:text-is("Push Day")) >> text=Start').click()
        page.locator('button:text-is("✓")').first.click(); page.wait_for_timeout(300)
        page.screenshot(path=SHOTS / f'theme-{scheme}-workout.png', full_page=True)
        page.click('button:text-is("Discard")'); page.wait_for_selector('#sheet.open'); page.wait_for_timeout(300)
        page.screenshot(path=SHOTS / f'theme-{scheme}-dialog.png')
        sheet_ok(page)
        page.click('nav button[data-tab=settings]'); page.wait_for_timeout(300)
        page.screenshot(path=SHOTS / f'theme-{scheme}-settings.png')
        page.close()

    # Import: a backup's theme is applied; an old backup without one means System
    page = open_app(b, 'light')
    page.click('nav button[data-tab=settings]')
    for theme, expect in [('dark', 'dark'), (None, 'light')]:
        data = dict(SEED, **({'theme': theme} if theme else {}))
        page.set_input_files('#import', files=[{'name': 'b.json', 'mimeType': 'application/json', 'buffer': json.dumps(data).encode()}])
        page.wait_for_selector('#sheet.open'); sheet_ok(page)
        check(f'import with theme={theme}: app is {expect}', mode(page) == expect)
    page.close()
    b.close()
finish()
