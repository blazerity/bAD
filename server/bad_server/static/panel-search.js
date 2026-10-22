/** Live search: устройства и события (debounce 300 ms). */
(function () {
  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(t);
      t = setTimeout(function () {
        fn.apply(self, args);
      }, ms);
    };
  }

  function initDeviceLiveSearch() {
    var input = document.getElementById("device-live-q");
    var box = document.getElementById("device-live-results");
    if (!input || !box) return;

    function clear() {
      box.innerHTML = "";
      box.hidden = true;
    }

    function render(items) {
      box.innerHTML = "";
      if (!items.length) {
        clear();
        return;
      }
      items.forEach(function (d) {
        var a = document.createElement("a");
        a.href = d.href || "/devices/" + encodeURIComponent(d.device_id);
        a.className = "live-search-item";
        a.textContent = (d.hostname || d.device_id) + " · " + d.device_id;
        box.appendChild(a);
      });
      box.hidden = false;
    }

    input.addEventListener(
      "input",
      debounce(function () {
        var q = (input.value || "").trim();
        if (q.length < 1) {
          clear();
          return;
        }
        fetch("/devices/search.json?q=" + encodeURIComponent(q), {
          credentials: "same-origin",
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            render(data.devices || []);
          })
          .catch(function () {
            clear();
          });
      }, 300)
    );

    document.addEventListener("click", function (ev) {
      if (!box.contains(ev.target) && ev.target !== input) clear();
    });
  }

  function initDebouncedForms() {
    document.querySelectorAll("form[data-live-submit]").forEach(function (form) {
      var delay = parseInt(form.getAttribute("data-live-delay") || "350", 10);
      form.querySelectorAll("input[type=search][name], select").forEach(function (el) {
        if (el.id === "device-live-q" || el.hasAttribute("data-live-skip")) {
          return;
        }
        if (el.tagName === "SELECT") {
          el.addEventListener("change", function () {
            form.requestSubmit();
          });
          return;
        }
        el.addEventListener(
          "input",
          debounce(function () {
            form.requestSubmit();
          }, delay)
        );
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initDeviceLiveSearch();
      initDebouncedForms();
    });
  } else {
    initDeviceLiveSearch();
    initDebouncedForms();
  }
})();
