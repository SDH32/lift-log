"""History list test: shows only the calendar's month, a tapped day narrows it to that day.
Run: python3 tests/test_history.py (needs Playwright)."""
import datetime, json
from helpers import app, check, data, finish, sheet_ok

today = datetime.date.today()
this_month = today.replace(day=1)
last_month = (this_month - datetime.timedelta(days=1)).replace(day=1)
two_ago = (last_month - datetime.timedelta(days=1)).replace(day=1)


def session(name, day, hour=18):
    t = datetime.datetime.combine(day, datetime.time(hour)).timestamp() * 1000
    return {'name': name, 'start': t, 'end': t + 3600000,
            'exercises': [{'name': 'Squat', 'sets': [{'weight': 225, 'reps': 5, 'done': True}]}]}


SEED = {'unit': 'lb', 'theme': 'system', 'active': None, 'exercises': ['Squat'], 'templates': [], 'sessions': [
    session('Old legs', two_ago.replace(day=5)),
    session('Push A', last_month.replace(day=3)),
    session('Pull A', last_month.replace(day=10), 7),
    session('Legs A', last_month.replace(day=10), 18),
    session('Now push', this_month)]}


def titles(page): return page.locator('#view .card h2').all_text_contents()
def month_name(d): return d.strftime('%B')


with app(seed=SEED) as page:
    page.click('nav button[data-tab=history]')
    check('opens on this month: only its workout listed', titles(page) == ['Now push'], titles(page))

    page.click('[aria-label="Previous month"]')
    check('previous month lists its workouts, newest first', titles(page) == ['Legs A', 'Pull A', 'Push A'], titles(page))

    page.click('[aria-label="Previous month"]')
    check('two months back lists only that month', titles(page) == ['Old legs'], titles(page))

    page.click('[aria-label="Previous month"]')
    check('empty month says so', titles(page) == [] and f'No workouts in {month_name(two_ago - datetime.timedelta(days=1))}' in page.text_content('#view'),
          page.text_content('#view')[-200:])

    page.click('[aria-label="Next month"]'); page.click('[aria-label="Next month"]')
    page.click('.cal .day.has >> text="10"')
    check('tapping a day shows just that day', titles(page) == ['Legs A', 'Pull A'], titles(page))
    back = page.locator('#view button', has_text=f'All of {month_name(last_month)}')
    check('day filter offers going back to the whole month', back.count() == 1)
    back.click()
    check('back to the whole month', titles(page) == ['Legs A', 'Pull A', 'Push A'], titles(page))

    page.click('.cal .day.has >> text="3"')
    page.click('[aria-label="Next month"]')
    check('changing month drops the day filter', titles(page) == ['Now push'] and page.locator('.cal .day.sel').count() == 0, titles(page))

    # Delete still removes the right workout when the list is filtered
    page.click('[aria-label="Previous month"]')
    page.locator('#view .card', has_text='Pull A').get_by_role('button', name='Delete').click()
    sheet_ok(page)
    names = [s['name'] for s in data(page)['sessions']]
    check('delete removes the workout shown', 'Pull A' not in names and len(names) == 4, names)
    check('list stays on that month after delete', titles(page) == ['Legs A', 'Push A'], titles(page))

finish()
