/** Сворачивание левой рейки (desktop) и off-canvas (viewport <768). */
(function () {
  var KEY = "bad-panel-rail-collapsed";
  var MQ = window.matchMedia("(max-width: 767px)");

  function isMobile() {
    return MQ.matches;
  }

  function toggleBtn() {
    return document.getElementById("rail-toggle");
  }

  function backdrop() {
    return document.getElementById("hcp-rail-backdrop");
  }

  function setDesktopCollapsed(collapsed) {
    document.documentElement.classList.toggle("rail-collapsed", collapsed);
    document.body.classList.remove("rail-mobile-open");
    var btn = toggleBtn();
    if (btn) {
      btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
      btn.title = collapsed ? "Развернуть меню" : "Свернуть меню";
    }
  }

  function setMobileOpen(open) {
    document.body.classList.toggle("rail-mobile-open", open);
    var btn = toggleBtn();
    if (btn) {
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.title = open ? "Закрыть меню" : "Открыть меню";
    }
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
    if (!toggleBtn()) return;
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
    var btn = toggleBtn();
    if (btn) btn.addEventListener("click", onToggleClick);
    var bd = backdrop();
    if (bd) {
      bd.addEventListener("click", function () {
        setMobileOpen(false);
      });
    }
    MQ.addEventListener("change", applyLayout);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
