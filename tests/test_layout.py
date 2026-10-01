"""Layout across screen sizes: small phones, phone sideways, iPad. Run: python3 tests/test_layout.py"""
import time
from playwright.sync_api import sync_playwright
import helpers
from helpers import check, finish, SHOTS

SIZES = {'iphone-se-320': (320, 568), 'android-360': (360, 740), 'iphone-390': (390, 844),
         'phone-landscape': (844, 390), 'ipad-portrait': (820, 1180), 'ipad-landscape': (1180, 820)}
now = int(time.time() * 1000); D = 86400000
S = lambda w, r: {'weight': w, 'reps': r, 'done': True}
SEED = {'unit': 'lb', 'active': None, 'exercises': ['Bench Press'],
        'templates': [{'name': 'Push Day', 'exercises': ['Bench Press', 'Overhead Press']}],
        'sessions': [{'name': 'Upper', 'start': now - (6 - i) * 2 * D, 'end': now - (6 - i) * 2 * D + 3600000,
                      'exercises': [{'name': 'Bench Press', 'sets': [S(155 + i * 5, 5)]}]} for i in range(6)]}

MEASURE = """() => {
  const r = (el) => el.getBoundingClientRect();
  const card = document.querySelector('main .card');
  const tabs = [...document.querySelectorAll('nav button')];
  return {
    overflow: document.documentElement.scrollWidth > innerWidth,
    cutTabs: tabs.filter(b => b.scrollWidth > b.clientWidth).map(b => b.textContent),
    titleLeft: r(document.querySelector('#title')).left,
    cardLeft: card ? r(card).left : null, cardRight: card ? r(card).right : null,
    tabsLeft: r(tabs[0]).left, tabsRight: r(tabs.at(-1)).right,
  };
}"""

with sync_playwright() as p:
    b = helpers.launch(p)
    for name, (w, h) in SIZES.items():
        page = b.new_page(viewport={'width': w, 'height': h}, has_touch=True)
        page.on('pageerror', lambda e: helpers.ERRORS.append(str(e)))
        page.goto(helpers.URL)
        page.evaluate("s => localStorage.setItem('liftlog.v1', JSON.stringify(s))", SEED); page.reload()
        screens = {}
        screens['history'] = page.evaluate(MEASURE)
        page.click('nav button[data-tab=exercises]'); page.locator('.card').first.click(); page.wait_for_timeout(300)
        screens['chart'] = page.evaluate(MEASURE)
        page.click('nav button[data-tab=workout]'); page.locator('.card:has(h2:text-is("Push Day")) >> text=Start').click(); page.wait_for_timeout(300)
        check(f'{name}: workout has set rows to measure', page.locator('input[placeholder=BW]').count() == 2)
        screens['workout'] = page.evaluate(MEASURE)
        page.screenshot(path=SHOTS / f'ff-{name}-workout.png')
        for screen, m in screens.items():
            tag = f'{name} {screen}:'
            check(f'{tag} nothing spills off-screen', not m['overflow'])
            check(f'{tag} no tab label cut off', not m['cutTabs'], m['cutTabs'])
            # Title sits 4px inside the cards' left edge at every width (16px header vs 12px main padding)
            check(f'{tag} title lines up with content', abs(m['titleLeft'] - m['cardLeft'] - 4) < 1, m)
            check(f'{tag} tabs within content column', m['tabsLeft'] >= m['cardLeft'] - 13 and m['tabsRight'] <= m['cardRight'] + 13, m)
        page.close()
    b.close()
finish()
