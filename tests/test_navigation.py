"""Browser test for navigation, back handling, and dialogs. Run: python3 tests/test_navigation.py"""
import json, time
from helpers import app, check, data, finish, sheet_ok, sheet_cancel, sheet_title, sheet_open, toast, title, SHOTS

DAY = 86400000
now = int(time.time() * 1000)
def S(w, r): return {'weight': w, 'reps': r, 'done': True}
LIFTS = ['Squat', 'Bench Press', 'Deadlift', 'Overhead Press', 'Barbell Row', 'Pull-up', 'Dips', 'Lunge', 'Curl', 'Lat Pulldown']
SEED = {'unit': 'lb', 'active': None, 'exercises': LIFTS, 'templates': [],
        'sessions': [{'name': f'Day {i}', 'start': now - (10 - i) * DAY, 'end': now - (10 - i) * DAY + 3600000,
                      'exercises': [{'name': n, 'sets': [S(100 + i * 5, 5)]} for n in LIFTS]} for i in range(6)]}
depth = lambda page: page.evaluate("history.state && history.state.depth")
view_anim = lambda page: page.get_attribute('#view', 'class') or ''

with app(seed=SEED) as page:
    url = page.url
    # Sub-screen: header, back target, animation, and browser/Android back
    page.click('nav button[data-tab=exercises]')
    check('root tab has no back button', page.is_hidden('#back') and title(page) == 'Exercises')
    page.mouse.wheel(0, 1200); page.wait_for_timeout(200)
    y_before = page.evaluate('scrollY')
    page.locator('.card:has(h2:text-is("Lat Pulldown"))').click()
    check('detail: title + back label', title(page) == 'Lat Pulldown' and page.text_content('#back') == '‹ Exercises')
    check('detail slides in', 'anim-push' in view_anim(page))
    check('detail scrolled to top', page.evaluate('scrollY') == 0)
    page.screenshot(path=SHOTS / 'nav-1-detail.png')
    page.go_back()  # same event as Android back / iOS swipe in Safari
    page.wait_for_function("document.querySelector('#title').textContent === 'Exercises'")
    check('back returns to list and slides back', 'anim-pop' in view_anim(page))
    check('scroll position restored', abs(page.evaluate('scrollY') - y_before) < 5)
    check('history back at root', depth(page) == 0 and page.url == url)

    # Header back button does the same
    page.locator('.card:has(h2:text-is("Squat"))').click(); page.click('#back')
    page.wait_for_function("document.querySelector('#title').textContent === 'Exercises'")
    check('header back works', depth(page) == 0)

    # Switching tabs from a sub-screen unwinds history (no dead back presses later)
    page.locator('.card:has(h2:text-is("Squat"))').click()
    page.click('nav button[data-tab=settings]')
    page.wait_for_function("document.querySelector('#title').textContent === 'Settings'")
    check('tab switch from sub-screen clears history', depth(page) == 0)
    page.click('nav button[data-tab=exercises]')
    check('returning to tab shows its root', title(page) == 'Exercises')

    # Dialog + back: back closes the dialog as "cancel" and stays put
    page.click('nav button[data-tab=history]')
    n = len(data(page)['sessions'])
    page.locator('button:text-is("Delete")').first.click()
    check('delete asks first', sheet_open(page) and sheet_title(page) == 'Delete this workout?')
    check('dialog focuses its button', page.evaluate("document.activeElement.id") == 'sheet-ok')
    check('page behind dialog is inert', page.evaluate("document.querySelector('main').inert"))
    page.screenshot(path=SHOTS / 'dlg-3-delete.png')
    page.go_back(); page.wait_for_selector('#sheet', state='hidden')
    check('back closes dialog without deleting', len(data(page)['sessions']) == n and title(page) == 'History' and depth(page) == 0)
    check('page usable again after close', not page.evaluate("document.querySelector('main').inert"))
    # Escape and backdrop also cancel
    page.locator('button:text-is("Delete")').first.click(); page.keyboard.press('Escape'); page.wait_for_selector('#sheet', state='hidden')
    page.locator('button:text-is("Delete")').first.click(); page.mouse.click(195, 100); page.wait_for_selector('#sheet', state='hidden')
    check('escape/backdrop cancel', len(data(page)['sessions']) == n)
    # Double-tapping the confirm button only goes back once
    page.locator('button:text-is("Delete")').first.click()
    page.dblclick('#sheet-ok'); page.wait_for_selector('#sheet', state='hidden'); page.wait_for_timeout(300)
    check('double-tap deletes once, stays on page', len(data(page)['sessions']) == n - 1 and page.url == url and title(page) == 'History')

    # Editor with unsaved changes + hardware back
    page.click('nav button[data-tab=settings]'); page.click('text=+ New template')
    page.fill('#tpl-name', 'Draft')
    page.go_back(); page.wait_for_selector('#sheet.open')
    check('back from edited template asks', sheet_title(page) == 'Discard changes?' and page.is_visible('#tpl-name'))
    page.go_back(); page.wait_for_selector('#sheet', state='hidden')
    check('back again = keep editing', page.input_value('#tpl-name') == 'Draft' and depth(page) == 1)
    page.click('nav button[data-tab=workout]'); page.wait_for_selector('#sheet.open')
    check('tab switch from edited template asks', sheet_title(page) == 'Discard changes?')
    sheet_ok(page)
    page.wait_for_function("document.querySelector('#title').textContent === 'Workout'")
    check('discard then lands on chosen tab', depth(page) == 0 and data(page)['templates'] == [])

    # Finish workout toast
    page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    page.click('button:text-is("✓")'); page.click('button:text-is("Finish")')
    check('finish shows toast and history', toast(page, 'Workout saved') and title(page) == 'History')
    page.screenshot(path=SHOTS / 'dlg-4-toast.png')

    # Import: bad file -> toast; good file -> confirm -> replaced
    page.click('nav button[data-tab=settings]')
    page.set_input_files('#import', files=[{'name': 'bad.json', 'mimeType': 'application/json', 'buffer': b'not json'}])
    check('bad import file', toast(page, "Couldn't read that file."))
    good = dict(SEED, sessions=SEED['sessions'][:2])
    page.set_input_files('#import', files=[{'name': 'good.json', 'mimeType': 'application/json', 'buffer': json.dumps(good).encode()}])
    page.wait_for_selector('#sheet.open')
    check('import asks to replace', sheet_title(page) == 'Replace all data?' and '2 workouts' in page.text_content('#sheet-msg'))
    sheet_ok(page)
    check('import replaced data', len(data(page)['sessions']) == 2)

    # Reload while in a sub-screen starts cleanly at a root screen
    page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click()
    page.reload()
    check('reload lands on a root screen', page.is_hidden('#back') and depth(page) == 0)

