"""Programs: rotation instead of fixed weekdays, switching programs, the program builder, the "don't do" list."""
import asyncio
import os
import sys
from harness import async_playwright, page, checks, txt, seed, HEADLESS, SHOTS

SEQ = "[...document.querySelectorAll('#weekGrid .seq')].map(b => b.querySelector('.sq-t').textContent + (b.classList.contains('next') ? '*' : '')).join(' ')"
fails = []


def expect(cond, label, got=''):
    print(('OK  ' if cond else 'FAIL'), label, got)
    if not cond:
        fails.append(label)


async def tick_one(pg):
    """Fill and tick the first open set of the visible day."""
    bt = await pg.query_selector('#panels .day:not([hidden]) .chk[aria-pressed="false"]')
    code, i = await bt.get_attribute('data-ex'), await bt.get_attribute('data-i')
    for sel, v in [(f'#kg-{code}-{i}', '30'), (f'#rp-{code}-{i}', '8')]:
        el = await pg.query_selector(sel)
        if el:
            await el.fill(v)
    await bt.click()
    await pg.wait_for_timeout(80)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=HEADLESS)

        # ---- a new visitor starts on the beginner program; no volleyball tab
        ctx, pg, errs = await page(b, 400, 'light')
        tops = await pg.eval_on_selector_all('#views button', 'els => els.map(e => e.textContent).join(",")')
        expect(tops == '重訓,飲食,須知,設定', 'top tabs', tops)
        expect(await pg.evaluate('__t.log.prog') == 'novice', 'new user gets 新手器械入門')
        await pg.evaluate("__t.showView('prog')")
        await pg.wait_for_timeout(120)
        expect(await pg.evaluate(SEQ) == '1* 2', 'sequence starts at day 1', await pg.evaluate(SEQ))
        await pg.screenshot(path=os.path.join(SHOTS, 'prog-400.png'), full_page=True)
        expect(await checks(pg, 'program page'), 'program page layout')

        # ---- did day 1 three days ago, skipped since: next is day 2, whatever weekday today is
        await pg.evaluate("""() => { const d = new Date(); d.setDate(d.getDate() - 3); const iso = d.toLocaleDateString('sv');
          const l = __t.log; l.workouts = [{id: iso + '-N', d: iso, day: 'N', t0: 1, t1: 2, ex: [{slot: 'N1', id: 'leg_press', sets: [{w: 50, r: 10, done: true}]}]}];
          localStorage.setItem('spike-log-v2', JSON.stringify(l)); localStorage.removeItem('spike-ui-v2'); }""")
        await pg.reload()
        await pg.wait_for_timeout(400)
        expect(await pg.evaluate('__t.ui.day') == 'M', 'opens on the next day in order', await txt(pg, '#today'))
        await ctx.close()

        # ---- switching programs through the detail sheet
        ctx, pg, errs = await page(b, 400, 'light')
        await seed(pg)
        await pg.evaluate("__t.showView('prog')")
        await pg.click('#pgList [data-pgopen="ppl"]')
        await pg.wait_for_timeout(120)
        await pg.click('#sheet [data-useprog="ppl"]')
        await pg.wait_for_timeout(200)
        expect(await pg.evaluate('__t.log.prog') == 'ppl', 'switched to PPL')
        await pg.evaluate("__t.showView('prog')")
        await pg.wait_for_timeout(100)
        expect(await pg.evaluate(SEQ) == '拉* 推 腿 拉 推 腿', 'PPL rotation', await pg.evaluate(SEQ))

        # ---- program builder: 2 times a week, chest / back / legs, no barbell squat or deadlift
        await pg.click('#pgGenD > summary')
        await pg.click('#genN [data-gn="2"]')
        await pg.click('#genSplit [data-gsplit="cbl"]')
        await pg.click('#genAvoid [data-gavoid="back_squat"]')
        await pg.click('#genAvoid [data-gavoid="deadlift"]')
        await pg.wait_for_timeout(100)
        out = await pg.inner_text('#genOut')
        expect('槓鈴背蹲舉' not in out and '傳統硬舉' not in out, 'avoided lifts left out of the plan')
        await pg.screenshot(path=os.path.join(SHOTS, 'builder-400.png'), full_page=True)
        expect(await checks(pg, 'builder'), 'builder layout')
        await pg.click('#genUse')
        await pg.wait_for_timeout(250)
        tabs = await pg.eval_on_selector_all('#tabs .tab:not([hidden])', 'els => els.map(e => e.textContent).join(",")')
        expect(await pg.evaluate('__t.log.prog') == 'mine' and tabs == '1胸,2背,3腿', 'my program in use', tabs)

        # finish day 1 -> next is day 2; survives reload
        await pg.click('#panels .day:not([hidden]) .start')
        await tick_one(pg)
        await pg.click('#fbEnd')
        await pg.wait_for_timeout(80)
        await pg.click('#fbEnd')
        await pg.wait_for_timeout(250)
        expect('2 背' in await txt(pg, '.sm-next'), 'summary points to day 2', await txt(pg, '.sm-next'))
        await pg.keyboard.press('Escape')
        await pg.reload()
        await pg.wait_for_timeout(400)
        expect(await pg.evaluate('__t.log.prog') == 'mine', 'my program kept after reload')

        # ---- "don't do" list swaps exercises in fixed programs too
        await pg.evaluate("__t.showView('library')")
        await pg.click('#libList [data-lib="bb_bench"]')
        await pg.wait_for_timeout(120)
        await pg.click('#sheet [data-avoid]')
        await pg.wait_for_timeout(120)
        await pg.keyboard.press('Escape')
        await pg.evaluate("__t.showView('prog')")
        await pg.click('#pgList [data-pgopen="fullbody"]')
        await pg.wait_for_timeout(100)
        await pg.click('#sheet [data-useprog="fullbody"]')
        await pg.wait_for_timeout(200)
        await pg.click('#tab-F')
        names = await pg.eval_on_selector_all('#panel-F .ex-name', 'els => els.map(e => e.textContent).join(",")')
        expect('槓鈴臥推' not in names and '槓鈴背蹲舉' not in names, '5x5 swaps avoided lifts', names)
        expect(await checks(pg, 'end'), 'final layout')
        expect(not errs, 'no page errors', errs)
        await ctx.close()
        await b.close()
    print('programs:', 'all passed' if not fails else f'{len(fails)} failed: {fails}')
    sys.exit(1 if fails else 0)

asyncio.run(main())
