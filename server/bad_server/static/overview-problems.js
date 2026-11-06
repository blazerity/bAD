/** Фильтр «Сейчас требует действия» + перерисовка графика по выбранной серьёзности. */
(function () {
  function init() {
    var bar = document.querySelector(".prob-severity-bar");
    var list = document.querySelector("[data-problems-list]");
    if (!bar) return;

    var rows = list ? list.querySelectorAll("[data-problem-row]") : [];
    var empty = document.querySelector("[data-problems-empty]");
    var chips = bar.querySelectorAll("[data-sev-filter]");

    function applyChart(filter) {
      var chart = document.getElementById("dash-event-chart");
      if (!chart || typeof window.renderEventChart !== "function") return;
      chart.setAttribute("data-sev", filter);
      window.renderEventChart(
        chart,
        chart.getAttribute("data-days") || "14",
        filter
      );
    }

    function applyProblems(filter) {
      if (!list) return;
      var visible = 0;
      rows.forEach(function (row) {
        var sev = row.getAttribute("data-severity") || "";
        var show = filter === "all" || sev === filter;
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (empty) empty.hidden = visible > 0;
    }

    function apply(filter) {
      chips.forEach(function (chip) {
        chip.classList.toggle(
          "is-active",
          chip.getAttribute("data-sev-filter") === filter
        );
      });
      applyProblems(filter);
      applyChart(filter);
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        apply(chip.getAttribute("data-sev-filter") || "all");
      });
    });

    var active = bar.querySelector(".prob-sev-chip.is-active");
    apply(active ? active.getAttribute("data-sev-filter") || "all" : "all");
  }

  badOnReady(init);
})();
