/** Поле на обзоре открывает общее окно поиска. */
(function () {
  function init() {
    var input = document.querySelector("[data-overview-search]");
    var box = document.getElementById("overview-search-results");
    if (box) {
      box.hidden = true;
      box.setAttribute("aria-hidden", "true");
    }
    var catRoot = document.querySelector("[data-overview-search-cats]");
    if (catRoot) catRoot.hidden = true;

    if (!input || !window.badGlobalSearch) return;

    function openWithValue() {
      window.badGlobalSearch.open(input.value || "");
    }

    input.addEventListener("focus", openWithValue);
    input.addEventListener("click", openWithValue);
    input.addEventListener("input", function () {
      if (window.badGlobalSearch.setQuery) {
        window.badGlobalSearch.setQuery(input.value || "");
      }
    });
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") ev.preventDefault();
    });
  }

  badOnReady(init);
})();
