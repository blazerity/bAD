/** Дашборд: столбчатый график событий, модалки «остальные» */
(function () {
  function parseJson(el, attr) {
    try {
      return JSON.parse(el.getAttribute(attr) || "{}");
    } catch (e) {
      return {};
    }
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
    var seriesMap = parseJson(root, "data-series");
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

    // сетка Y
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
      var y = padT + plotH - barH;
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

      // hit area
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

      // X labels — каждый 2-й при длинных рядах
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

  function bindOthersDialogs() {
    document.querySelectorAll(".dash-others-open").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-dialog");
        var dlg = id ? document.getElementById(id) : null;
        if (dlg && typeof dlg.showModal === "function") dlg.showModal();
      });
    });
  }

  var resizeTimer = null;
  function init() {
    var chart = document.getElementById("dash-event-chart");
    if (chart) {
      renderEventChart(chart, chart.getAttribute("data-days") || "14");
      bindRangeTabs(chart);
      window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
          renderEventChart(chart, chart.getAttribute("data-days") || "14");
        }, 120);
      });
    }
    bindOthersDialogs();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
