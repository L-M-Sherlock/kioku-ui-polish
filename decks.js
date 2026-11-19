/* Keep Anki's original links and bridge commands; make the rest of a row tap
   the deck link. The arrow itself remains a separate collapse target. */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("tr.deck .decktd").forEach(function (cell) {
        const first = cell.firstChild;
        if (!first || first.nodeType !== Node.TEXT_NODE) return;
        const match = first.data.match(/^[ \t\r\n]*(\u00a0+)[ \t\r\n]*$/);
        if (!match) return;
        const indent = document.createElement("span");
        indent.className = "kioku-deck-indent";
        indent.style.setProperty("--kioku-deck-indent", Math.min(match[1].length / 6 * 10, 30) + "px");
        indent.setAttribute("aria-hidden", "true");
        indent.textContent = first.data;
        cell.replaceChild(indent, first);
    });
    document.querySelectorAll("tr.deck a.collapse").forEach(function (arrow) {
        const expanded = arrow.textContent.trim() !== "+";
        arrow.dataset.kiokuExpanded = String(expanded);
        arrow.setAttribute("aria-expanded", String(expanded));
    });
    document.addEventListener("click", function (event) {
        if (event.shiftKey ||
            event.defaultPrevented || event.target.closest("a, button, input, select, textarea")) {
            return;
        }
        const row = event.target.closest("tr.deck");
        const deck = row && row.querySelector("a.deck");
        if (deck) deck.click();
    });
});
