/** Live submit фильтров и «Ещё фильтры» на списках. */
(function () {
  function initMoreFilters() {
    document.querySelectorAll(".devices-more-toggle").forEach(function (btn) {
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      if (!panel) return;
      btn.addEventListener("click", function () {
        var open = panel.hasAttribute("hidden");
        if (open) panel.removeAttribute("hidden");
        else panel.setAttribute("hidden", "");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
    });
  }

  function initDebouncedForms() {
    document.querySelectorAll("form[data-live-submit]").forEach(function (form) {
      var delay = parseInt(form.getAttribute("data-live-delay") || "350", 10);
      form.querySelectorAll("input[type=search][name], input[type=checkbox][name], select").forEach(function (el) {
        if (el.hasAttribute("data-live-skip") || el.hasAttribute("data-devices-search")) {
          return;
        }
        if (el.tagName === "SELECT") {
          el.addEventListener("change", function () {
            form.requestSubmit();
          });
          return;
        }
        if (el.type === "checkbox") {
          el.addEventListener("change", function () {
            form.requestSubmit();
          });
          return;
        }
        el.addEventListener(
          "input",
          badDebounce(function () {
            form.requestSubmit();
          }, delay)
        );
      });
    });
  }

  badOnReady(function () {
    initDebouncedForms();
    initMoreFilters();
  });
})();
