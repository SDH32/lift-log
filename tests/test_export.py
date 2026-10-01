"""Export/backup test: share sheet on phones, download elsewhere, and a full round trip.
Run: python3 tests/test_export.py (needs Playwright)."""
import datetime, json, pathlib, tempfile
from playwright.sync_api import sync_playwright
import helpers
from helpers import check, finish, sheet_ok, toast

TODAY = datetime.date.today().isoformat()  # local date, like the app's file name
SEED = {'unit': 'lb', 'active': None, 'exercises': ['Squat'], 'templates': [{'name': 'Legs', 'exercises': ['Squat']}],
        'sessions': [{'name': 'Legs', 'start': 1.7e12, 'end': 1.7e12 + 3600000,
                      'exercises': [{'name': 'Squat', 'sets': [{'weight': 225, 'reps': 5, 'done': True}]}]}]}
# Stand-in share sheet: records what the app hands it; behaviour set per test via window.__share
FAKE_SHARE = """
window.__shared = []; window.__share = { can: true, result: 'ok' };
Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => window.__share.can });
Object.defineProperty(navigator, 'share', { configurable: true, value: async ({ files }) => {
  window.__shared.push({ name: files[0].name, type: files[0].type, text: await files[0].text() });
  if (window.__share.result !== 'ok') throw new DOMException('test', window.__share.result);
}});
"""

def open_app(b, phone):
    opts = dict(viewport={'width': 390, 'height': 844}, has_touch=phone, is_mobile=phone, accept_downloads=True)
    page = b.new_page(**opts)
    page.on('pageerror', lambda e: helpers.ERRORS.append(str(e)))
    page.add_init_script(FAKE_SHARE)
    page.goto(helpers.URL)
    page.evaluate("s => localStorage.setItem('liftlog.v1', JSON.stringify(s))", SEED); page.reload()
    page.click('nav button[data-tab=settings]')
    downloads = []
    page.on('download', lambda d: downloads.append(d))
    return page, downloads

def stored(page): return json.loads(page.evaluate("localStorage.getItem('liftlog.v1')"))

with sync_playwright() as p:
    b = p.chromium.launch()

    # Phone: Export hands the backup to the share sheet
    page, downloads = open_app(b, phone=True)
    check('dark color scheme declared (no white flashes on iOS)',
          page.evaluate("getComputedStyle(document.documentElement).colorScheme") == 'dark'
          and page.locator('meta[name=color-scheme][content=dark]').count() == 1)
    check('phone counts as touch screen', page.evaluate("matchMedia('(pointer: coarse)').matches"))
    page.click('button:text-is("Export")'); page.wait_for_timeout(300)
    shared = page.evaluate("window.__shared")
    check('phone: opens share sheet with one file', len(shared) == 1 and not downloads)
    check('phone: file name uses local date', shared and shared[0]['name'] == f'liftlog-{TODAY}.json', shared and shared[0]['name'])
    check('phone: file is the full backup', shared and shared[0]['type'] == 'application/json' and json.loads(shared[0]['text']) == stored(page))
    # Closing the share sheet: nothing else happens
    page.evaluate("window.__share.result = 'AbortError'")
    page.click('button:text-is("Export")'); page.wait_for_timeout(300)
    check('phone: closing share sheet does nothing else', not downloads and not page.is_visible('#toast.show'))
    # Share sheet fails for another reason: fall back to a download
    page.evaluate("window.__share.result = 'NotAllowedError'")
    with page.expect_download() as d: page.click('button:text-is("Export")')
    check('phone: share error falls back to download', d.value.suggested_filename == f'liftlog-{TODAY}.json')
    # File type not shareable (Android doesn't allow .json): download instead
    page.evaluate("window.__share = { can: false, result: 'ok' }; window.__shared = []")
    with page.expect_download() as d: page.click('button:text-is("Export")')
    check('phone: unshareable file downloads instead', d.value.suggested_filename == f'liftlog-{TODAY}.json' and page.evaluate("window.__shared.length") == 0)
    page.close()

    # Computer: Export downloads, and the file imports back intact
    page, downloads = open_app(b, phone=False)
    with page.expect_download() as d: page.click('button:text-is("Export")')
    path = pathlib.Path(tempfile.mkdtemp()) / d.value.suggested_filename
    d.value.save_as(path)
    check('computer: downloads (no share sheet)', page.evaluate("window.__shared.length") == 0)
    backup = json.loads(path.read_text())
    check('computer: download is the full backup', backup == SEED)
    page.evaluate("localStorage.setItem('liftlog.v1', JSON.stringify({unit:'kg', sessions:[], active:null, exercises:[], templates:[]}))")
    page.reload(); page.click('nav button[data-tab=settings]')
    page.set_input_files('#import', str(path)); page.wait_for_selector('#sheet.open'); sheet_ok(page)
    check('round trip: import restores everything', stored(page) == SEED and toast(page, 'Data imported'))
    page.close()
    b.close()
finish()
