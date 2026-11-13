/** Единое окно поиска: короткий список и расширенная лента. */
(function () {
  var FILTER_LABELS = {
    os: "ОС",
    ram: "ОЗУ",
    disk: "Диск",
    cpu: "CPU",
    model: "Модель",
    chassis: "Корпус",
  };
  var FILTER_KEYS = ["os", "ram", "disk", "cpu", "model", "chassis"];
  var FRESH_LABELS = {
    online: "Онлайн",
    recent: "Недавно",
    stale: "Устарел",
    unknown: "Нет данных",
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function init() {
    var modal = document.getElementById("global-search-modal");
    if (!modal) return;

    var openBtn = document.getElementById("global-search-open");
    var dialog = modal.querySelector("[data-global-search-dialog]");
    var input = modal.querySelector("[data-global-search-input]");
    var backdrop = modal.querySelector("[data-global-search-backdrop]");
    var closeEl = modal.querySelector("[data-global-search-close]");
    var shortWrap = modal.querySelector("[data-global-search-short]");
    var shortBox = document.getElementById("global-search-results");
    var moreBtn = document.getElementById("global-search-more");
    var expandedBody = document.getElementById("global-search-expanded-body");
    var filtersRoot = modal.querySelector("[data-global-search-filters]");
    var feed = modal.querySelector("[data-global-search-feed]");

    var expanded = false;
    var shortTimer = null;
    var expandedOffset = 0;
    var expandedLoading = false;
    var expandedMore = { devices: false, events: false };
    var expandedFilters = { os: "", ram: "", disk: "", cpu: "", model: "", chassis: "" };
    var expandedFilterOptions = null;

    function trimmed() {
      return (input && input.value ? input.value : "").trim();
    }

    function setBackdropOpacity() {
      if (!backdrop) return;
      var q = trimmed();
      var op = "0";
      if (expanded) op = "0.55";
      else if (q.length >= 2) op = "0.28";
      backdrop.style.opacity = op;
    }

    function setExpanded(on) {
      expanded = !!on;
      modal.classList.toggle("global-search-expanded", expanded);
      if (expandedBody) {
        expandedBody.hidden = false;
        expandedBody.classList.toggle("is-visible-panel", expanded);
        expandedBody.setAttribute("aria-hidden", expanded ? "false" : "true");
      }
      if (shortWrap) {
        shortWrap.hidden = false;
        shortWrap.classList.toggle("is-hidden-panel", expanded);
      }
      if (moreBtn) moreBtn.hidden = expanded || trimmed().length < 2;
      setBackdropOpacity();
      if (dialog) dialog.classList.toggle("is-open", !modal.hidden);
    }

    function clearShort() {
      if (shortBox) {
        shortBox.innerHTML = "";
        shortBox.hidden = true;
      }
      if (moreBtn) moreBtn.hidden = expanded || trimmed().length < 2;
    }

    function clearExpandedFeed() {
      if (feed) feed.innerHTML = "";
      expandedOffset = 0;
      expandedMore = { devices: false, events: false };
    }

    function deviceShortRow(d) {
      var a = document.createElement("a");
      a.href = d.href || "#";
      a.className = "panel-search-item global-search-device-item";
      var title = d.title_html || esc(d.hostname || "");
      var match =
        d.match_label && d.match_html
          ? '<span class="global-search-match"><span class="muted">' +
            esc(d.match_label) +
            "</span> " +
            d.match_html +
            "</span>"
          : "";
      a.innerHTML =
        '<span class="search-hit-body"><span class="search-hit-title">' +
        title +
        "</span>" +
        match +
        "</span>";
      return a;
    }

    function renderShort(data) {
      if (!shortBox) return;
      shortBox.innerHTML = "";
      var devs = (data.devices || []).slice(0, 8);
      if (!devs.length) {
        var p = document.createElement("p");
        p.className = "muted";
        p.textContent = "Ничего не найдено.";
        shortBox.appendChild(p);
      } else {
        devs.forEach(function (d) {
          shortBox.appendChild(deviceShortRow(d));
        });
      }
      shortBox.hidden = false;
      if (moreBtn) moreBtn.hidden = expanded || trimmed().length < 2;
    }

    function fetchShort() {
      var q = trimmed();
      if (q.length < 2) {
        clearShort();
        setBackdropOpacity();
        return;
      }
      fetch("/overview/search.json?q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (expanded) return;
          renderShort(data);
          setBackdropOpacity();
        })
        .catch(clearShort);
    }

    function scheduleShort() {
      if (shortTimer) clearTimeout(shortTimer);
      shortTimer = setTimeout(fetchShort, 280);
    }

    function filterParams() {
      var parts = [];
      FILTER_KEYS.forEach(function (k) {
        if (expandedFilters[k]) parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(expandedFilters[k]));
      });
      return parts.length ? "&" + parts.join("&") : "";
    }

    function expandedUrl(offset) {
      return (
        "/overview/search/expanded.json?q=" +
        encodeURIComponent(trimmed()) +
        "&offset=" +
        String(offset || 0) +
        filterParams()
      );
    }

    function renderFilterSelects(filters) {
      if (!filtersRoot) return;
      filtersRoot.innerHTML = "";
      FILTER_KEYS.forEach(function (key) {
        var wrap = document.createElement("label");
        wrap.className = "global-search-filter";
        var span = document.createElement("span");
        span.className = "global-search-filter-label";
        span.textContent = FILTER_LABELS[key] || key;
        var sel = document.createElement("select");
        sel.dataset.filter = key;
        var optAll = document.createElement("option");
        optAll.value = "";
        optAll.textContent = "все";
        sel.appendChild(optAll);
        (filters[key] || []).forEach(function (v) {
          var o = document.createElement("option");
          o.value = v;
          o.textContent = v;
          if (expandedFilters[key] === v) o.selected = true;
          sel.appendChild(o);
        });
        sel.value = expandedFilters[key] || "";
        sel.addEventListener("change", function () {
          expandedFilters[key] = sel.value || "";
          expandedFilterOptions = filters;
          clearExpandedFeed();
          loadExpanded(true);
        });
        wrap.appendChild(span);
        wrap.appendChild(sel);
        filtersRoot.appendChild(wrap);
      });
    }

    function deviceExpandedRow(d) {
      var el = document.createElement("a");
      el.href = d.href || "#";
      el.className = "panel-search-item global-search-expanded-item";
      var bits = ['<span class="search-hit-title">' + (d.title_html || esc(d.hostname || "")) + "</span>"];
      if (d.match_label && d.match_html) {
        bits.push(
          '<span class="global-search-match muted">' +
            esc(d.match_label) +
            " " +
            d.match_html +
            "</span>"
        );
      }
      if (d.model) bits.push('<span class="global-search-meta">' + esc(d.model) + "</span>");
      if (d.user) bits.push('<span class="global-search-meta">' + esc(d.user) + "</span>");
      if (d.os) bits.push('<span class="global-search-meta">' + esc(d.os) + "</span>");
      if (d.ip) bits.push('<span class="global-search-meta mono">' + esc(d.ip) + "</span>");
      el.innerHTML = '<span class="search-hit-body global-search-expanded-body-line">' + bits.join("") + "</span>";
      return el;
    }

    function eventExpandedRow(e) {
      var el = document.createElement("a");
      el.href = e.href || "#";
      el.className = "panel-search-item global-search-expanded-item";
      var bits = ['<span class="search-hit-title">' + (e.title_html || "") + "</span>"];
      if (e.match_label) bits.push('<span class="muted">' + esc(e.match_label) + "</span>");
      if (e.hostname) bits.push('<span class="global-search-meta">' + esc(e.hostname) + "</span>");
      el.innerHTML = '<span class="search-hit-body global-search-expanded-body-line">' + bits.join("") + "</span>";
      return el;
    }

    function appendExpandedPage(data, replace) {
      if (!feed) return;
      if (replace) feed.innerHTML = "";
      if (data.filters && expandedOffset === 0) {
        expandedFilterOptions = data.filters;
        renderFilterSelects(data.filters);
      }
      (data.devices || []).forEach(function (d) {
        feed.appendChild(deviceExpandedRow(d));
      });
      (data.events || []).forEach(function (e) {
        feed.appendChild(eventExpandedRow(e));
      });
      expandedMore.devices = !!data.more_devices;
      expandedMore.events = !!data.more_events;
    }

    function loadExpanded(reset) {
      var q = trimmed();
      if (q.length < 2) return;
      if (expandedLoading) return;
      if (reset) {
        expandedOffset = 0;
        clearExpandedFeed();
      }
      expandedLoading = true;
      fetch(expandedUrl(expandedOffset), { credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          appendExpandedPage(data, expandedOffset === 0);
          expandedOffset += 20;
        })
        .catch(function () {})
        .finally(function () {
          expandedLoading = false;
        });
    }

    function openModal(prefill) {
      modal.hidden = false;
      document.body.classList.add("global-search-open");
      if (dialog) {
        requestAnimationFrame(function () {
          dialog.classList.add("is-open");
        });
      }
      setExpanded(false);
      if (typeof prefill === "string" && input) {
        input.value = prefill;
      }
      if (input) {
        input.focus();
        if (input.value) input.select();
      }
      scheduleShort();
      setBackdropOpacity();
    }

    function hideModal() {
      if (dialog) dialog.classList.remove("is-open");
      modal.hidden = true;
      document.body.classList.remove("global-search-open");
      setExpanded(false);
      clearShort();
      clearExpandedFeed();
      setBackdropOpacity();
    }

    if (openBtn) openBtn.addEventListener("click", function () {
      openModal("");
    });
    if (closeEl) closeEl.addEventListener("click", hideModal);
    modal.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hideModal();
    });

    if (moreBtn) {
      moreBtn.addEventListener("click", function () {
        setExpanded(true);
        clearExpandedFeed();
        loadExpanded(true);
      });
    }

    if (input) {
      input.addEventListener("input", function () {
        if (expanded) {
          clearExpandedFeed();
          loadExpanded(true);
        } else {
          scheduleShort();
        }
        setBackdropOpacity();
      });
    }

    if (feed) {
      feed.addEventListener("scroll", function () {
        if (!expanded || expandedLoading) return;
        if (!(expandedMore.devices || expandedMore.events)) return;
        var nearBottom = feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 48;
        if (nearBottom) loadExpanded(false);
      });
    }

    window.badGlobalSearch = {
      open: openModal,
      setQuery: function (q) {
        if (!input) return;
        input.value = q || "";
        if (expanded) {
          clearExpandedFeed();
          loadExpanded(true);
        } else {
          scheduleShort();
        }
        setBackdropOpacity();
      },
    };

    function wirePageSearchInput(input, opts) {
      if (!input) return;
      var box = opts && opts.resultsId ? document.getElementById(opts.resultsId) : null;
      if (box) {
        box.hidden = true;
        box.setAttribute("aria-hidden", "true");
      }
      if (opts && opts.hideCats) {
        var catRoot = document.querySelector("[data-overview-search-cats]");
        if (catRoot) catRoot.hidden = true;
      }
      function openWithValue() {
        openModal(input.value || "");
      }
      input.addEventListener("focus", openWithValue);
      input.addEventListener("click", openWithValue);
      input.addEventListener("input", function () {
        window.badGlobalSearch.setQuery(input.value || "");
      });
      input.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") ev.preventDefault();
      });
    }

    wirePageSearchInput(document.querySelector("[data-devices-search]"), {
      resultsId: "devices-search-results",
    });
    wirePageSearchInput(document.querySelector("[data-overview-search]"), {
      resultsId: "overview-search-results",
      hideCats: true,
    });

    setBackdropOpacity();
  }

  badOnReady(init);
})();
