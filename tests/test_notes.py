"""Notes: one per workout and one per lift, written while logging or later via Edit; shown in History,
marked on the progress chart (ring + tooltip) and in its table. Run: python3 tests/test_notes.py"""
import datetime
from helpers import app, check, data, finish, sheet_ok, sheet_cancel, sheet_open, sheet_title, title, toast, SHOTS

month1 = datetime.date.today().replace(day=1)
def ts(i): return int(datetime.datetime.combine(month1, datetime.time(6 + i)).timestamp() * 1000)
def session(i, w, **extra):
    return {'name': 'Legs', 'start': ts(i), 'end': ts(i) + 1800000, **extra,
            'exercises': [{'name': 'Squat', 'sets': [{'weight': w, 'reps': 5, 'done': True}]}]}


SEED = {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat', 'Pull-up'], 'templates': [],
        'sessions': [session(0, 225), session(1, 185), session(2, 235)]}
ready = lambda page: page.wait_for_function("document.getAnimations().length === 0")


def write_note(page, button, text):
    button.click()
    sheet_ok(page, text)


with app(seed=SEED) as page:
    # ---- While logging
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    add = page.locator('#view button.note-btn')
    check('workout and lift each offer "+ Add note"', add.count() == 2 and add.first.text_content() == '+ Add note')
    add.nth(1).click()
    check('note dialog names the lift', sheet_open(page) and sheet_title(page) == 'Squat note')
    sheet_cancel(page)
    check('cancel adds nothing', 'note' not in data(page)['active']['exercises'][0])
    write_note(page, page.locator('#view .card', has_text='Squat').locator('button.note-btn'), 'Shoulder pain')
    write_note(page, page.locator('#view .card').first.locator('button.note-btn'), 'Bad sleep <b>')
    a = data(page)['active']
    check('lift note saved', a['exercises'][0].get('note') == 'Shoulder pain', a['exercises'][0])
    check('workout note saved', a.get('note') == 'Bad sleep <b>', a.get('note'))
    check('notes shown in place of the button', page.locator('#view button.note-btn.note').all_text_contents() == ['Bad sleep <b>', 'Shoulder pain'])
    page.screenshot(path=SHOTS / 'notes-live.png')
    # Edit, then clear one
    write_note(page, page.locator('#view button.note-btn.note', has_text='Shoulder pain'), 'Shoulder pain, went light')
    check('editing a note replaces it', data(page)['active']['exercises'][0]['note'] == 'Shoulder pain, went light')
    page.locator('#view button.note-btn.note', has_text='Bad sleep').click()
    check('dialog starts with the current note', page.input_value('#sheet-input') == 'Bad sleep <b>')
    sheet_ok(page, '')
    check('clearing the text removes the note', 'note' not in data(page)['active'])
    write_note(page, page.locator('#view .card').first.locator('button.note-btn'), 'Deload week')
    reps = page.locator('td input[inputmode=numeric]').first; reps.fill('5'); reps.dispatch_event('change')
    w = page.locator('td input[placeholder="BW"]').first; w.fill('135'); w.dispatch_event('change')
    page.locator('#view button', has_text='✓').first.click()
    page.click('text=Finish'); toast(page, 'Workout saved')
    s = data(page)['sessions'][-1]
    check('notes kept when the workout is finished', s.get('note') == 'Deload week' and s['exercises'][0].get('note') == 'Shoulder pain, went light', s)

    # ---- In History
    card = page.locator('#view .card', has_text='Deload week')
    check('History shows both notes', card.locator('.note').all_text_contents() == ['Deload week', 'Shoulder pain, went light'],
          card.locator('.note').all_text_contents())
    check('lift without a note still lists its sets on their own line',
          page.locator('#view .card:not(:has(.note))').filter(has_text='Squat').first.locator('b + br').count() == 1)
    page.screenshot(path=SHOTS / 'notes-history.png')

    # ---- Added later through Edit (the dip on the 2nd session)
    page.locator('#view .card', has_text='185×5').get_by_role('button', name='Edit').click(); ready(page)
    write_note(page, page.locator('#view .card', has_text='Squat').locator('button.note-btn'), 'Deloaded')
    page.go_back()
    check('unsaved note counts as a change', sheet_open(page) and sheet_title(page) == 'Discard changes?')
    sheet_cancel(page)
    page.click('#view button:text-is("Save")'); toast(page, 'Workout updated')
    check('note added later is saved', data(page)['sessions'][1]['exercises'][0].get('note') == 'Deloaded')

    # ---- On the chart
    page.click('nav button[data-tab=exercises]'); page.click('text=Squat'); ready(page)
    check('noted sessions get a ring', page.locator('#chart circle.noted').count() == 2, page.locator('#chart circle.noted').count())
    ring = page.locator('#chart circle.noted').first.bounding_box()
    page.mouse.move(ring['x'] + ring['width'] / 2, ring['y'] + ring['height'] / 2)
    tip = page.locator('#chart .tip')
    check('tooltip shows the lift note', tip.is_visible() and 'Deloaded' in tip.text_content(), tip.text_content())
    page.screenshot(path=SHOTS / 'notes-chart.png')
    last = page.locator('#chart circle.noted').last.bounding_box()
    page.mouse.move(last['x'] + last['width'] / 2, last['y'] + last['height'] / 2)
    check('tooltip shows lift and workout notes', page.locator('#chart .tip .tip-note').all_text_contents() == ['Shoulder pain, went light', 'Deload week'],
          page.locator('#chart .tip .tip-note').all_text_contents())
    page.click('text=Show table')
    check('table lists notes', 'Deloaded' in page.text_content('.data-table') and 'Deload week' in page.text_content('.data-table'))

finish()
