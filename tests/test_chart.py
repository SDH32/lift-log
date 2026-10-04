"""Progress chart test: dragging across it doesn't select text, and tapping it leaves no outline
(the outline is only for keyboard focus). Run: python3 tests/test_chart.py (needs Playwright)."""
import datetime
from helpers import app, check, finish, SHOTS

start = datetime.datetime.combine(datetime.date.today().replace(day=1), datetime.time()).timestamp() * 1000
SEED = {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat'], 'templates': [], 'sessions': [
    {'name': 'Legs', 'start': start + i * 86400000, 'end': start + i * 86400000 + 3600000,
     'exercises': [{'name': 'Squat', 'sets': [{'weight': 200 + i * 10, 'reps': 5, 'done': True}]}]} for i in range(5)]}

outline = lambda page: page.locator('#chart svg').evaluate("e => getComputedStyle(e).outlineStyle")
selected = lambda page: page.evaluate("getSelection().toString()")

with app(seed=SEED) as page:
    page.click('nav button[data-tab=exercises]')
    page.click('text=Squat')
    page.wait_for_function("document.getAnimations().length === 0")  # let the slide-in finish
    box = page.locator('#chart svg').bounding_box()

    # Drag from the chart's left edge out past the text above it, like a finger sliding around
    page.mouse.move(box['x'] + 2, box['y'] + box['height'] - 8)
    page.mouse.down()
    page.mouse.move(box['x'] + box['width'] * 0.5, box['y'] + 20, steps=5)
    page.mouse.move(box['x'] + box['width'] - 4, box['y'] - 60, steps=5)
    page.mouse.up()
    check('dragging across the chart selects no text', selected(page) == '', repr(selected(page)))
    check('chart text is not selectable', page.locator('#chart').evaluate(
        "e => getComputedStyle(e).webkitUserSelect") == 'none')

    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    check('tooltip shows on tap', page.locator('#chart .tip').is_visible())
    check('no outline after tapping the chart', outline(page) == 'none', outline(page))
    page.screenshot(path=SHOTS / 'chart-tapped.png')

    # Keyboard users still see where focus is
    page.evaluate("document.activeElement.blur()")
    for _ in range(20):
        page.keyboard.press('Tab')
        if page.evaluate("document.activeElement.tagName") == 'svg': break
    check('keyboard focus reaches the chart', page.evaluate("document.activeElement.tagName") == 'svg')
    check('keyboard focus shows an outline', outline(page) != 'none', outline(page))

finish()
