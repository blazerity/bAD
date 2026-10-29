/** Дашборд: squarified treemap (CPU / модели). При 1–2 плитках — крупные читаемые блоки. */
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

  /**
   * 1–2 элемента: полосы на всю ширину, высота ∝ count,
   * с гарантированным минимумом — плитка не «схлопывается».
   */
  function layoutFew(items, width, height) {
    var total = 0;
    items.forEach(function (it) {
      total += Math.max(0, Number(it.count) || 0);
    });
    if (total <= 0 || width <= 0 || height <= 0) return [];

    var n = items.length;
    var minH = n === 1 ? height : Math.min(96, Math.floor(height / n));
    var weights = items.map(function (it) {
      return Math.max(0, Number(it.count) || 0);
    });
    var free = height - minH * n;
    if (free < 0) {
      minH = Math.floor(height / n);
      free = height - minH * n;
    }
    var rects = [];
    var y = 0;
    for (var i = 0; i < n; i++) {
      var extra = total > 0 ? (free * weights[i]) / total : free / n;
      var h = minH + extra;
      if (i === n - 1) h = height - y;
      rects.push({ x: 0, y: y, w: width, h: h, item: items[i] });
      y += h;
    }
    return rects;
  }

  function placeCell(root, cell, gap, forceLabel) {
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

    var showLabel = forceLabel || (cw >= 72 && ch >= 36);
    var showCount = forceLabel || (cw >= 40 && ch >= 28);
    var labelHtml = showLabel
      ? '<span class="dash-treemap-label">' + item.label + "</span>"
      : "";
    var countHtml = showCount
      ? '<span class="tnum">' + item.count + "</span>"
      : "";
    if (!labelHtml && !countHtml) {
      countHtml = '<span class="tnum">' + item.count + "</span>";
    }
    a.innerHTML = labelHtml + countHtml;
    if (forceLabel || (cw >= 160 && ch >= 72)) {
      a.classList.add("is-roomy");
    }
    root.appendChild(a);
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

    items = items.slice().sort(function (a, b) {
      return b.count - a.count || String(a.label).localeCompare(String(b.label));
    });

    var gap = 3;
    var width = Math.max(root.clientWidth || root.offsetWidth || 320, 160);
    var few = items.length <= 2;
    var baseH = Math.round(Math.min(420, Math.max(few ? 200 : 220, width * (few ? 0.36 : 0.42))));
    if (few) {
      baseH = Math.max(baseH, items.length === 1 ? 160 : 220);
    }
    var height = Math.max(
      parseInt(root.getAttribute("data-height"), 10) || 0,
      baseH
    );
    root.style.height = height + "px";
    root.style.position = "relative";
    root.classList.toggle("dash-treemap--few", few);

    var layout = few
      ? layoutFew(items, width, height)
      : layoutSquarified(items, width, height);
    layout.forEach(function (cell) {
      placeCell(root, cell, gap, few);
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

  var resizeTimer = null;
  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderAllTreemaps, 120);
  }

  function init() {
    renderAllTreemaps();
    window.addEventListener("resize", onResize);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
