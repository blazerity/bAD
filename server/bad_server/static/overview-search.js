/** Поиск на Обзоре → /overview/search.json (Bolt-строки выдачи) */
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

  function hitRow(href, titleHtml, metaHtml, typeLabel) {
    var a = document.createElement("a");
    a.href = href;
    a.className = "search-hit-row";
    a.innerHTML =
      '<span class="search-hit-icon" aria-hidden="true"></span>' +
      '<span class="search-hit-text">' +
      '<span class="search-hit-title"></span>' +
      '<span class="search-hit-meta muted"></span>' +
      "</span>" +
      '<span class="search-hit-type">' +
      (typeLabel || "") +
      "</span>" +
      '<span class="search-hit-arrow" aria-hidden="true">↗</span>';
    a.querySelector(".search-hit-title").innerHTML = titleHtml || "";
    var meta = a.querySelector(".search-hit-meta");
    if (metaHtml) {
      meta.innerHTML = metaHtml;
    } else {
      meta.remove();
    }
    return a;
  }

  function init() {
    var input = document.querySelector("[data-overview-search]");
    var box = document.getElementById("overview-search-results");
    var catRoot = document.querySelector("[data-overview-search-cats]");
    if (!input || !box) return;

    var cats = { devices: true, events: true, settings: true, serial: true };

    if (catRoot) {
      catRoot.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-cat]");
        if (!btn) return;
        var key = btn.getAttribute("data-cat");
        if (!key || !cats.hasOwnProperty(key)) return;
        cats[key] = !cats[key];
        var any = Object.keys(cats).some(function (k) {
          return cats[k];
        });
        if (!any) cats[key] = true;
        catRoot.querySelectorAll("[data-cat]").forEach(function (b) {
          b.classList.toggle("is-active", !!cats[b.getAttribute("data-cat")]);
        });
        if ((input.value || "").trim().length >= 2) runSearch();
      });
    }

    function clear() {
      box.innerHTML = "";
      box.hidden = true;
    }

    function render(data, q) {
      box.innerHTML = "";
      var allDevs = data.devices || [];
      var devs = cats.devices
        ? allDevs
        : cats.serial
          ? allDevs.filter(function (d) {
              var r = (d.match_reason || "").toLowerCase();
              return (
                r.indexOf("serial") >= 0 ||
                r.indexOf("серий") >= 0 ||
                r.indexOf("uuid") >= 0 ||
                r.indexOf("bios") >= 0 ||
                r.indexOf("плат") >= 0 ||
                r.indexOf("диск") >= 0 ||
                r.indexOf("монитор") >= 0 ||
                r.indexOf("озу") >= 0 ||
                r.indexOf("identifying") >= 0
              );
            })
          : [];
      var evts = cats.events ? data.events || [] : [];
      var users = data.users || [];
      var sets =
        cats.settings && typeof window.badPanelSettingsHits === "function"
          ? window.badPanelSettingsHits(q)
          : [];
      if (!devs.length && !evts.length && !users.length && !sets.length) {
        var p = document.createElement("p");
        p.className = "muted search-hit-empty";
        p.textContent = "Ничего не найдено.";
        box.appendChild(p);
        box.hidden = false;
        return;
      }
      devs.forEach(function (d) {
        box.appendChild(
          hitRow(
            d.href,
            d.title_html || d.hostname || "",
            d.subtitle_html || d.match_reason || "",
            "Устройства"
          )
        );
      });
      evts.forEach(function (e) {
        box.appendChild(
          hitRow(
            e.href,
            e.title_html || e.summary || "",
            e.subtitle_html || e.hostname || "",
            "События"
          )
        );
      });
      users.forEach(function (u) {
        var subs = (u.devices || [])
          .map(function (d) {
            return d.hostname || d.bad_id || "";
          })
          .join(", ");
        box.appendChild(
          hitRow(
            (u.devices && u.devices[0] && u.devices[0].href) || "/devices",
            u.name || "",
            subs,
            "Пользователь"
          )
        );
      });
      sets.forEach(function (s) {
        box.appendChild(
          hitRow(s.href, s.label, "раздел параметров", "Параметры")
        );
      });
      box.hidden = false;
    }

    function runSearch() {
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
        .then(function (data) {
          render(data, q);
        })
        .catch(clear);
    }

    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") ev.preventDefault();
    });
    input.addEventListener("input", debounce(runSearch, 300));
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
