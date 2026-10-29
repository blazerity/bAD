/** Тумблер ленты Обзора: Критичные / Все */
(function () {
  function init() {
    var root = document.querySelector("[data-overview-feed]");
    if (!root) return;
    var toggle = root.querySelector("[data-feed-imp-toggle]");
    var list = root.querySelector("[data-feed-list]");
    var emptyCrit = root.querySelector("[data-feed-empty-critical]");
    if (!toggle || !list) return;

    function apply(mode) {
      var rows = list.querySelectorAll("[data-importance]");
      var visible = 0;
      rows.forEach(function (row) {
        var imp = (row.getAttribute("data-importance") || "").toLowerCase();
        var show = mode !== "critical" || imp === "critical";
        row.hidden = !show;
        if (show) visible += 1;
      });
      // Баннер только при фильтре «Критичные», если в ленте их нет
      if (emptyCrit) {
        emptyCrit.hidden = !(mode === "critical" && visible === 0);
      }
      toggle.querySelectorAll("[data-feed-imp]").forEach(function (btn) {
        btn.classList.toggle(
          "is-active",
          btn.getAttribute("data-feed-imp") === mode
        );
      });
    }

    toggle.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-feed-imp]");
      if (!btn || !toggle.contains(btn)) return;
      apply(btn.getAttribute("data-feed-imp") || "all");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
