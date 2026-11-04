/** Фильтр списка «Сейчас требует действия» по полосе серьёзности. */
(function () {
  function init() {
    var bar = document.querySelector(".prob-severity-bar");
    var list = document.querySelector("[data-problems-list]");
    if (!bar || !list) return;
    var rows = list.querySelectorAll("[data-problem-row]");
    var empty = document.querySelector("[data-problems-empty]");
    var chips = bar.querySelectorAll("[data-sev-filter]");

    function apply(filter) {
      var visible = 0;
      rows.forEach(function (row) {
        var sev = row.getAttribute("data-severity") || "";
        var show = filter === "all" || sev === filter;
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (empty) empty.hidden = visible > 0;
      chips.forEach(function (chip) {
        chip.classList.toggle(
          "is-active",
          chip.getAttribute("data-sev-filter") === filter
        );
      });
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        apply(chip.getAttribute("data-sev-filter") || "all");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
