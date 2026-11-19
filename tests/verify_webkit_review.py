"""Check phone/tablet review layouts in macOS WebKit without a collection.

Usage: python3 tests/verify_webkit_review.py [/path/to/kioku]
Requires macOS, Swift, and a Kioku checkout. This does not launch Kioku.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from test_toolbar import ReviewerBottomBar, ToolbarHooksTest, TopToolbar, Web

ROOT = Path(__file__).resolve().parent.parent
KIOKU = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "kioku"
spec = importlib.util.spec_from_file_location("kioku_webscripts", KIOKU / "shared/python/kioku/webscripts.py")
webscripts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webscripts)

fixture = ToolbarHooksTest("test_undo_is_only_enabled_when_available_in_review")
fixture.setUp()
try:
    addon = fixture.plugin
    mw = fixture.aqt.mw
    mw.state = "review"
    top = SimpleNamespace(head="")
    addon._style_web_content(top, TopToolbar(mw.toolbar))
    bottom = SimpleNamespace(head="")
    addon._style_web_content(bottom, ReviewerBottomBar(SimpleNamespace(mw=mw)))
    web = Web()
    addon._set_undo_state(web, True, "Undo Answer Card")
    enable = web.scripts[-1]
    addon._set_undo_state(web, False, "Undo")
    disable = web.scripts[-1]
finally:
    fixture.tearDown()

top_html = """<!doctype html><html><head><script>
window.commands=[];function pycmd(x){commands.push(x);return false}
</script><style>
body{margin:0}.header{display:grid;grid-template-columns:repeat(3,1fr)}
.toolbar{grid-column:2;white-space:nowrap}.hitem{display:inline-block;padding:5px 12px}
</style>""" + top.head + """</head><body><div class="header"><div class="toolbar">
<a class="hitem" id="decks">Decks</a><a class="hitem" id="add">Add</a>
<a class="hitem" id="browse">Browse</a><a class="hitem" id="stats">Stats</a>
<a class="hitem" id="sync">Sync</a><a class="hitem" id="kioku-edit-current">Edit</a>
<a class="hitem" id="kioku-undo-current">Undo</a><a class="hitem" id="kioku-review-more">More</a>
</div></div></body></html>"""
top_js = r"""(()=>{
function check(value, message) { if (!value) throw Error(message); }
const visible = id => getComputedStyle(document.getElementById(id)).display !== 'none';
const wide = innerWidth >= 584;
for (const id of ['stats', 'sync']) check(visible(id) === wide, 'wrong main toolbar: '+id);
for (const id of ['kioku-edit-current', 'kioku-undo-current', 'kioku-review-more'])
    check(visible(id) === !wide, 'wrong review toolbar: '+id);
document.documentElement.classList.remove('kioku-review-toolbar');
check(visible('stats') && visible('sync'), 'normal toolbar not restored');
const oldWidth = innerWidth, oldDescriptor = Object.getOwnPropertyDescriptor(window, 'innerWidth');
Object.defineProperty(window, 'innerWidth', {value: oldWidth + 1, configurable: true});
window.dispatchEvent(new Event('resize'));
window.dispatchEvent(new Event('resize'));
check(commands.join(',') === 'kioku:toolbar-resize', 'toolbar resize message');
if (oldDescriptor) Object.defineProperty(window, 'innerWidth', oldDescriptor);
else delete window.innerWidth;
return JSON.stringify({width:oldWidth, mainActions:wide, topReviewActions:!wide});
})()"""

base = """body{margin:0;overflow:hidden;font-family:sans-serif}
#outer{border-top:1px solid #ccc}#middle td[align=center]{padding-top:10px;position:relative}
button{min-width:60px;white-space:nowrap;margin:9px;position:relative}
.nobold,.stattxt{position:absolute;white-space:nowrap;font-size:small;top:-3px;left:50%;
transform:translate(-50%,-100%);font-weight:normal;display:inline-block}
.stat{padding-top:10px}@media(max-width:583px){.stat{display:none}}
"""
bottom_html = ("<!doctype html><html><head><style>" + base + '</style>'
               + '<script>window.commands=[];function pycmd(x){commands.push(x);return false}</script>'
               + bottom.head + '''</head><body><center id="outer"><table id="innertable" width="100%" cellspacing="0" cellpadding="0">
<tr><td class="stat" align="start"><button id="edit" onclick="return pycmd('edit')">Edit</button></td>
<td align="center" id="middle"></td><td class="stat" align="end">
<button id="more" onclick="return pycmd('more')">More ▾<span id="time" class="stattxt"></span></button>
</td></tr></table></center></body></html>''')
bottom_js = r"""(()=>{
function check(value, message) { if (!value) throw Error(message); }
const undo = document.getElementById('kioku-bottom-undo'), edit = document.getElementById('edit');
const more = document.getElementById('more'), middle = document.getElementById('middle');
const wide = innerWidth >= 584;
check(undo && undo.disabled, 'undo should initially be disabled');
""" + enable + r"""
check(!undo.disabled && undo.getAttribute('aria-disabled') === 'false', 'undo should be enabled');
""" + disable + r"""
check(undo.disabled && undo.getAttribute('aria-disabled') === 'true', 'undo should be disabled');
""" + enable + r"""
check((undo.getBoundingClientRect().width > 0) === wide, 'bottom undo visibility');
if (wide) {
    edit.click(); more.click(); undo.click();
    check(commands.join(',') === 'edit,more,kioku:bottom-undo', 'incorrect action');
}
for (const n of [2, 3, 4]) {
    let html = '<center><table cellpadding=0 cellspacing=0><tr>';
    for (let i=1; i<=n; i++) html += `<td align=center><button data-ease="${i}">Grade ${i}<span class=nobold>10 min</span></button></td>`;
    middle.innerHTML = html + '</tr></table></center>';
    const grades = [...middle.querySelectorAll('button')].map(x => x.getBoundingClientRect());
    check(grades.every(r => r.height === 72 && r.left >= 0 && r.right <= innerWidth), 'grades clipped');
    for (let i=1; i<grades.length; i++) check(grades[i].left >= grades[i-1].right, 'grades overlap');
    if (wide) {
        const e=edit.getBoundingClientRect(), m=more.getBoundingClientRect(), u=undo.getBoundingClientRect();
        check(e.right <= grades[0].left && m.left >= grades.at(-1).right && m.right <= innerWidth, 'side controls overlap');
        check(m.bottom <= u.top && u.right <= innerWidth, 'undo must be under more');
        check(e.height === 72 && m.height === 34 && u.height === 34, 'wrong control heights');
    }
}
middle.innerHTML='<table><tr><td align=center><button id=ansbut>Show Answer<span class=stattxt><span class=new-count>1</span></span></button></td></tr></table>';
if (wide) {
    function colors() { return [edit, more, undo, document.getElementById('ansbut')].map(x => getComputedStyle(x).backgroundColor); }
    for (const theme of ['light', 'dark']) {
        document.body.classList.toggle('nightMode', theme === 'dark');
        const c=colors(); check(c.every(x => x === c[0]), theme+' colors differ');
    }
}
return JSON.stringify({width:innerWidth, bottomReviewActions:wide, grades:[2,3,4], undo:'passed'});
})()"""

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    runner = tmp / "runner"
    subprocess.run(["swiftc", str(ROOT / "tests/webkit_layout_runner.swift"), "-o", str(runner)], check=True)
    for name, html, script in (("top", top_html, top_js), ("bottom", bottom_html, bottom_js)):
        (tmp / f"{name}.html").write_text(webscripts.with_viewport(html), encoding="utf-8")
        (tmp / f"{name}.js").write_text(script, encoding="utf-8")
        for width in (320, 583, 584, 600, 768, 1024):
            subprocess.run([str(runner), str(width), str(tmp / f"{name}.html"), str(tmp / f"{name}.js")], check=True)
