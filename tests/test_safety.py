"""Data safety and workout comfort: the backup reminder in Settings, asking the browser to keep the
app's data, and keeping the screen on during a workout. Run: python3 tests/test_safety.py"""
import datetime, json, time
from playwright.sync_api import sync_playwright
import helpers
from helpers import check, finish, sheet_ok

DAY = 86400000
now = int(time.time() * 1000)
month1 = int(datetime.datetime.combine(datetime.date.today().replace(day=1), datetime.time(7)).timestamp() * 1000)
SESSION = {'name': 'Legs', 'start': month1, 'end': month1 + 3600000,
           'exercises': [{'name': 'Squat', 'sets': [{'weight': 225, 'reps': 5, 'done': True}]}]}
def seed(**kw): return {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat'], 'templates': [], 'sessions': [SESSION], **kw}

# Stand-ins for the phone's screen-on lock, storage, and share sheet; they record what the app asks for
FAKES = """
window.__wl = { attempts: 0, granted: 0, released: 0, deny: false, last: null };
Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: async () => {
  __wl.attempts++;
  if (__wl.deny) throw new DOMException('denied', 'NotAllowedError');
  __wl.granted++;
  const lock = new EventTarget(); lock.released = false;
  lock.release = async () => { if (!lock.released) { lock.released = true; __wl.released++; lock.dispatchEvent(new Event('release')); } };
  return __wl.last = lock;
}}});
window.__persist = 0;
Object.defineProperty(navigator, 'storage', { configurable: true, value: { persist: async () => { __persist++; return true; } } });
window.__share = 'ok';
Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
Object.defineProperty(navigator, 'share', { configurable: true, value: async () => { if (__share !== 'ok') throw new DOMException('x', __share); } });
"""


def open_app(b, data, phone=False):
    page = b.new_page(viewport={'width': 390, 'height': 844}, has_touch=phone, is_mobile=phone, accept_downloads=True)
    page.on('pageerror', lambda e: helpers.ERRORS.append(str(e)))
    page.add_init_script(FAKES)
    page.goto(helpers.URL)
    page.evaluate("s => localStorage.setItem('liftlog.v1', JSON.stringify(s))", data); page.reload()
    return page


wl = lambda page: page.evaluate("({ ...__wl, held: !!__wl.last && !__wl.last.released })")
stored = lambda page: json.loads(page.evaluate("localStorage.getItem('liftlog.v1')"))


def backup_line(page):
    page.click('nav button[data-tab=settings]')
    el = page.locator('#view .card', has_text='Backup').locator('p.warn, p.muted').nth(1)
    return (el.text_content(), el.get_attribute('class')) if el.count() else (None, None)


with sync_playwright() as p:
    b = helpers.launch(p)

    # ---- Backup reminder
    page = open_app(b, seed())
    check('asks the browser to keep the data', page.evaluate("__persist") == 1)
    check('never backed up, with workouts: orange note', backup_line(page) == ('Not backed up yet.', 'warn'), backup_line(page))
    with page.expect_download(): page.click('button:text-is("Export")')
    check('export records the time', abs(stored(page)['lastBackup'] - now) < 60000)
    check('after export: "today", not orange', backup_line(page) == ('Last backup: today.', 'muted'), backup_line(page))
    page.close()

    page = open_app(b, seed(sessions=[]))
    check('nothing logged yet: no backup note', page.click('nav button[data-tab=settings]') or
          page.locator('#view .card', has_text='Backup').locator('p').count() == 1)
    page.close()

    for days, want in [(1, ('Last backup: yesterday.', 'muted')), (29, ('Last backup: 29 days ago.', 'muted')),
                       (30, ('Last backup: 30 days ago.', 'warn')), (45, ('Last backup: 45 days ago.', 'warn'))]:
        at = int(datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=days), datetime.time(12)).timestamp() * 1000)
        page = open_app(b, seed(lastBackup=at))
        check(f'{days} days: {want[0]} ({want[1]})', backup_line(page) == want, backup_line(page))
        page.close()

    # Phone: a closed share sheet isn't a backup; a completed share is
    page = open_app(b, seed(), phone=True)
    page.click('nav button[data-tab=settings]')
    page.evaluate("__share = 'AbortError'"); page.click('button:text-is("Export")'); page.wait_for_timeout(300)
    check('closing the share sheet records nothing', stored(page).get('lastBackup') is None and backup_line(page)[0] == 'Not backed up yet.')
    page.evaluate("__share = 'ok'"); page.click('button:text-is("Export")'); page.wait_for_timeout(300)
    check('sharing the file counts as a backup', backup_line(page)[0] == 'Last backup: today.')
    page.close()

    # ---- Screen stays on during a workout
    page = open_app(b, seed())
    check('no workout: screen allowed to sleep', wl(page)['granted'] == 0)
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.wait_for_function("__wl.granted === 1")
    for name in ['Squat', 'Bench Press']: page.fill('#new-ex', name); page.press('#new-ex', 'Enter')
    page.wait_for_timeout(200)
    check('workout started: screen kept on (one lock, not one per redraw)', wl(page)['granted'] == 1 and wl(page)['held'], wl(page))
    # The phone drops the lock when the app goes to the background; coming back takes it again
    page.evaluate("__wl.last.release()")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function("__wl.granted === 2")
    check('back from the background: screen kept on again', wl(page)['held'])
    page.reload(); page.wait_for_function("__wl.granted >= 1")
    check('reopening the app mid-workout keeps the screen on', wl(page)['held'])
    page.locator('td button', has_text='✓').first.click()
    page.click('text=Finish'); page.wait_for_timeout(300)
    check('workout finished: screen allowed to sleep again', not wl(page)['held'] and wl(page)['released'] >= 1, wl(page))
    page.close()

    # Refused (e.g. low power mode): carries on without retrying in a loop
    page = open_app(b, seed())
    page.evaluate("__wl.deny = true")
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.wait_for_timeout(500)
    attempts = wl(page)['attempts']
    check('refused lock: app works, no retry loop', 1 <= attempts <= 3 and page.locator('#new-ex').count() == 1, attempts)
    page.close()

    b.close()
finish()
