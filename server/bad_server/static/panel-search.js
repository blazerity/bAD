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
        a.className =
          "live-search-item device-link chassis-" + (d.chassis_type || "other");
        a.title = d.chassis_label || "";
        var icon = document.createElement("span");
        icon.className = "device-link__icon live-search-chassis";
        icon.setAttribute("aria-hidden", "true");
        var body = document.createElement("span");
        body.className = "live-search-body";
        var label = document.createElement("span");
        label.className = "device-link__label";
        label.textContent = d.hostname || d.device_id;
        var reason = document.createElement("span");
        reason.className = "live-search-reason muted";
        var parts = [];
        if (d.match_reason) {
          parts.push(d.match_reason);
        }
        if (d.chassis_label) {
          parts.push(d.chassis_label);
        }
        reason.textContent = parts.join(" · ");
        body.appendChild(label);
        if (parts.length) {
          body.appendChild(reason);
        }
        a.appendChild(icon);
        a.appendChild(body);
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
        if (
          el.id === "device-live-q" ||
          el.hasAttribute("data-live-skip") ||
          el.hasAttribute("data-devices-search")
        ) {
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
