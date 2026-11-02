"""Lift housekeeping: rename or merge a lift, "Add exercise" suggestions that only list what's
logged, and the new-best callout when a workout is finished. Run: python3 tests/test_lifts.py"""
import datetime, time
from helpers import app, check, data, finish, sheet_ok, sheet_cancel, sheet_open, sheet_title, title, toast

month1 = datetime.date.today().replace(day=1)
def ts(h): return int(datetime.datetime.combine(month1, datetime.time(h)).timestamp() * 1000)
def S(w, r, done=True): return {'weight': w, 'reps': r, 'done': done}
def W(h, *exercises, **kw): return {'name': 'W', 'start': ts(h), 'end': ts(h) + 3600000, 'exercises': list(exercises), **kw}
def E(name, *sets, **kw): return {'name': name, 'sets': list(sets), **kw}

ready = lambda page: page.wait_for_function("document.getAnimations().length === 0")
names_in = lambda d: sorted({e['name'] for w in d['sessions'] + [d['active'] or {'exercises': []}] for e in w['exercises']})
suggestions = lambda page: page.evaluate("[...document.querySelectorAll('#exercise-list option')].map(o => o.value)")


def open_lift(page, name):
    page.click('nav button[data-tab=exercises]'); page.click(f'.list-row[data-name="{name}"]'); ready(page)


def rename(page, to):
    page.click('#view button:text-is("Rename")')
    check_title = sheet_title(page)
    sheet_ok(page, to)
    return check_title


# ---------------------------------------------------------------- rename and merge
SEED = {'unit': 'lb', 'theme': 'system', 'templates': [{'name': 'Push', 'exercises': ['Bench', 'Dips', 'Bench Press']}],
        'active': {'name': 'Now', 'start': int(time.time() * 1000), 'exercises': [E('Bench', S(135, 5, False))]},
        'sessions': [W(6, E('Bench Press', S(185, 5))),
                     W(7, E('Bench', S(175, 5), note='Paused reps'), E('Squat', S(225, 5)), E('Bench Press', S(185, 3), note='Shoulder ok')),
                     W(8, E('Bench', S(180, 5)), E('Dips', S(None, 12)))]}

with app(seed=SEED) as page:
    check('suggestions list only logged/template lifts, A–Z', suggestions(page) == ['Bench', 'Bench Press', 'Dips', 'Squat'], suggestions(page))

    open_lift(page, 'Squat')
    check('rename dialog names the lift', rename(page, 'Back Squat') == 'Rename Squat')
    check('plain rename says so', toast(page, 'Renamed to Back Squat'))
    d = data(page)
    check('renamed in every workout', 'Squat' not in names_in(d) and 'Back Squat' in names_in(d), names_in(d))
    check('chart screen follows the new name', title(page) == 'Back Squat' and page.locator('#chart svg').count() == 1)

    open_lift(page, 'Bench')
    page.click('#view button:text-is("Rename")'); sheet_ok(page, 'bench press')
    check('existing name asks to merge', sheet_open(page) and sheet_title(page) == 'Merge into Bench Press?')
    sheet_cancel(page)
    check('cancel merge changes nothing', 'Bench' in names_in(data(page)) and title(page) == 'Bench')

    page.click('#view button:text-is("Rename")'); sheet_ok(page, 'bench press'); sheet_ok(page)
    check('merge says so', toast(page, 'Merged into Bench Press'))
    d = data(page)
    check('merged everywhere, keeping the existing spelling', 'Bench' not in names_in(d) and 'bench press' not in names_in(d), names_in(d))
    both = d['sessions'][1]['exercises']
    check('a workout with both keeps one entry with all sets, in place', [e['name'] for e in both] == ['Bench Press', 'Back Squat']
          and [x['weight'] for x in both[0]['sets']] == [175, 185], both)
    check('notes from both are kept', both[0].get('note') == 'Paused reps; Shoulder ok', both[0].get('note'))
    check('live workout renamed too', [e['name'] for e in d['active']['exercises']] == ['Bench Press'])
    check('template renamed without a duplicate', d['templates'][0]['exercises'] == ['Bench Press', 'Dips'], d['templates'][0])
    check('one history now: chart shows all three Bench workouts', title(page) == 'Bench Press'
          and page.locator('#chart circle:not(.noted):not(.hover-dot)').count() == 3)
    page.click('nav button[data-tab=exercises]')
    check('Exercises list has one entry for it', page.locator('.list-row').evaluate_all("rs => rs.map(r => r.dataset.name)") == ['Back Squat', 'Bench Press', 'Dips'])
    check('suggestions drop the old names', suggestions(page) == ['Back Squat', 'Bench Press', 'Dips'], suggestions(page))

    open_lift(page, 'Dips')
    page.click('#view button:text-is("Rename")'); sheet_cancel(page)
    page.click('#view button:text-is("Rename")'); sheet_ok(page, '')
    check('cancel or empty name changes nothing', 'Dips' in names_in(data(page)) and title(page) == 'Dips')

# ---------------------------------------------------------------- suggestions
with app(seed={'unit': 'lb', 'theme': 'system', 'templates': [], 'active': None, 'sessions': [], 'exercises': ['Benhc Typo']}) as page:
    s = suggestions(page)
    check('nothing logged yet: starter list, not old saved names', 'Squat' in s and 'Benhc Typo' not in s and len(s) == 10, s)
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Sled Push'); page.press('#new-ex', 'Enter')
    check('a lift in the live workout is suggested', suggestions(page) == ['Sled Push'], suggestions(page))
    check('old saved name list is dropped from stored data', 'exercises' not in data(page), list(data(page)))
    page.click('text=Discard'); sheet_ok(page)
    check('discarded workout: its lift drops off again', 'Sled Push' not in suggestions(page))
    page.click('nav button[data-tab=settings]'); page.click('text=+ New template')
    page.fill('#tpl-ex', 'Cable Fly'); page.press('#tpl-ex', 'Enter')
    check('lift in a template being edited is suggested', 'Cable Fly' in suggestions(page))

# ---------------------------------------------------------------- new bests
NOW = int(time.time() * 1000)
def live(*exercises): return {'name': 'Today', 'start': NOW - 3600000, 'exercises': list(exercises)}
HIST = [W(6, E('Squat', S(225, 5)), E('Pull-up', S(None, 10)))]  # Squat est. 1RM 263

def finish_with(active):
    with app(seed={'unit': 'lb', 'theme': 'system', 'templates': [], 'sessions': HIST, 'active': active}) as page:
        page.click('nav button[data-tab=workout]'); page.click('text=Finish')
        if sheet_open(page): sheet_ok(page)
        page.wait_for_function("document.querySelector('#toast').classList.contains('show')")
        return page.text_content('#toast')

msg = finish_with(live(E('Squat', S(235, 5)), E('Pull-up', S(None, 12)), E('Bench Press', S(135, 5))))
check('beating earlier workouts calls out each new best', msg == 'Workout saved · New bests 🎉\nSquat: 274 lb est. 1RM\nPull-up: 12 reps', msg)
check("a lift's first workout isn't a record", 'Bench' not in msg)
msg = finish_with(live(E('Squat', S(225, 5)), E('Pull-up', S(None, 10))))
check('matching (not beating) a best: plain message', msg == 'Workout saved', msg)
msg = finish_with(live(E('Squat', S(225, 5), S(315, 5, done=False))))
check('unticked sets never count', msg == 'Workout saved', msg)
msg = finish_with(live(E('squat', S(230, 5))))
check('one new best, lift name in any case', msg == 'Workout saved · New best 🎉\nsquat: 268 lb est. 1RM', msg)

finish()
