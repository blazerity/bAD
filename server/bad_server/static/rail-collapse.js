/** Сворачивание левой рейки (desktop) и off-canvas (viewport <768). */
(function () {
  var KEY = "bad-panel-rail-collapsed";
  var MQ = window.matchMedia("(max-width: 767px)");

  function isMobile() {
    return MQ.matches;
  }

  function toggleButtons() {
    var ids = ["rail-toggle", "rail-toggle-mobile"];
    var out = [];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) out.push(el);
    });
    return out;
  }

  function backdrop() {
    return document.getElementById("hcp-rail-backdrop");
  }

  function setDesktopCollapsed(collapsed) {
    document.documentElement.classList.toggle("rail-collapsed", collapsed);
    document.body.classList.remove("rail-mobile-open");
    toggleButtons().forEach(function (btn) {
      if (btn.id === "rail-toggle-mobile") {
        btn.setAttribute("aria-expanded", "false");
        btn.title = "Открыть меню";
        btn.setAttribute("data-rail-mobile-open", "false");
        return;
      }
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
      btn.title = collapsed ? "Развернуть меню" : "Свернуть меню";
    });
  }

  function setMobileOpen(open) {
    document.body.classList.toggle("rail-mobile-open", open);
    toggleButtons().forEach(function (btn) {
      if (btn.id === "rail-toggle-mobile") {
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        btn.title = open ? "Закрыть меню" : "Открыть меню";
        btn.setAttribute("data-rail-mobile-open", open ? "true" : "false");
        return;
      }
      if (btn.id === "rail-toggle") {
        btn.setAttribute("aria-expanded", readDesktopCollapsed() ? "false" : "true");
        btn.title = readDesktopCollapsed() ? "Развернуть меню" : "Свернуть меню";
      }
    });
    var bd = backdrop();
    if (bd) bd.hidden = !open;
  }

  function readDesktopCollapsed() {
    try {
      return localStorage.getItem(KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function applyLayout() {
    if (!toggleButtons().length) return;
    if (isMobile()) {
      document.documentElement.classList.remove("rail-collapsed");
      setMobileOpen(false);
    } else {
      setDesktopCollapsed(readDesktopCollapsed());
    }
  }

  function onToggleClick() {
    if (isMobile()) {
      setMobileOpen(!document.body.classList.contains("rail-mobile-open"));
      return;
    }
    var next = !document.documentElement.classList.contains("rail-collapsed");
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch (e) {}
    setDesktopCollapsed(next);
  }

  function init() {
    applyLayout();
    toggleButtons().forEach(function (btn) {
      btn.addEventListener("click", onToggleClick);
    });
    var bd = backdrop();
    if (bd) {
      bd.addEventListener("click", function () {
        setMobileOpen(false);
      });
    }
    MQ.addEventListener("change", applyLayout);
  }

  badOnReady(init);
})();
