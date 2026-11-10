/** Чипы серьёзности меняют только график динамики. Список «Сейчас требует действия» не трогают. */
(function () {
  function chartNote(filter) {
    var note = document.querySelector("[data-chart-sev-empty]");
    var chart = document.getElementById("dash-event-chart");
    if (!note || !chart) return;
    var text = chart.textContent || "";
    var emptyChart = text.indexOf("Нет данных") !== -1;
    note.hidden = filter === "all" || filter === "offline" || !emptyChart;
  }

  function init() {
    var bar = document.querySelector(".prob-severity-bar");
    if (!bar) return;

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
      chartNote(filter);
    }

    function apply(filter) {
      chips.forEach(function (chip) {
        chip.classList.toggle(
          "is-active",
          chip.getAttribute("data-sev-filter") === filter
        );
      });
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
