"""UI details: set summaries, done-set rows, the Exercises list, calendar tint, aligned numbers.
Run: python3 tests/test_polish.py (needs Playwright)."""
import datetime, time
from helpers import app, check, finish

month1 = datetime.date.today().replace(day=1)
t0 = int(datetime.datetime.combine(month1, datetime.time(7)).timestamp() * 1000)
def S(w, r, done=True): return {'weight': w, 'reps': r, 'done': done}
SEED = {'unit': 'lb', 'theme': 'dark', 'exercises': ['Squat', 'Pull-up'], 'templates': [],
        'active': {'name': 'Legs', 'start': int(time.time() * 1000), 'exercises': [{'name': 'Squat', 'sets': [S(225, 5), S(225, 5, done=False)]}]},
        'sessions': [{'name': 'Legs', 'start': t0, 'end': t0 + 3600000, 'exercises': [
            {'name': 'Squat', 'sets': [S(225, 5), S(225, 5), S(225, 4), S(245, 3), S(200, 8, done=False)]},
            {'name': 'Pull-up', 'sets': [S(None, 12), S(None, 10)]}]}]}

with app(seed=SEED) as page:
    cases = [
        ([S(225, 5), S(225, 5), S(225, 4)], '225 × 5, 5, 4'),
        ([S(225, 5), S(245, 3), S(225, 5)], '225 × 5 · 245 × 3 · 225 × 5'),
        ([S(None, 12), S(None, 10)], 'BW × 12, 10'),
        ([S(315, 1)], '315 × 1'),
    ]
    for sets, want in cases:
        got = page.evaluate("s => fmtSets(s)", sets)
        check(f'summary {want!r}', got == want, got)

    # Live workout: a ticked set's fields lose their box; pending ones keep it
    done_bg = page.locator('tr.done input').first.evaluate("e => getComputedStyle(e).backgroundColor")
    open_bg = page.locator('tr:not(.done) input[placeholder="BW"]').first.evaluate("e => getComputedStyle(e).backgroundColor")
    check('done set fields have no box, open ones do', done_bg == 'rgba(0, 0, 0, 0)' and open_bg != done_bg, (done_bg, open_bg))
    check('"last time" hint uses the summary', '225 × 5, 5, 4 · 245 × 3' in page.text_content('#view'))

    page.click('nav button[data-tab=history]')
    lift = page.locator('#view .lift').first
    check('History shows done sets only, summarized', lift.locator('.sets').text_content() == '225 × 5, 5, 4 · 245 × 3', lift.text_content())
    has = page.locator('.cal .day.has').first
    bg = has.evaluate("e => getComputedStyle(e).backgroundColor")
    tint = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent-tint').trim()")
    check('workout days use the soft tint', bg == 'rgb(36, 65, 106)' and tint == '#24416a', (bg, tint))
    check('numbers line up (tabular figures)', page.evaluate("getComputedStyle(document.body).fontVariantNumeric") == 'tabular-nums')

    page.click('nav button[data-tab=exercises]')
    rows = page.locator('#view .card.list .list-row')
    check('Exercises is one list, a row per lift', page.locator('#view .card').count() == 1 and rows.count() == 2, rows.count())
    sq = page.locator('.list-row[data-name="Squat"] .best')
    check('weighted lift shows its best est. 1RM (245×3 → 270)', sq.text_content().strip() == '270 lbest. 1RM', sq.text_content())
    pu = page.locator('.list-row[data-name="Pull-up"] .best')
    check('bodyweight lift shows max reps', pu.text_content().strip() == '12max reps', pu.text_content())
    # Alphabetical, ignoring case, regardless of when each lift was last done
    order = page.evaluate('''(() => {
      state.sessions.push({ name: 'x', start: Date.now() - 1000, end: Date.now(), exercises: [
        { name: 'bench press', sets: [{ weight: 135, reps: 5, done: true }] },
        { name: 'Zercher Squat', sets: [{ weight: 135, reps: 5, done: true }] }] });
      render();
      return [...document.querySelectorAll('.list-row')].map(r => r.dataset.name);
    })()''')
    check('lifts listed alphabetically, ignoring case', order == ['bench press', 'Pull-up', 'Squat', 'Zercher Squat'], order)
    page.locator('.list-row[data-name="Pull-up"]').click()
    page.wait_for_function("document.querySelector('#title').textContent === 'Pull-up'")
    check('row opens the progress chart', page.locator('#chart svg').count() == 1)

finish()
