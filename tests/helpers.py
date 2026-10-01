"""Shared helpers for the browser tests (Playwright, iPhone-sized viewport)."""
import json, pathlib
from contextlib import contextmanager
from playwright.sync_api import sync_playwright

URL = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
SHOTS = pathlib.Path('/tmp/shots'); SHOTS.mkdir(exist_ok=True)
FAILED, ERRORS = [], []
IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 '
             '(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1')


def check(label, cond):
    print(('PASS ' if cond else 'FAIL ') + label)
    if not cond: FAILED.append(label)


@contextmanager
def app(fresh=True, seed=None, ios=False):
    with sync_playwright() as p:
        b = p.chromium.launch()
        ua = {'user_agent': IPHONE_UA} if ios else {}
        page = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, **ua)
        page.on('pageerror', lambda e: ERRORS.append(str(e)))
        page.on('dialog', lambda d: (ERRORS.append(f'native {d.type}: {d.message}'), d.dismiss()))
        page.goto(URL)
        if fresh: page.evaluate("localStorage.clear()")
        if seed is not None: page.evaluate("s => localStorage.setItem('liftlog.v1', JSON.stringify(s))", seed)
        page.reload()
        try: yield page
        finally: b.close()


def data(page): return json.loads(page.evaluate("localStorage.getItem('liftlog.v1')") or 'null')
def title(page): return page.text_content('#title')
def sheet_open(page): return page.locator('#sheet.open').count() == 1
def sheet_title(page): return page.text_content('#sheet-title')
def _answer(page, button):
    # Wait until this dialog is gone, or a follow-up dialog (different title) has replaced it
    before = sheet_title(page)
    page.click(button)
    page.wait_for_function("t => document.querySelector('#sheet').hidden || "
                           "(document.querySelector('#sheet-title').textContent !== t && !document.querySelector('#sheet-ok').disabled)", arg=before)


def sheet_ok(page, text=None):
    if text is not None: page.fill('#sheet-input', text)
    _answer(page, '#sheet-ok')


def sheet_cancel(page): _answer(page, '#sheet-cancel')


def toast(page, expect):
    """True once the toast shows `expect` (or text containing it); False if it never does."""
    try:
        page.wait_for_function("t => { const el = document.querySelector('#toast');"
                               " return el.classList.contains('show') && el.textContent.includes(t); }", arg=expect, timeout=3000)
        return True
    except Exception:
        print('   toast was:', repr(page.text_content('#toast')))
        return False


def finish():
    print('ERRORS:', ERRORS or 'none')
    raise SystemExit(1 if ERRORS or FAILED else 0)
