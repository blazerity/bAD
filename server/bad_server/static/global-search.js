/** Глобальный поиск из шапки → /overview/search.json */
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

  function settingsSection(q) {
    var ql = q.toLowerCase();
    return SETTINGS_HITS.filter(function (s) {
      return (
        s.label.toLowerCase().indexOf(ql) >= 0 ||
        s.keys.indexOf(ql) >= 0
      );
    });
  }

  function init() {
    var openBtn = document.getElementById("global-search-open");
    var modal = document.getElementById("global-search-modal");
    if (!openBtn || !modal) return;

    var input = modal.querySelector("[data-global-search-input]");
    var box = document.getElementById("global-search-results");
    var backdrop = modal.querySelector("[data-global-search-close]");

    function show() {
      modal.hidden = false;
      document.body.classList.add("global-search-open");
      if (input) {
        input.focus();
        if (input.value) input.select();
      }
    }

    function hide() {
      modal.hidden = true;
      document.body.classList.remove("global-search-open");
      if (box) {
        box.innerHTML = "";
        box.hidden = true;
      }
    }

    openBtn.addEventListener("click", show);
    if (backdrop) backdrop.addEventListener("click", hide);
    modal.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hide();
    });

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

    function render(data, q) {
      box.innerHTML = "";
      var devs = data.devices || [];
      var evts = data.events || [];
      var sets = settingsSection(q);
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
        a.className = "panel-search-item search-hit-row";
        a.innerHTML =
          '<span class="search-hit-body"><span class="search-hit-title">' +
          (d.title_html || d.hostname || "") +
          '</span><span class="muted search-hit-sub">' +
          (d.match_reason || "") +
          "</span></span>";
        return a;
      });
      section("События", evts, function (e) {
        var a = document.createElement("a");
        a.href = e.href;
        a.className = "panel-search-item search-hit-row";
        a.innerHTML =
          '<span class="search-hit-body"><span class="search-hit-title">' +
          (e.title_html || e.summary || "") +
          '</span><span class="muted search-hit-sub">' +
          (e.hostname || "") +
          "</span></span>";
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
          .then(function (data) {
            render(data, q);
          })
          .catch(clear);
      }, 280)
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
