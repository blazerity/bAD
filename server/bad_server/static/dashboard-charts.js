/** Графики дашборда: squarified treemap, датчики, sparkline */
(function () {
  function parseJson(el, attr) {
    try {
      return JSON.parse(el.getAttribute(attr) || "[]");
    } catch (e) {
      return [];
    }
  }

  /** Worst aspect ratio of a row against remaining area length. */
  function worst(row, w) {
    if (!row.length) return Infinity;
    var s = 0;
    var max = 0;
    var min = Infinity;
    for (var i = 0; i < row.length; i++) {
      var v = row[i].value;
      s += v;
      if (v > max) max = v;
      if (v < min) min = v;
    }
    var s2 = s * s;
    var w2 = w * w;
    return Math.max((w2 * max) / s2, s2 / (w2 * min));
  }

  /**
   * Squarified treemap (Bruls et al.): площадь ячейки строго ∝ count.
   * Возвращает {x,y,w,h,item} в координатах контейнера.
   */
  function layoutSquarified(items, width, height) {
    var total = 0;
    var nodes = items.map(function (it) {
      var v = Math.max(0, Number(it.count) || 0);
      total += v;
      return { item: it, value: v };
    });
    if (total <= 0 || width <= 0 || height <= 0) return [];

    var scale = (width * height) / total;
    nodes.forEach(function (n) {
      n.value *= scale;
    });

    var rects = [];
    var x0 = 0;
    var y0 = 0;
    var w = width;
    var h = height;
    var row = [];
    var i = 0;

    function layoutRow(horizontal) {
      var sum = 0;
      for (var r = 0; r < row.length; r++) sum += row[r].value;
      if (sum <= 0) return;
      if (horizontal) {
        var rowH = sum / w;
        var x = x0;
        for (r = 0; r < row.length; r++) {
          var cw = row[r].value / rowH;
          rects.push({
            x: x,
            y: y0,
            w: cw,
            h: rowH,
            item: row[r].item,
          });
          x += cw;
        }
        y0 += rowH;
        h -= rowH;
      } else {
        var rowW = sum / h;
        var y = y0;
        for (r = 0; r < row.length; r++) {
          var ch = row[r].value / rowW;
          rects.push({
            x: x0,
            y: y,
            w: rowW,
            h: ch,
            item: row[r].item,
          });
          y += ch;
        }
        x0 += rowW;
        w -= rowW;
      }
    }

    while (i < nodes.length) {
      var horizontal = w >= h;
      var side = horizontal ? w : h;
      var next = nodes[i];
      if (!row.length || worst(row, side) >= worst(row.concat([next]), side)) {
        row.push(next);
        i += 1;
      } else {
        layoutRow(horizontal);
        row = [];
      }
    }
    if (row.length) {
      layoutRow(w >= h);
    }
    return rects;
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

    // Сортировка по убыванию — крупные слева/сверху
    items = items.slice().sort(function (a, b) {
      return b.count - a.count || String(a.label).localeCompare(String(b.label));
    });

    var gap = 3;
    var width = Math.max(root.clientWidth || root.offsetWidth || 320, 160);
    var height = Math.max(
      parseInt(root.getAttribute("data-height"), 10) || 0,
      Math.round(Math.min(420, Math.max(220, width * 0.42)))
    );
    root.style.height = height + "px";
    root.style.position = "relative";

    var layout = layoutSquarified(items, width, height);
    layout.forEach(function (cell) {
      var item = cell.item;
      var a = document.createElement(item.href ? "a" : "div");
      if (item.href) a.href = item.href;
      a.className = "dash-treemap-cell vendor-" + (item.vendor || "neutral");
      var left = cell.x + gap / 2;
      var top = cell.y + gap / 2;
      var cw = Math.max(0, cell.w - gap);
      var ch = Math.max(0, cell.h - gap);
      a.style.left = left + "px";
      a.style.top = top + "px";
      a.style.width = cw + "px";
      a.style.height = ch + "px";
      a.title = item.label + ": " + item.count;
      var showLabel = cw >= 72 && ch >= 36;
      var showCount = cw >= 40 && ch >= 28;
      a.innerHTML =
        (showLabel
          ? '<span class="dash-treemap-label">' + item.label + "</span>"
          : "") +
        (showCount ? '<span class="tnum">' + item.count + "</span>" : "");
      if (!showLabel && !showCount) {
        a.innerHTML = '<span class="tnum">' + item.count + "</span>";
      }
      root.appendChild(a);
    });
  }

  function renderAllTreemaps() {
    ["dash-cpu-treemap", "dash-laptop-treemap", "dash-desktop-treemap"].forEach(
      function (id) {
        var el = document.getElementById(id);
        if (el) renderTreemap(el);
      }
    );
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

  var resizeTimer = null;
  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderAllTreemaps, 120);
  }

  function init() {
    renderAllTreemaps();
    window.addEventListener("resize", onResize);
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
