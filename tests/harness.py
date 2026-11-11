"""Shared test helpers: load index.html in Chromium with a fake Claude runtime and expose app internals.

The page is served from a fake origin (https://test.local) so localStorage works, and every other
request (Google Fonts, YouTube) is blocked, so tests run offline.
"""
import os
from playwright.async_api import async_playwright  # noqa: F401  (re-exported for the test files)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADLESS = os.environ.get('HEADLESS', '1') != '0'
SHOTS = os.path.join(ROOT, 'tests', 'shots')
os.makedirs(SHOTS, exist_ok=True)

with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
    _html = f.read()
with open(os.path.join(ROOT, 'tests', 'fakeclaude.js'), encoding='utf-8') as f:
    FAKE = f.read()

# expose a few internals as window.__t, just before the app's closing "})();"
_HOOK = ("  window.__t = { get ui(){return ui;}, get log(){return log;}, get EX(){return EX;}, showView: showView, "
         "selectDay: selectDay, buildCSV: typeof buildCSV==='function'?buildCSV:null, LIB: LIB };\n})();\n</script>")
_cut = _html.rindex('})();')
DOC = _html[:_cut] + _HOOK + _html[_html.index('</script>', _cut) + 9:]


async def page(browser, width, scheme):
    """New context at the given width and color scheme; returns (context, page, errors)."""
    ctx = await browser.new_context(viewport={'width': width, 'height': 860}, color_scheme=scheme)
    await ctx.add_init_script(FAKE)
    pg = await ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append('PAGEERR ' + str(e)))
    pg.on('console', lambda m: errs.append('CONSOLE ' + m.text)
          if m.type in ('error', 'warning') and 'ERR_' not in m.text and 'fonts' not in m.text else None)
    await pg.route('**/*', lambda r: r.fulfill(status=200, body=DOC, content_type='text/html')
                   if r.request.url.startswith('https://test.local') else r.abort())
    await pg.goto('https://test.local/')
    await pg.wait_for_timeout(400)
    return ctx, pg, errs


async def txt(pg, sel):
    el = await pg.query_selector(sel)
    return (await el.inner_text()).replace('\n', ' | ') if el else '<none:' + sel + '>'


async def checks(pg, label):
    """No horizontal scroll, no duplicate ids, every visible control has a name."""
    r = await pg.evaluate("""() => {
      const ids = {}; document.querySelectorAll('[id]').forEach(e => ids[e.id] = (ids[e.id]||0)+1);
      const dup = Object.keys(ids).filter(k => ids[k] > 1);
      const unnamed = [...document.querySelectorAll('button, input, select')].filter(b => b.offsetParent &&
        !(b.textContent.trim() || b.getAttribute('aria-label') || (b.labels && b.labels.length) || b.getAttribute('aria-labelledby'))).length;
      return {sw: document.documentElement.scrollWidth, vw: window.innerWidth, dup, unnamed};
    }""")
    ok = r['sw'] <= r['vw'] and not r['dup'] and not r['unnamed']
    print(('OK  ' if ok else 'FAIL'), label, r)
    return ok


# four weeks of sample training on the 扣球爆發 program (days A, B, C)
SEED = """() => { const p=n=>(n<10?'0':'')+n; const ds=k=>{const d=new Date(); d.setDate(d.getDate()-k); return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate());};
  const W = [];
  const mk = (k, day, exs) => W.push({id: ds(k)+'-'+day, d: ds(k), day, t0: Date.now()-k*864e5, t1: Date.now()-k*864e5+55*6e4, last: null, ex: exs});
  const S = (w, r, n) => Array.from({length:n}, () => ({w, r, done:true}));
  [28,21,14,7].forEach((k,i) => { mk(k,'A',[{slot:'A1',id:'goblet_squat',rpe:7+(i%2),tgt:{sets:4,reps:6},sets:S(30+i*2,6,4)},{slot:'A2',id:'rdl',rpe:7,tgt:{sets:3,reps:8},sets:S(40+i*2.5,8,3)},{slot:'A3',id:'bss',rpe:8,tgt:{sets:3,reps:8},sets:S(10+i*2,8,3)},{slot:'A4',id:'plank',rpe:null,tgt:{sets:3,reps:30},sets:S(null,30+i*5,3)}]);
    mk(k-1,'B',[{slot:'B1',id:'db_bench',rpe:8,tgt:{sets:3,reps:8},sets:S(14+i*2,8,3)},{slot:'B2',id:'pullup',rpe:8,tgt:{sets:3,reps:6},sets:S(0,5+i%2,3)},{slot:'B3',id:'db_press',rpe:7,tgt:{sets:3,reps:8},sets:S(10+i,8,3)}]);
    mk(k-3,'C',[{slot:'C1',id:'box_jump',rpe:null,tgt:{sets:4,reps:3},sets:S(null,3,4)},{slot:'C4',id:'kb_swing',rpe:7,tgt:{sets:3,reps:10},sets:S(16+i*4>24?24:16+i*4,10,3)}]); });
  return {v:3, mode:'4', start: ds(30), swaps:{}, workouts: W, tests:{reach:[], throw:[], speed:[]}, lines:[], diag:{}, bw:72, updated: Date.now()}; }"""


async def seed(pg):
    data = await pg.evaluate(SEED)
    await pg.evaluate("s => { localStorage.setItem('spike-log-v2', JSON.stringify(s)); localStorage.removeItem('spike-ui-v2'); }", data)
    await pg.reload()
    await pg.wait_for_timeout(400)
