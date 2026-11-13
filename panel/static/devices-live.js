/** Тихое обновление таблицы устройств. */
(function () {
  var STORAGE_KEY = "bad-devices-live";
  var TICK_MS = 30000;
  var FRESH_LABELS = {
    online: "Онлайн",
    recent: "Недавно",
    stale: "Устарел",
    unknown: "Нет данных",
  };

  function reducedMotion() {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) {
      return false;
    }
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function findMainTbody(table) {
    var bodies = table.querySelectorAll("tbody");
    for (var i = 0; i < bodies.length; i++) {
      if (!bodies[i].classList.contains("devices-live-in")) return bodies[i];
    }
    return table.querySelector("tbody");
  }

  function updateBadge(cell, state) {
    var badge = cell && cell.querySelector(".badge-fresh-online, .badge-fresh-recent, .badge-fresh-stale, .badge-fresh-unknown");
    if (!badge) return;
    var tier = state || "unknown";
    badge.className = "badge badge-fresh-" + tier;
    badge.textContent = FRESH_LABELS[tier] || tier;
  }

  function applyRow(tr, d) {
    if (!tr || !d) return;
    tr.dataset.badId = d.bad_id || "";
    updateBadge(tr.querySelector(".col-device-state"), d.state);
    var host = tr.querySelector(".device-cell-host");
    if (host && d.hostname) host.textContent = d.hostname;
    var userCell = tr.querySelector(".device-col-user");
    if (userCell) {
      var ut = userCell.querySelector(".device-col-user-text");
      if (d.user) {
        if (!ut) {
          userCell.innerHTML = '<span class="device-col-user-text">' + esc(d.user) + "</span>";
        } else ut.textContent = d.user;
      } else if (ut) ut.textContent = "";
    }
    var model = tr.querySelector(".device-col-model-text");
    if (model) model.textContent = d.model || "—";
    var cpu = tr.querySelector(".device-col-cpu-text");
    if (cpu) cpu.textContent = d.cpu || "—";
    var ram = tr.querySelector(".device-col-ram");
    if (ram) ram.textContent = d.ram || "—";
    var disk = tr.querySelector(".device-col-disk");
    if (disk) disk.textContent = d.disk || "—";
    var os = tr.querySelector(".device-col-os-cell span");
    if (os) os.textContent = d.os || "—";
    var ipCell = tr.querySelector(".device-col-ip");
    if (ipCell && d.ip) ipCell.textContent = d.ip;
    var seen = tr.querySelector(".col-device-seen");
    if (seen) seen.textContent = d.seen || "—";
    var link = tr.querySelector(".device-cell-link, .row-chevron");
    if (link && d.href) link.setAttribute("href", d.href);
  }

  function buildRow(d) {
    var tr = document.createElement("tr");
    tr.className = "table-row-link";
    tr.dataset.badId = d.bad_id || "";
    var tier = d.state || "unknown";
    tr.innerHTML =
      '<td class="col-device-state"><span class="devices-state-inline"><span class="badge badge-fresh-' +
      esc(tier) +
      '">' +
      esc(FRESH_LABELS[tier] || tier) +
      '</span></span></td>' +
      '<td class="col-device-host"><a class="device-cell-link" href="' +
      esc(d.href || "#") +
      '"><span class="device-cell-host">' +
      esc(d.hostname || "(неизвестно)") +
      '</span></a><span class="mono device-cell-id">' +
      esc(d.bad_id || "") +
      "</span></td>" +
      '<td class="device-col-user">' +
      (d.user
        ? '<span class="device-col-user-text">' + esc(d.user) + "</span>"
        : '<span class="muted">нет данных</span>') +
      "</td>" +
      '<td class="device-col-model muted"><span class="device-col-model-text">' +
      esc(d.model || "—") +
      "</span></td>" +
      '<td class="device-col-cpu muted"><span class="device-col-cpu-text">' +
      esc(d.cpu || "—") +
      "</span></td>" +
      '<td class="device-col-ram muted">' +
      esc(d.ram || "—") +
      "</td>" +
      '<td class="device-col-disk muted">' +
      esc(d.disk || "—") +
      "</td>" +
      '<td class="device-col-os-cell"><span>' +
      esc(d.os || "—") +
      '</span><span class="mono muted device-col-sub">bAD Agent</span></td>' +
      '<td class="mono device-col-ip">' +
      esc(d.ip || "—") +
      "</td>" +
      '<td class="muted col-device-seen">' +
      esc(d.seen || "—") +
      "</td>" +
      '<td class="col-chevron"><a class="row-chevron" href="' +
      esc(d.href || "#") +
      '" aria-label="Открыть устройство"></a></td>';
    return tr;
  }

  function flashNewRows(tbody) {
    if (!tbody || reducedMotion()) return;
    tbody.classList.add("devices-live-in");
    var onEnd = function () {
      tbody.classList.remove("devices-live-in");
      tbody.removeEventListener("animationend", onEnd);
    };
    tbody.addEventListener("animationend", onEnd);
  }

  function init() {
    var toggle = document.querySelector("[data-devices-live-toggle]");
    var table = document.querySelector(".devices-table-modern");
    if (!toggle || !table) return;

    var tbody = findMainTbody(table);
    var loading = false;
    var enabled = false;

    try {
      enabled = localStorage.getItem(STORAGE_KEY) === "1";
    } catch (e) {
      enabled = false;
    }
    toggle.checked = enabled;

    function setEnabled(on) {
      enabled = !!on;
      try {
        localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
      } catch (e) {}
    }

    toggle.addEventListener("change", function () {
      setEnabled(toggle.checked);
    });

    function applyPayload(data) {
      var list = data.devices || [];
      var byId = {};
      list.forEach(function (d) {
        byId[d.bad_id] = d;
      });
      var existing = {};
      table.querySelectorAll("tr[data-bad-id]").forEach(function (tr) {
        var id = tr.getAttribute("data-bad-id");
        if (!id) return;
        existing[id] = tr;
        if (byId[id]) applyRow(tr, byId[id]);
        else tr.remove();
      });
      var newRows = [];
      list.forEach(function (d) {
        if (!d.bad_id || existing[d.bad_id]) return;
        newRows.push(buildRow(d));
      });
      if (newRows.length && tbody) {
        var wrap = document.createElement("tbody");
        if (!reducedMotion()) wrap.className = "devices-live-in";
        var frag = document.createDocumentFragment();
        newRows.forEach(function (tr) {
          frag.appendChild(tr);
        });
        wrap.appendChild(frag);
        tbody.parentNode.insertBefore(wrap, tbody.nextSibling);
        if (wrap.classList.contains("devices-live-in")) flashNewRows(wrap);
      }
      var shown = document.getElementById("devices-shown-count");
      var totalEl = document.getElementById("devices-total-count");
      if (shown) shown.textContent = String(list.length);
      if (totalEl && data.total != null) totalEl.textContent = String(data.total);
    }

    function tick() {
      if (!enabled || loading || document.hidden) return;
      loading = true;
      var url = "/devices/live.json" + (window.location.search || "");
      fetch(url, { credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(applyPayload)
        .catch(function () {})
        .finally(function () {
          loading = false;
        });
    }

    setInterval(tick, TICK_MS);
  }

  badOnReady(init);
})();
