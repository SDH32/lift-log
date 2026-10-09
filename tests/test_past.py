"""Past workouts: edit a logged workout from History, or log a forgotten one by tapping a rest day.
Run: python3 tests/test_past.py (needs Playwright)."""
import datetime
from helpers import app, check, data, finish, sheet_ok, sheet_cancel, sheet_open, sheet_title, title, toast, SHOTS

today = datetime.date.today()
month1 = today.replace(day=1)
H = 3600000


def ts(day, hour): return int(datetime.datetime.combine(day, datetime.time(hour)).timestamp() * 1000)
def S(w, r, done=True): return {'weight': w, 'reps': r, 'done': done}


SQUAT_DAY = month1  # the 1st of this month, 7 am, 45 minutes
SEED = {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat', 'Bench Press', 'Pull-up'],
        'templates': [{'name': 'Legs', 'exercises': ['Squat']}],
        'sessions': [{'name': 'Legs', 'start': ts(SQUAT_DAY, 7), 'end': ts(SQUAT_DAY, 7) + 45 * 60000,
                      'exercises': [{'name': 'Squat', 'sets': [S(225, 5), S(225, 5), S(245, 3, done=False)]}]}]}
titles = lambda page: page.locator('#view .card h2').all_text_contents()
ready = lambda page: page.wait_for_function("document.getAnimations().length === 0")


def open_edit(page, name):
    page.locator('#view .card', has_text=name).get_by_role('button', name='Edit').click(); ready(page)


