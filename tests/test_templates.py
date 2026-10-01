"""Browser test for templates. Run: python3 tests/test_templates.py (needs Playwright)."""
from helpers import app, check, data, finish, sheet_ok, sheet_cancel, sheet_title, sheet_open, toast, title, SHOTS

with app() as page:
    # Create a new template from Settings
    page.click('nav button[data-tab=settings]')
    check('empty state shown', page.locator('text=No templates yet.').count() == 1)
    page.click('text=+ New template')
    check('header shows New template with back to Settings', title(page) == 'New template' and page.text_content('#back') == '‹ Settings')
    page.click('text=Save template')
    check('blocks save with no name', toast(page, 'Give the template a name.'))
    page.fill('#tpl-name', 'Push Day')
    page.click('text=Save template')
    check('blocks save with no exercises', toast(page, 'Add at least one exercise.'))
    for ex in ['Bench Press', 'Overhead Press', 'Cable Fly']:
        page.fill('#tpl-ex', ex); page.press('#tpl-ex', 'Enter')
    check('focus stays in add box', page.evaluate("document.activeElement.id") == 'tpl-ex')
    page.locator('.tpl-row').nth(2).locator('button[aria-label="Move up"]').click()
    check('first up / last down disabled',
          page.locator('.tpl-row').nth(0).locator('button[aria-label="Move up"]').is_disabled() and
          page.locator('.tpl-row').nth(2).locator('button[aria-label="Move down"]').is_disabled())
    page.screenshot(path=SHOTS / 'tpl-1-editor.png', full_page=True)
    page.click('text=Save template')
    check('save shows toast', toast(page, 'Saved "Push Day"'))
    check('back on Settings after save', title(page) == 'Settings')
    s = data(page)
    check('template saved in order', s['templates'] == [{'name': 'Push Day', 'exercises': ['Bench Press', 'Cable Fly', 'Overhead Press']}])
    check('new exercise added to autocomplete list', 'Cable Fly' in s['exercises'])

    # Save a manually entered workout as a template
    page.click('nav button[data-tab=workout]'); page.click('text=Start empty workout')
    page.fill('#new-ex', 'Squat'); page.press('#new-ex', 'Enter')
    page.fill('#new-ex', 'Leg Press'); page.press('#new-ex', 'Enter')
    page.click('text=Save as template')
    check('save-as-template sheet lists exercises', sheet_title(page) == 'Save as template' and page.text_content('#sheet-msg') == 'Squat · Leg Press')
    page.screenshot(path=SHOTS / 'dlg-1-save-template.png')
    sheet_ok(page, 'Leg Day')
    check('save-from-workout still works', data(page)['templates'][1] == {'name': 'Leg Day', 'exercises': ['Squat', 'Leg Press']})
    # Saving under an existing name asks to replace; cancelling keeps the original
    page.click('text=Save as template'); sheet_ok(page, 'push day')
    check('replace prompt for existing name', sheet_title(page) == 'Replace "Push Day"?')
    sheet_cancel(page)
    check('cancel replace keeps original', data(page)['templates'][0]['exercises'] == ['Bench Press', 'Cable Fly', 'Overhead Press'])
    page.click('button:text-is("Discard")'); sheet_ok(page)

    # Edit: rename to a clashing name, then fix and remove an exercise
    page.click('nav button[data-tab=settings]')
    page.screenshot(path=SHOTS / 'tpl-2-settings.png', full_page=True)
    page.locator('.tpl-row:has-text("Leg Day") >> text=Edit').click()
    page.fill('#tpl-name', 'push day')
    page.click('text=Save template')
    check('blocks duplicate name (case-insensitive)', toast(page, 'already a template called "Push Day"'))
    page.fill('#tpl-name', 'Legs')
    page.locator('.tpl-row:has-text("Leg Press") button[aria-label="Remove"]').click()
    check('name kept after re-render', page.input_value('#tpl-name') == 'Legs')
    page.click('text=Save template')
    check('edit saved in place', data(page)['templates'][1] == {'name': 'Legs', 'exercises': ['Squat']})

    # Cancel with unsaved changes: keep editing, then discard
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click()
    page.fill('#tpl-name', 'Changed')
    page.click('button:text-is("Cancel")')
    check('unsaved changes ask before leaving', sheet_title(page) == 'Discard changes?')
    page.screenshot(path=SHOTS / 'dlg-2-discard.png')
    sheet_cancel(page)
    check('keep editing stays in editor with edits', page.input_value('#tpl-name') == 'Changed')
    page.click('button:text-is("Cancel")'); sheet_ok(page)
    check('discarding leaves template unchanged', data(page)['templates'][1]['name'] == 'Legs' and title(page) == 'Settings')
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click(); page.click('#back')
    check('no prompt when nothing changed', not sheet_open(page) and title(page) == 'Settings')

    # Delete from editor
    page.locator('.tpl-row:has-text("Legs") >> text=Edit').click()
    page.click('text=Delete template')
    check('delete asks with red button', sheet_title(page) == 'Delete "Legs"?' and 'danger-fill' in page.get_attribute('#sheet-ok', 'class'))
    sheet_ok(page)
    check('template deleted', [t['name'] for t in data(page)['templates']] == ['Push Day'] and title(page) == 'Settings')

    # Workout tab: Edit opens the editor in place; back returns to Workout; Start uses the order
    page.click('nav button[data-tab=workout]')
    page.screenshot(path=SHOTS / 'tpl-3-workout-tab.png', full_page=True)
    page.locator('.card:has(h2:text-is("Push Day")) >> text=Edit').click()
    check('Edit on workout tab opens editor', page.input_value('#tpl-name') == 'Push Day' and page.text_content('#back') == '‹ Workout')
    page.click('#back')
    check('back returns to Workout', title(page) == 'Workout')
    page.locator('.card:has(h2:text-is("Push Day")) >> text=Start').click()
    check('start uses template order', [e['name'] for e in data(page)['active']['exercises']] == ['Bench Press', 'Cable Fly', 'Overhead Press'])

with app(seed={'unit': 'lb', 'active': None, 'exercises': [], 'templates': [],
               'sessions': [{'name': 'x', 'start': 1e12, 'end': 1e12, 'exercises': []}]}) as page:
    page.click('nav button[data-tab=history]')
    check('calendar rest days not dimmed', page.locator('.cal .day:disabled').first.evaluate("e => getComputedStyle(e).opacity") == '1')

finish()
