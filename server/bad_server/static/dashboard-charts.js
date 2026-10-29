/** SVG-графики дашборда (treemap, датчики, sparkline) */
(function () {
  function parseJson(el, attr) {
    try {
      return JSON.parse(el.getAttribute(attr) || "[]");
    } catch (e) {
      return [];
    }
  }

  function renderTreemap(root) {
    var items = parseJson(root, "data-treemap").filter(function (x) {
      return x && x.count > 0;
    });
    root.innerHTML = "";
    if (!items.length) {
      root.innerHTML = '<p class="muted">Нет данных</p>';
      return;
    }
    // Уже отсортированы на сервере по count desc; площадь ∝ count
    var total = items.reduce(function (sum, i) {
      return sum + (i.count || 0);
    }, 0);
    if (total < 1) total = 1;
    items.forEach(function (item) {
      var a = document.createElement(item.href ? "a" : "div");
      if (item.href) a.href = item.href;
      a.className = "dash-treemap-cell vendor-" + (item.vendor || "neutral");
      var share = item.share != null ? item.share : item.count / total;
      // flex-grow пропорционален count — самый частый = самый большой куб
      a.style.flexGrow = String(Math.max(1, item.count));
      a.style.flexBasis = Math.max(7, share * 100) + "%";
      a.style.maxWidth = Math.min(100, Math.max(18, share * 100 + 12)) + "%";
      a.title = item.label + ": " + item.count;
      a.innerHTML =
        '<span class="dash-treemap-label">' +
        item.label +
        '</span><span class="tnum">' +
        item.count +
        "</span>";
      root.appendChild(a);
    });
  }

  function renderGauges(root) {
    var online = parseFloat(root.getAttribute("data-online") || "0");
    var stale = parseFloat(root.getAttribute("data-stale") || "0");
    root.innerHTML =
      '<div class="dash-gauge"><span class="muted">Онлайн</span><strong class="tnum">' +
      online +
      "%</strong></div>" +
      '<div class="dash-gauge"><span class="muted">Устарели</span><strong class="tnum">' +
      stale +
      "%</strong></div>";
  }

  function renderSparkline(root) {
    var points = parseJson(root, "data-points");
    root.innerHTML = "";
    if (!points.length) {
      root.innerHTML = '<p class="muted">Нет данных</p>';
      return;
    }
    var w = 280;
    var h = 64;
    var pad = 4;
    var max = Math.max.apply(
      null,
      points.map(function (p) {
        return p.count || 0;
      })
    );
    if (max < 1) max = 1;
    var step = (w - pad * 2) / Math.max(1, points.length - 1);
    var coords = points.map(function (p, i) {
      var x = pad + i * step;
      var y = h - pad - ((p.count || 0) / max) * (h - pad * 2);
      return x + "," + y;
    });
    var svg =
      '<svg viewBox="0 0 ' +
      w +
      " " +
      h +
      '" class="dash-sparkline-svg" aria-hidden="true"><polyline fill="none" stroke="var(--accent)" stroke-width="2" points="' +
      coords.join(" ") +
      '"/></svg>';
    root.innerHTML = svg;
  }

  function init() {
    ["dash-cpu-treemap", "dash-laptop-treemap", "dash-desktop-treemap"].forEach(
      function (id) {
        var el = document.getElementById(id);
        if (el) renderTreemap(el);
      }
    );
    var gauges = document.querySelector(".dash-gauges");
    if (gauges) renderGauges(gauges);
    var spark = document.getElementById("dash-event-sparkline");
    if (spark) renderSparkline(spark);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
