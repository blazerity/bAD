(function () {
  "use strict";

  var SKIP = { "": true, "—": true, "-": true };

  function toast(message) {
    var el = document.getElementById("copy-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "copy-toast";
      el.className = "copy-toast";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add("is-visible");
    window.clearTimeout(el._hideTimer);
    el._hideTimer = window.setTimeout(function () {
      el.classList.remove("is-visible");
    }, 2000);
  }

  function copyText(text) {
    var value = (text || "").trim();
    if (!value || SKIP[value]) {
      return Promise.resolve(false);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(value).then(
        function () {
          return true;
        },
        function () {
          return fallbackCopy(value);
        }
      );
    }
    return Promise.resolve(fallbackCopy(value));
  }

  function fallbackCopy(value) {
    var ta = document.createElement("textarea");
    ta.value = value;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      return document.execCommand("copy");
    } catch (_e) {
      return false;
    } finally {
      document.body.removeChild(ta);
    }
  }

  function resolvePayload(btn) {
    var target = btn.getAttribute("data-copy-target");
    if (target) {
      var el = document.querySelector(target);
      if (el) {
        return el.textContent || "";
      }
    }
    return btn.getAttribute("data-copy") || "";
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".copy-btn");
    if (!btn) {
      return;
    }
    ev.preventDefault();
    copyText(resolvePayload(btn)).then(function (ok) {
      if (!ok) {
        return;
      }
      toast("Скопировано");
      var prevTitle = btn.getAttribute("title") || "Копировать";
      btn.setAttribute("title", "Скопировано");
      window.setTimeout(function () {
        btn.setAttribute("title", prevTitle);
      }, 1500);
    });
  });
})();
