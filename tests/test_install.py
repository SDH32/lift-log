"""Install/offline test: serves a copy of the app over http (the offline helper needs http).
Run: python3 tests/test_install.py (needs Playwright)."""
import functools, http.server, json, pathlib, shutil, socketserver, sys, tempfile, threading, time
from playwright.sync_api import sync_playwright
import helpers

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(tempfile.mkdtemp())
APP = SITE / 'lift-log'  # same sub-path as GitHub Pages
APP.mkdir()
for name in ['index.html', 'manifest.webmanifest', 'sw.js']: shutil.copy(ROOT / name, APP)
shutil.copytree(ROOT / 'icons', APP / 'icons')
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
Handler.log_message = lambda *a: None
# Threaded: WebKit can hold one connection open idle while it waits on another, which stalls a
# one-at-a-time server and makes the first page load time out now and then
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
server = Server(('localhost', 0), Handler)
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://localhost:{PORT}/lift-log/'

def server_down():  # like the connection dropping: nothing answers on the port
    global server
    server.shutdown(); server.server_close()

def server_up():
    global server
    server = Server(('localhost', PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

FAILED = []
def check(label, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + label, extra)
    if not cond: FAILED.append(label)
errors = []
with sync_playwright() as p:
    b = helpers.launch(p)
    ctx = b.new_context(viewport={'width': 412, 'height': 915}, has_touch=True, is_mobile=True,
                        user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36')
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(URL)
    page.evaluate("navigator.serviceWorker.ready"); page.reload()
    check('offline helper active', page.evaluate("!!navigator.serviceWorker.controller"))
    if helpers.BROWSER == 'chromium':  # these checks use Chrome's dev tools
        cdp = ctx.new_cdp_session(page)
        m = cdp.send('Page.getAppManifest')
        check('manifest loads without errors', not m.get('errors') and '"standalone"' in m.get('data', ''), m.get('errors') or '')
        inst = cdp.send('Page.getInstallabilityErrors')['installabilityErrors']
        check('Chrome considers it installable', inst == [], inst or '')
    for icon in ['icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png', 'icons/icon.svg']:
        r = page.request.get(URL + icon)
        check(f'{icon} served', r.ok and r.headers['content-type'].startswith('image/'))
    # Offline: the app still opens and works
    # Go offline. WebKit's test browser crashes if its offline switch is used with an offline
    # helper, so on WebKit the test server is switched off instead.
    if helpers.BROWSER == 'webkit': server_down()
    else: ctx.set_offline(True)
    page.reload()
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    check('opens and works offline', page.text_content('#title') == 'Workout' and page.locator('h2:text-is("Squat")').count() == 1)
    if helpers.BROWSER == 'webkit': server_up()
    else: ctx.set_offline(False)
    # Updates: a new version on the server shows up on the next online load
    time.sleep(1.2)  # the test server tracks changes to the second
    f = APP / 'index.html'
    html = open(f).read()
    open(f, 'w').write(html.replace('<title>Lift Log</title>', '<title>Lift Log v2</title>'))
    page.reload()
    check('new version shows up when online', page.title() == 'Lift Log v2', page.title())
    sw = page.request.get(URL + 'sw.js', headers={'Cache-Control': 'no-cache'})
    check('http cache bypassed for updates', 'no-cache' in sw.text())
    check('logged data survived', json.loads(page.evaluate("localStorage.getItem('liftlog.v1')"))['active']['exercises'][0]['name'] == 'Squat')
    b.close()
server.shutdown(); shutil.rmtree(SITE)
print('ERRORS:', errors or 'none')
sys.exit(1 if errors or FAILED else 0)
