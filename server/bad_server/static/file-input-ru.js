(function () {
  function bindOne(wrap) {
    var input = wrap.querySelector('input[type="file"]');
    var btn = wrap.querySelector(".file-input-ru-btn");
    var nameEl = wrap.querySelector(".file-input-ru-name");
    if (!input || !btn || !nameEl) return;
    var empty =
      input.getAttribute("data-empty-label") ||
      nameEl.getAttribute("data-file-empty") ||
      "файл не выбран";

    function sync() {
      var f = input.files && input.files[0];
      nameEl.textContent = f ? f.name : empty;
    }

    btn.addEventListener("click", function () {
      input.click();
    });
    input.addEventListener("change", sync);
    sync();
  }

  function init() {
    document.querySelectorAll(".file-input-ru").forEach(bindOne);
  }

  badOnReady(init);
})();
