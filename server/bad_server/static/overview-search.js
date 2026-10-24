/** Поиск на Обзоре → /overview/search.json + чипы категорий */
(function () {
  var SETTINGS_HITS = [
    { label: "Доступ / LDAP", href: "/settings/ldap", keys: "ldap доступ домен" },
    { label: "Сертификат TLS", href: "/settings/tls", keys: "tls https сертификат" },
    { label: "Почта и уведомления", href: "/settings/mail", keys: "smtp почта mail digest" },
    { label: "Хранение и очистка", href: "/settings/retention", keys: "retention хранение очистка" },
    { label: "Резервные копии", href: "/settings/backups", keys: "backup резерв ключи" },
    { label: "Политики агента", href: "/settings/policies", keys: "политики policy агент" },
    { label: "Обновления агента", href: "/settings/updates", keys: "агент msi обновление enrollment" },
    { label: "Обновление сервера", href: "/settings/server-update", keys: "сервер обновление release" },
  ];

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

  function settingsSection(q, enabled) {
    if (!enabled) return [];
    var ql = q.toLowerCase();
    return SETTINGS_HITS.filter(function (s) {
      return (
        s.label.toLowerCase().indexOf(ql) >= 0 ||
        s.keys.indexOf(ql) >= 0
      );
    });
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
        if (!any) {
          cats[key] = true;
        }
        catRoot.querySelectorAll("[data-cat]").forEach(function (b) {
          var k = b.getAttribute("data-cat");
          b.classList.toggle("is-active", !!cats[k]);
        });
        if ((input.value || "").trim().length >= 2) {
          runSearch();
        }
      });
    }

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

    function render(data, q) {
      box.innerHTML = "";
      var devs = cats.devices ? data.devices || [] : [];
      var evts = cats.events ? data.events || [] : [];
      if (cats.serial && devs.length) {
        devs = devs.filter(function (d) {
          var r = (d.match_reason || "").toLowerCase();
          return (
            r.indexOf("serial") >= 0 ||
            r.indexOf("серий") >= 0 ||
            r.indexOf("uuid") >= 0 ||
            (d.subtitle_html && String(d.subtitle_html).length > 0)
          );
        });
        if (!devs.length && (data.devices || []).length) {
          devs = data.devices;
        }
      }
      var sets = settingsSection(q, cats.settings);
      if (!devs.length && !evts.length && !sets.length) {
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
          "panel-search-item live-search-item search-hit-row device-link chassis-" +
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
        a.className = "panel-search-item live-search-item search-hit-row";
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
      section("Параметры", sets, function (s) {
        var a = document.createElement("a");
        a.href = s.href;
        a.className = "panel-search-item search-hit-row";
        a.innerHTML =
          '<span class="search-hit-body"><span class="search-hit-title">' +
          s.label +
          '</span><span class="muted search-hit-sub">раздел параметров</span></span>';
        return a;
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
