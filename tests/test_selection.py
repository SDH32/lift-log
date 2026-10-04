"""Text selection test: dragging a finger around the app selects nothing (like a native app),
but text fields still select so you can edit and paste. Run: python3 tests/test_selection.py"""
import datetime
from helpers import app, check, finish

start = datetime.datetime.combine(datetime.date.today().replace(day=1), datetime.time()).timestamp() * 1000
SEED = {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat'], 'templates': [], 'sessions': [
    {'name': 'Legs', 'start': start, 'end': start + 3600000,
     'exercises': [{'name': 'Squat', 'sets': [{'weight': 225, 'reps': 5, 'done': True}]}]}]}

selected = lambda page: page.evaluate("getSelection().toString()")


def drag(page, sel, frm=(0.05, 0.02), to=(0.9, 0.95)):
    page.wait_for_function("document.getAnimations().length === 0")
    page.evaluate("getSelection().removeAllRanges()")
    b = page.locator(sel).first.bounding_box()
    page.mouse.move(b['x'] + b['width'] * frm[0], b['y'] + b['height'] * frm[1])
    page.mouse.down()
    page.mouse.move(b['x'] + b['width'] * to[0], b['y'] + b['height'] * to[1], steps=8)
    page.mouse.up()
    return selected(page)


with app(seed=SEED) as page:
    page.click('nav button[data-tab=history]')
    s = drag(page, '#view .card')
    check('dragging over the calendar selects nothing', s == '', repr(s[:60]))
    s = drag(page, '#view .card >> nth=1')
    check('dragging over a past workout selects nothing', s == '', repr(s[:60]))
    page.keyboard.press('ControlOrMeta+a')
    check('select-all outside a field selects nothing', selected(page) == '', repr(selected(page)[:60]))

    s = drag(page, '#title', (0.0, 0.5), (1.0, 0.5))
    check('dragging over the screen title selects nothing', s == '', repr(s[:60]))

    # Fields still select: needed to fix a typo or retype a number
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    name = page.locator('input[placeholder^="Workout name"]')
    name.fill('Leg day'); name.click(); page.keyboard.press('ControlOrMeta+a')
    check('workout name field selects its text',
          name.evaluate("e => e.selectionEnd - e.selectionStart") == len('Leg day'))
    weight = page.locator('td input[placeholder="BW"]').first
    weight.fill('135'); weight.click(); page.keyboard.press('ControlOrMeta+a'); page.keyboard.type('145')
    check('weight field can be selected and retyped', weight.input_value() == '145', weight.input_value())
    for f in ['input[placeholder^="Workout name"]', 'td input[placeholder="BW"]', '#new-ex']:
        us = page.locator(f).first.evaluate("e => getComputedStyle(e).webkitUserSelect")
        check(f'{f} allows selection', us != 'none', us)

finish()
