/* Keep Anki's original links and bridge commands; make the rest of a row tap
   the deck link. The arrow itself remains a separate collapse target. */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("tr.deck a.collapse").forEach(function (arrow) {
        const expanded = arrow.textContent.trim() !== "+";
        arrow.dataset.kiokuExpanded = String(expanded);
        arrow.setAttribute("aria-expanded", String(expanded));
    });
    document.addEventListener("click", function (event) {
        if (!window.matchMedia("(max-width: 600px)").matches || event.shiftKey ||
            event.defaultPrevented || event.target.closest("a, button, input, select, textarea")) {
            return;
        }
        const row = event.target.closest("tr.deck");
        const deck = row && row.querySelector("a.deck");
        if (deck) deck.click();
    });
});
