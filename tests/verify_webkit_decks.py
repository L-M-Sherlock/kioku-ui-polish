"""Run a synthetic deck list with Kioku's actual phone CSS on macOS WebKit.

Usage: python3 tests/verify_webkit_decks.py [/path/to/kioku]
Requires macOS, Swift, and a Kioku checkout. This does not launch Kioku.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIOKU = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "kioku"
spec = importlib.util.spec_from_file_location("kioku_webscripts", KIOKU / "shared/python/kioku/webscripts.py")
webscripts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webscripts)

# Approximate Anki's table stylesheet; Kioku's unmodified PHONE_CSS is appended
# by with_viewport(), as it is in the running app.
base = """body{margin:2em 1em;font-family:sans-serif;--border-subtle:#ddd}
.fancy table{padding:1rem;border:1px solid #ddd}tr.deck td{padding:1px 12px}
.fancy tr.deck td{padding:4px 12px}.decktd{min-width:15em;overflow:hidden}
.collapse{display:inline-block;width:1em}.gears{visibility:hidden}
a.deck{display:inline-block;min-width:5em;text-decoration:none}
"""
html = ("<!doctype html><html><head><style>" + base + "</style><style>"
        + (ROOT / "decks.css").read_text(encoding="utf-8")
        + '</style><script>window.calls=[];function pycmd(x){calls.push(x);return false};'
        + (ROOT / "decks.js").read_text(encoding="utf-8")
        + '</script></head><body class="fancy"><center><table cellspacing="0" cellpadding="3">'
        + '<tr><th colspan="5">Deck</th><th>New</th><th>Learn</th><th>Review</th><th></th></tr>'
        + '<tr class="top-level-drag-row"><td colspan="6">&nbsp;</td></tr>')
for number in range(1, 9):
    indent = "&nbsp;" * 6 * (number - 1)
    new, learn, review = ("12345", "12345", "12345") if number in (4, 7) else ("5", "1", "40")
    html += (f'<tr class="deck" id="{number}"><td class="decktd" colspan="5">{indent}'
             f'<a class="collapse" href="#" onclick="return pycmd(\'collapse:{number}\')">+</a>'
             f'<a class="deck" href="#" onclick="return pycmd(\'open:{number}\')">Long 日本語 Deck Name</a></td>'
             f'<td align="end"><span class="new-count">{new}</span></td>'
             f'<td align="end"><span class="learn-count">{learn}</span></td>'
             f'<td align="end"><span class="review-count">{review}</span></td>'
             f'<td class="opts"><a onclick="return pycmd(\'opts:{number}\')"><img class="gears"></a></td></tr>')
html += '</table><div id="studiedToday">Studied 0 cards today.</div></center></body></html>'

js = r"""(()=>{
function check(value, message) { if (!value) throw Error(message); }
const rows = [...document.querySelectorAll('tr.deck')], table = document.querySelector('table');
const width = document.documentElement.clientWidth;
function verify(theme) {
    document.body.classList.toggle('nightMode', theme === 'dark');
    for (const row of rows) {
        const box = row.getBoundingClientRect();
        const option = row.querySelector('.opts a').getBoundingClientRect();
        const indent = row.querySelector('.kioku-deck-indent');
        const link = row.querySelector('a.deck'), name = link.getBoundingClientRect();
        const nameStyle = getComputedStyle(link);
        check(parseFloat(nameStyle.fontSize) === 18 && Number(nameStyle.fontWeight) >= 700, 'deck name typography');
        check(box.left >= 0 && box.right <= width + 0.5, 'row clipped');
        check(option.width >= 44 && option.height >= 44 && option.right <= width + 0.5, 'options clipped');
        check(name.width > 0, 'deck name missing');
        if (indent) check(indent.getBoundingClientRect().width <= 30, 'deep indentation');
        for (const count of row.querySelectorAll('td span[class$="count"]')) {
            const range = document.createRange(); range.selectNodeContents(count);
            const text = range.getBoundingClientRect(), cell = count.closest('td').getBoundingClientRect();
            const expectedSize = Math.min(13, Math.max(11, innerWidth * 0.04));
            check(Math.abs(parseFloat(getComputedStyle(count).fontSize) - expectedSize) < 0.1, 'count typography');
            check(text.left >= cell.left - 0.5 && text.right <= cell.right + 0.5, 'count overflow');
        }
    }
    check(table.scrollWidth <= table.clientWidth + 1, 'table overflow');
}
verify('light'); verify('dark');
const wideCount = rows[6].querySelector('.new-count').closest('td').getBoundingClientRect().width;
const narrowCount = rows[7].querySelector('.new-count').closest('td').getBoundingClientRect().width;
check(narrowCount < wideCount, 'counts still use fixed column widths');
check(rows[7].querySelector('a.deck').getBoundingClientRect().width >
      rows[6].querySelector('a.deck').getBoundingClientRect().width, 'compact counts did not free space');
rows[7].querySelector('.learn-count').click();
rows[3].querySelector('a.collapse').click();
rows[1].querySelector('.opts a').click();
check(calls.join(',') === 'open:8,collapse:4,opts:2', 'incorrect action');
return JSON.stringify({width: innerWidth, themes: 'light/dark',
    singleDigitCell: narrowCount, fiveDigitCell: wideCount, actions: calls});
})()"""

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / "fixture.html").write_text(webscripts.with_viewport(html), encoding="utf-8")
    (tmp / "check.js").write_text(js, encoding="utf-8")
    runner = tmp / "runner"
    subprocess.run(["swiftc", str(ROOT / "tests/webkit_layout_runner.swift"), "-o", str(runner)], check=True)
    for width in (240, 280, 320, 390, 600):
        subprocess.run([str(runner), str(width), str(tmp / "fixture.html"), str(tmp / "check.js")], check=True)
