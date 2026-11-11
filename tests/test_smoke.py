"""Every page opens without errors and without horizontal scrolling, on a phone and a desktop, light and dark."""
import asyncio
import sys
from harness import async_playwright, page, checks, HEADLESS

VIEWS = ['today', 'prog', 'build', 'library', 'history', 'stretch', 'learn',
         'dcalc', 'dmeal', 'dfood', 'dveg', 'guide', 'settings']


async def main():
    failed = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=HEADLESS)
        for w, scheme in [(400, 'light'), (400, 'dark'), (1000, 'light'), (1000, 'dark')]:
            ctx, pg, errs = await page(b, w, scheme)
            for v in VIEWS:
                await pg.evaluate(f"__t.showView('{v}')")
                await pg.wait_for_timeout(120)
                if not await checks(pg, f'{w}px {scheme} {v}'):
                    failed += 1
            if errs:
                print('FAIL errors', w, scheme, errs)
                failed += 1
            await ctx.close()
        await b.close()
    print('smoke:', 'all passed' if not failed else f'{failed} failed')
    sys.exit(1 if failed else 0)

asyncio.run(main())