# Back animation: iOS animates its own back swipe, so system backs there must not slide again
def anims(page):
    page.wait_for_timeout(50)  # let any animation start
    return page.evaluate("document.querySelector('#view').getAnimations().length")

def open_editor(page):
    page.click('nav button[data-tab=settings]'); page.click('text=+ New template'); page.wait_for_timeout(300)

with app(seed=SEED, ios=True) as page:
    open_editor(page); page.go_back()
    page.wait_for_function("document.querySelector('#title').textContent === 'Settings'")
    check('iOS system back (swipe): no extra slide', anims(page) == 0)
    open_editor(page); page.click('#back')
    page.wait_for_function("document.querySelector('#title').textContent === 'Settings'")
    check('iOS header back: slides', anims(page) == 1)

with app(seed=SEED) as page:
    open_editor(page); page.go_back()
    page.wait_for_function("document.querySelector('#title').textContent === 'Settings'")
    check('Android/system back elsewhere: slides', anims(page) == 1)

# Edge swipe (home-screen app only)
TOUCH = """(seq) => {
  const t = (x) => new Touch({ identifier: 1, target: document.body, clientX: x, clientY: 400 });
  for (const [type, x] of seq)
    document.body.dispatchEvent(new TouchEvent(type, { touches: type === 'touchstart' ? [t(x)] : [], changedTouches: [t(x)], bubbles: true }));
}"""
with app(seed=SEED, ios=True) as page:
    page.add_init_script("Object.defineProperty(navigator, 'standalone', { value: true })")
    page.reload()
    url = page.url
    # iOS took over the gesture (touchcancel): the app must not go back as well
    page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click()
    page.evaluate(TOUCH, [['touchstart', 6], ['touchcancel', 160], ['touchend', 160]]); page.wait_for_timeout(300)
    check('touchcancel: no extra back', depth(page) == 1 and title(page) != 'Exercises')
    # A system back during the swipe: the swipe's own back must not fire too
    page.evaluate(TOUCH, [['touchstart', 6]]); page.go_back()
    page.wait_for_function("document.querySelector('#title').textContent === 'Exercises'")
    page.evaluate(TOUCH, [['touchend', 160]]); page.wait_for_timeout(300)
    check('system back mid-swipe: only one back', page.url == url and title(page) == 'Exercises' and depth(page) == 0)

with app(seed=SEED) as page:
    page.add_init_script("Object.defineProperty(navigator, 'standalone', { value: true })")
    page.reload()
    page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click()
    page.evaluate("""() => {
      const t = (x) => new Touch({ identifier: 1, target: document.body, clientX: x, clientY: 400 });
      document.body.dispatchEvent(new TouchEvent('touchstart', { touches: [t(6)], changedTouches: [t(6)], bubbles: true }));
      document.body.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(160)], bubbles: true }));
    }""")
    page.wait_for_function("document.querySelector('#title').textContent === 'Exercises'")
    check('edge swipe goes back', depth(page) == 0)

finish()
