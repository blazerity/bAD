/** Живой поиск устройств → /devices/search.json (без submit формы) */
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

  function hitRow(d) {
    var a = document.createElement("a");
    a.href = d.href;
    a.className = "search-hit-row";
    a.innerHTML =
      '<span class="search-hit-icon search-hit-icon-device" aria-hidden="true"></span>' +
      '<span class="search-hit-text">' +
      '<span class="search-hit-title"></span>' +
      '<span class="search-hit-meta muted"></span>' +
      "</span>" +
      '<span class="search-hit-type">Устройства</span>' +
      '<span class="search-hit-arrow" aria-hidden="true">↗</span>';
    a.querySelector(".search-hit-title").innerHTML =
      d.title_html || d.hostname || d.device_id || "";
    var meta = a.querySelector(".search-hit-meta");
    if (d.subtitle_html) meta.innerHTML = d.subtitle_html;
    else if (d.match_reason) meta.textContent = d.match_reason;
    else meta.remove();
    return a;
  }

  function init() {
    var input = document.querySelector("[data-devices-search]");
    var box = document.getElementById("devices-search-results");
    if (!input || !box) return;

    function clear() {
      box.innerHTML = "";
      box.hidden = true;
    }

    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") ev.preventDefault();
    });

    input.addEventListener(
      "input",
      debounce(function () {
        var q = (input.value || "").trim();
        if (q.length < 2) {
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
            box.innerHTML = "";
            var items = data.devices || [];
            if (!items.length) {
              var p = document.createElement("p");
              p.className = "muted search-hit-empty";
              p.textContent = "Ничего не найдено.";
              box.appendChild(p);
            } else {
              items.forEach(function (d) {
                box.appendChild(hitRow(d));
              });
            }
            box.hidden = false;
          })
          .catch(clear);
      }, 300)
    );

    document.addEventListener("click", function (ev) {
      if (!box.contains(ev.target) && ev.target !== input) clear();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