with app(seed=SEED) as page:
    page.click('nav button[data-tab=history]')

    # ---- Edit an existing workout
    open_edit(page, 'Legs')
    check('Edit opens the workout editor', title(page) == 'Edit workout')
    check('editor shows date and minutes', page.input_value('#past-date') == SQUAT_DAY.isoformat() and page.input_value('#past-min') == '45',
          (page.input_value('#past-date'), page.input_value('#past-min')))
    weights = page.locator('td input[placeholder="BW"]')
    check('only sets that were done are shown', weights.count() == 2, weights.count())
    check('no done ticks when editing a past workout', page.locator('#view button', has_text='✓').count() == 0)
    page.screenshot(path=SHOTS / 'past-edit.png')

    weights.nth(1).fill('235'); weights.nth(1).dispatch_event('change')
    page.fill('input[placeholder^="Workout name"]', 'Heavy legs')
    page.click('#view button:text-is("Save")')
    check('save says so', toast(page, 'Workout updated'))
    s = data(page)['sessions'][0]
    check('edited weight saved', [x['weight'] for x in s['exercises'][0]['sets']] == [225, 235], s['exercises'][0]['sets'])
    check('edited name saved', s['name'] == 'Heavy legs')
    check('same day keeps the real start time', s['start'] == ts(SQUAT_DAY, 7) and s['end'] == s['start'] + 45 * 60000)
    check('back on History after saving', title(page) == 'History' and 'Heavy legs' in titles(page))

    # ---- Unsaved changes are guarded, on Cancel and on system back
    open_edit(page, 'Heavy legs')
    page.fill('#past-min', '50')
    page.click('#view button:text-is("Cancel")')
    check('cancel with changes asks first', sheet_open(page) and sheet_title(page) == 'Discard changes?')
    sheet_cancel(page)
    check('keep editing stays in the editor', title(page) == 'Edit workout' and page.input_value('#past-min') == '50')
    page.go_back()
    check('system back with changes asks too', sheet_open(page) and sheet_title(page) == 'Discard changes?')
    sheet_ok(page); page.wait_for_function("document.querySelector('#title').textContent === 'History'")
    check('discard leaves the workout unchanged', data(page)['sessions'][0]['end'] - data(page)['sessions'][0]['start'] == 45 * 60000)
    open_edit(page, 'Heavy legs'); page.click('#view button:text-is("Cancel")')
    page.wait_for_function("document.querySelector('#title').textContent === 'History'")
    check('cancel without changes just leaves', not sheet_open(page))

    # ---- Moving it to another day uses 6 pm on that day
    if today.day >= 3:
        open_edit(page, 'Heavy legs')
        new_day = month1.replace(day=2)
        page.fill('#past-date', new_day.isoformat()); page.dispatch_event('#past-date', 'change')
        page.click('#view button:text-is("Save")'); toast(page, 'Workout updated')
        s = data(page)['sessions'][0]
        check('new date starts at 6 pm that day', s['start'] == ts(new_day, 18) and s['end'] == s['start'] + 45 * 60000)
    else:
        print('SKIP move-date check (needs day 3+ of the month)')

    # ---- Log a forgotten workout by tapping a rest day
    future = today + datetime.timedelta(days=1)
    if future.month == today.month:
        check('future days stay disabled', page.locator(f'.cal .day >> text="{future.day}"').first.is_disabled())
    rest = today if today.day >= 3 else None
    if rest is None: print('SKIP rest-day logging (needs day 3+ of the month)')
    else:
        page.locator(f'.cal .day >> text="{rest.day}"').first.click()
        check('tapping a rest day offers to log one', sheet_open(page) and sheet_title(page) == 'Log a workout?')
        sheet_ok(page); ready(page)
        check('opens Log workout with that date', title(page) == 'Log workout' and page.input_value('#past-date') == rest.isoformat())
        check('templates offered for a new past workout', page.locator('#view button', has_text='Legs').count() == 1)
        page.screenshot(path=SHOTS / 'past-log.png')
        page.click('#view button:text-is("Save")')
        check('saving with no sets is refused', toast(page, 'Add at least one set') and title(page) == 'Log workout')
        page.locator('#view button', has_text='Legs').click()
        check('template fills lifts, prefilled from last time', page.input_value('td input[placeholder="BW"] >> nth=1') == '235')
        page.fill('#new-ex', 'Pull-up'); page.press('#new-ex', 'Enter')
        reps = page.locator('#view .card', has_text='Pull-up').locator('input[inputmode=numeric]')
        reps.fill('8'); reps.dispatch_event('change')
        page.fill('#past-min', '30'); page.dispatch_event('#past-min', 'input')
        page.click('#view button:text-is("Save")')
        check('logging says so', toast(page, 'Workout added'))
        ss = data(page)['sessions']
        added = [x for x in ss if x['name'] == 'Legs'][0]
        check('logged workout saved with all sets done', len(ss) == 2 and all(x['done'] for e in added['exercises'] for x in e['sets'])
              and [e['name'] for e in added['exercises']] == ['Squat', 'Pull-up'], added)
        check('logged workout lands on that day, before now', datetime.date.fromtimestamp(added['start'] / 1000) == rest
              and added['end'] - added['start'] == 30 * 60000 and added['end'] <= datetime.datetime.now().timestamp() * 1000 + 1000)
        check('sessions kept in date order', [x['start'] for x in ss] == sorted(x['start'] for x in ss))
        check('calendar shows the new day', page.locator(f'.cal .day.has >> text="{rest.day}"').count() == 1)
        page.screenshot(path=SHOTS / 'past-after.png')

    # ---- A live workout is never touched by editing a past one
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Bench Press'); page.press('#new-ex', 'Enter')
    page.click('nav button[data-tab=history]'); open_edit(page, 'Heavy legs')
    page.fill('#new-ex', 'Bench Press'); page.press('#new-ex', 'Enter')
    reps = page.locator('#view .card', has_text='Bench Press').locator('input[inputmode=numeric]')
    reps.fill('5'); reps.dispatch_event('change')
    page.click('#view button:text-is("Save")'); toast(page, 'Workout updated')
    d = data(page)
    check('live workout unchanged by past edit', [e['name'] for e in d['active']['exercises']] == ['Bench Press'], d['active'])
    check('past edit added its lift', 'Bench Press' in [e['name'] for e in d['sessions'][0]['exercises']])

finish()
