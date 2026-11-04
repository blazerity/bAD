/** Светлая/тёмная тема (HashiCorp-style tokens via data-theme). */
(function () {
  var KEY = "bad-panel-theme";
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.setAttribute(
        "title",
        theme === "dark" ? "Светлая тема" : "Тёмная тема"
      );
    }
  }
  var stored = localStorage.getItem(KEY);
  if (stored === "dark" || stored === "light") {
    apply(stored);
  } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    apply("dark");
  } else {
    apply("light");
  }
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next =
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "light"
          : "dark";
      localStorage.setItem(KEY, next);
      apply(next);
    });
  });
})();
