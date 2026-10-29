/** Дашборд + Обзор: treemap конфигов и столбчатый график событий. */
(function () {
  function parseJson(el, attr, fallback) {
    try {
      return JSON.parse(el.getAttribute(attr) || fallback || "null");
    } catch (e) {
      return fallback === "[]" ? [] : fallback === "{}" ? {} : null;
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

  function fmtDay(iso) {
    if (!iso || iso.length < 10) return iso || "";
    var p = iso.slice(0, 10).split("-");
    return p[2] + "." + p[1];
  }

  function niceMax(n) {
    if (n <= 0) return 5;
    var step = Math.ceil(n / 4);
    var mag = Math.pow(10, Math.floor(Math.log10(step)));
    var nice = Math.ceil(step / mag) * mag;
    return Math.max(nice * 4, nice);
  }

  function renderEventChart(root, days) {
    var seriesMap = parseJson(root, "data-series", "{}") || {};
    var key = String(days || root.getAttribute("data-days") || "14");
    var points = seriesMap[key] || seriesMap["14"] || [];
    root.innerHTML = "";
    if (!points.length) {
      root.innerHTML = '<p class="muted">Нет данных</p>';
      return;
    }

    var w = Math.max(root.clientWidth || 480, 280);
    var h = 220;
    var padL = 36;
    var padR = 12;
    var padT = 16;
    var padB = 36;
    var maxVal = 0;
    points.forEach(function (p) {
      if ((p.count || 0) > maxVal) maxVal = p.count || 0;
    });
    var yMax = niceMax(maxVal);
    var plotW = w - padL - padR;
    var plotH = h - padT - padB;
    var n = points.length;
    var gap = Math.max(2, Math.min(8, plotW / n / 4));
    var barW = Math.max(4, (plotW - gap * (n + 1)) / n);

    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("class", "dash-event-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "События по дням");

    function line(x1, y1, x2, y2, cls) {
      var el = document.createElementNS(svgNS, "line");
      el.setAttribute("x1", x1);
      el.setAttribute("y1", y1);
      el.setAttribute("x2", x2);
      el.setAttribute("y2", y2);
      el.setAttribute("class", cls || "");
      svg.appendChild(el);
    }

    for (var gi = 0; gi <= 4; gi++) {
      var gy = padT + (plotH * gi) / 4;
      line(padL, gy, w - padR, gy, "dash-chart-grid");
      var label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", padL - 6);
      label.setAttribute("y", gy + 3);
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "dash-chart-axis");
      label.textContent = String(Math.round(yMax * (1 - gi / 4)));
      svg.appendChild(label);
    }

    var tip = document.createElement("div");
    tip.className = "dash-chart-tip";
    tip.hidden = true;
    root.appendChild(tip);

    points.forEach(function (p, i) {
      var count = p.count || 0;
      var crit = p.critical || 0;
      var warn = p.warning || 0;
      var x = padL + gap + i * (barW + gap);
      var barH = yMax > 0 ? (count / yMax) * plotH : 0;
      var warnH = yMax > 0 ? (warn / yMax) * plotH : 0;
      var critH = yMax > 0 ? (crit / yMax) * plotH : 0;
      var otherH = Math.max(0, barH - warnH - critH);

      function rect(ry, rh, cls) {
        if (rh <= 0) return;
        var r = document.createElementNS(svgNS, "rect");
        r.setAttribute("x", x);
        r.setAttribute("y", ry);
        r.setAttribute("width", barW);
        r.setAttribute("height", rh);
        r.setAttribute("rx", 2);
        r.setAttribute("class", cls);
        svg.appendChild(r);
      }

      var yCursor = padT + plotH;
      if (otherH > 0) {
        yCursor -= otherH;
        rect(yCursor, otherH, "dash-chart-bar-other");
      }
      if (warnH > 0) {
        yCursor -= warnH;
        rect(yCursor, warnH, "dash-chart-bar-warn");
      }
      if (critH > 0) {
        yCursor -= critH;
        rect(yCursor, critH, "dash-chart-bar-crit");
      }

      var hit = document.createElementNS(svgNS, "rect");
      hit.setAttribute("x", x);
      hit.setAttribute("y", padT);
      hit.setAttribute("width", barW);
      hit.setAttribute("height", plotH);
      hit.setAttribute("class", "dash-chart-hit");
      hit.addEventListener("mouseenter", function (ev) {
        tip.hidden = false;
        tip.innerHTML =
          "<strong>" +
          fmtDay(p.day) +
          "</strong><br>Всего: " +
          count +
          "<br>Критичные: " +
          crit +
          "<br>Предупреждения: " +
          warn;
        tip.style.left = Math.min(w - 140, Math.max(0, ev.offsetX)) + "px";
        tip.style.top = Math.max(0, ev.offsetY - 8) + "px";
      });
      hit.addEventListener("mousemove", function (ev) {
        tip.style.left = Math.min(w - 140, Math.max(0, ev.offsetX)) + "px";
        tip.style.top = Math.max(0, ev.offsetY - 8) + "px";
      });
      hit.addEventListener("mouseleave", function () {
        tip.hidden = true;
      });
      svg.appendChild(hit);

      if (n <= 10 || i % Math.ceil(n / 8) === 0 || i === n - 1) {
        var xl = document.createElementNS(svgNS, "text");
        xl.setAttribute("x", x + barW / 2);
        xl.setAttribute("y", h - 10);
        xl.setAttribute("text-anchor", "middle");
        xl.setAttribute("class", "dash-chart-axis");
        xl.textContent = fmtDay(p.day);
        svg.appendChild(xl);
      }
    });

    root.appendChild(svg);
  }

  function bindRangeTabs(root) {
    var tabs = document.querySelectorAll(".dash-range-tab");
    tabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        tabs.forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        var days = btn.getAttribute("data-days") || "14";
        root.setAttribute("data-days", days);
        renderEventChart(root, days);
      });
    });
  }

  function renderTreemap(root) {
    var items = (parseJson(root, "data-treemap", "[]") || []).filter(function (x) {
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
    resizeTimer = setTimeout(function () {
      renderAllTreemaps();
      var chart = document.getElementById("dash-event-chart");
      if (chart) {
        renderEventChart(chart, chart.getAttribute("data-days") || "14");
      }
    }, 120);
  }

  function init() {
    renderAllTreemaps();
    var chart = document.getElementById("dash-event-chart");
    if (chart) {
      renderEventChart(chart, chart.getAttribute("data-days") || "14");
      bindRangeTabs(chart);
    }
    window.addEventListener("resize", onResize);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
