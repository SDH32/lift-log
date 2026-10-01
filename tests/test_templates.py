"""Browser test for templates. Run: python3 tests/test_templates.py (needs Playwright)."""
import json
from playwright.sync_api import sync_playwright
import pathlib, sys
URL = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
SHOTS = pathlib.Path('/tmp/shots'); SHOTS.mkdir(exist_ok=True)
errors, dialogs = [], []
answers = []  # queue of responses for prompt/confirm
def on_dialog(d):
    dialogs.append(f'{d.type}: {d.message}')
    a = answers.pop(0) if answers else True
    if d.type == 'prompt': d.accept(a) if a is not False else d.dismiss()
    elif d.type == 'confirm': d.accept() if a else d.dismiss()
    else: d.accept()
def st(page): return json.loads(page.evaluate("localStorage.getItem('liftlog.v1')") or 'null')
FAILED = []
def check(label, cond):
    print(('PASS ' if cond else 'FAIL ') + label)
    if not cond: FAILED.append(label)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('dialog', on_dialog)
    page.goto(URL); page.evaluate("localStorage.clear()"); page.reload()

    # Create a new template from Settings
    page.click('nav button[data-tab=settings]')
    check('empty state shown', page.locator('text=No templates yet.').count() == 1)
    page.click('text=+ New template')
    page.click('text=Save template')
    check('blocks save with no name', 'Give the template a name.' in dialogs[-1])
    page.fill('#tpl-name', 'Push Day')
    page.click('text=Save template')
    check('blocks save with no exercises', 'Add at least one exercise.' in dialogs[-1])
    for ex in ['Bench Press', 'Overhead Press', 'Cable Fly']:
        page.fill('#tpl-ex', ex); page.press('#tpl-ex', 'Enter')
    check('focus stays in add box', page.evaluate("document.activeElement.id") == 'tpl-ex')
    page.locator('.tpl-row').nth(2).locator('button[aria-label="Move up"]').click()   # Cable Fly up
    check('first up / last down disabled',
          page.locator('.tpl-row').nth(0).locator('button[aria-label="Move up"]').is_disabled() and
          page.locator('.tpl-row').nth(2).locator('button[aria-label="Move down"]').is_disabled())
    page.screenshot(path=SHOTS / 'tpl-1-editor.png', full_page=True)
    page.click('text=Save template')
    s = st(page)
    check('template saved in order', s['templates'] == [{'name': 'Push Day', 'exercises': ['Bench Press', 'Cable Fly', 'Overhead Press']}])
    check('new exercise added to autocomplete list', 'Cable Fly' in s['exercises'])

    # Save a manually entered workout as a template (existing flow still works)
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    page.fill('#new-ex', 'Leg Press'); page.press('#new-ex', 'Enter')
    answers[:] = ['Leg Day']
    page.click('text=Save as template')
    check('save-from-workout still works', st(page)['templates'][1] == {'name': 'Leg Day', 'exercises': ['Squat', 'Leg Press']})
    answers[:] = [True]; page.click('button:text-is("Discard")')

    page.click('nav button[data-tab=settings]')
    page.screenshot(path=SHOTS / 'tpl-2-settings.png', full_page=True)

    # Edit: rename to a clashing name, then fix and remove an exercise
    page.locator('.tpl-row:has-text("Leg Day") >> text=Edit').click()
    page.fill('#tpl-name', 'push day')
    page.click('text=Save template')
    check('blocks duplicate name (case-insensitive)', 'already a template called "Push Day"' in dialogs[-1])
    page.fill('#tpl-name', 'Legs')
    page.locator('.tpl-row:has-text("Leg Press") button[aria-label="Remove"]').click()
    check('name kept after re-render', page.input_value('#tpl-name') == 'Legs')
    page.click('text=Save template')
    check('edit saved in place', st(page)['templates'][1] == {'name': 'Legs', 'exercises': ['Squat']})

    # Cancel with unsaved changes: decline the prompt (stay), then accept it (discard)
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click()
    page.fill('#tpl-name', 'Changed')
    answers[:] = [False]; page.click('button:text-is("Cancel")')
    check('declining discard keeps editor open', page.locator('#tpl-name').count() == 1)
    answers[:] = [True]; page.click('button:text-is("Cancel")')
    check('discarding leaves template unchanged', st(page)['templates'][1]['name'] == 'Legs')
    # Cancel with no changes asks nothing
    n = len(dialogs)
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click(); page.click('text=‹ Settings')
    check('no prompt when nothing changed', len(dialogs) == n)

    # Delete from editor
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click()
    answers[:] = [True]; page.click('text=Delete template')
    check('template deleted', [t['name'] for t in st(page)['templates']] == ['Push Day'])

    # Workout tab: Edit jumps to editor; Start uses the edited order
    page.click('nav button[data-tab=workout]')
    page.screenshot(path=SHOTS / 'tpl-3-workout-tab.png', full_page=True)
    page.locator('.card:has(h2:text-is("Push Day")) >> text=Edit').click()
    check('Edit on workout tab opens editor', page.input_value('#tpl-name') == 'Push Day')
    page.click('nav button[data-tab=workout]')
    page.locator('.card:has(h2:text-is("Push Day")) >> text=Start').click()
    check('start uses template order', [e['name'] for e in st(page)['active']['exercises']] == ['Bench Press', 'Cable Fly', 'Overhead Press'])

    # Calendar rest days not dimmed by the new disabled-button style
    page.evaluate("""() => { const s = JSON.parse(localStorage.getItem('liftlog.v1')); s.active = null;
      s.sessions = [{name:'x', start: Date.now(), end: Date.now(), exercises: []}]; localStorage.setItem('liftlog.v1', JSON.stringify(s)); }""")
    page.reload(); page.click('nav button[data-tab=history]')
    check('calendar rest days not dimmed', page.locator('.cal .day:disabled').first.evaluate("e => getComputedStyle(e).opacity") == '1')
    b.close()
print('ERRORS:', errors or 'none')
sys.exit(1 if errors or FAILED else 0)
