/** Глобальный поиск на Обзоре → /overview/search.json */
(function () {
  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments;
      clearTimeout(t);
      t = setTimeout(function () {
        fn.apply(null, args);
      }, ms);
    };
  }

  function init() {
    var input = document.querySelector("[data-overview-search]");
    var box = document.getElementById("overview-search-results");
    if (!input || !box) return;

    function clear() {
      box.innerHTML = "";
      box.hidden = true;
    }

    function section(title, items, renderItem) {
      if (!items.length) return;
      var h = document.createElement("h3");
      h.className = "panel-search-section-title";
      h.textContent = title;
      box.appendChild(h);
      items.forEach(function (item) {
        box.appendChild(renderItem(item));
      });
    }

    function render(data) {
      box.innerHTML = "";
      var devs = data.devices || [];
      var evts = data.events || [];
      if (!devs.length && !evts.length) {
        var p = document.createElement("p");
        p.className = "muted";
        p.textContent = "Ничего не найдено.";
        box.appendChild(p);
        box.hidden = false;
        return;
      }
      section("Устройства", devs, function (d) {
        var a = document.createElement("a");
        a.href = d.href;
        a.className =
          "panel-search-item live-search-item device-link chassis-" +
          (d.chassis_type || "other");
        var body = document.createElement("span");
        body.className = "live-search-body";
        var title = document.createElement("span");
        title.className = "device-link__label";
        if (d.title_html) {
          title.innerHTML = d.title_html;
        } else {
          title.textContent = d.hostname || d.device_id || "";
        }
        var reason = document.createElement("span");
        reason.className = "live-search-reason muted";
        var bits = [];
        if (d.match_reason) bits.push(d.match_reason);
        if (d.archived) bits.push("архив");
        reason.textContent = bits.join(" · ");
        body.appendChild(title);
        if (bits.length) body.appendChild(reason);
        a.appendChild(body);
        return a;
      });
      section("События", evts, function (e) {
        var a = document.createElement("a");
        a.href = e.href;
        a.className = "panel-search-item live-search-item";
        var body = document.createElement("span");
        body.className = "live-search-body";
        var title = document.createElement("span");
        title.className = "device-link__label";
        if (e.title_html) {
          title.innerHTML = e.title_html;
        } else {
          title.textContent = e.summary || "";
        }
        var reason = document.createElement("span");
        reason.className = "live-search-reason muted";
        reason.textContent = [e.match_reason, e.hostname].filter(Boolean).join(" · ");
        body.appendChild(title);
        body.appendChild(reason);
        a.appendChild(body);
        return a;
      });
      box.hidden = false;
    }

    input.addEventListener(
      "input",
      debounce(function () {
        var q = (input.value || "").trim();
        if (q.length < 2) {
          clear();
          return;
        }
        fetch("/overview/search.json?q=" + encodeURIComponent(q), {
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json();
          })
          .then(render)
          .catch(clear);
      }, 300)
    );

    document.addEventListener("click", function (ev) {
      if (!box.contains(ev.target) && ev.target !== input) clear();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
