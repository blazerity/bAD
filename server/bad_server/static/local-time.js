(function () {
  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function formatLocal(iso) {
    var d = new Date(iso);
    if (Number.isNaN(d.getTime())) {
      return iso;
    }
    return (
      pad2(d.getHours()) +
      ":" +
      pad2(d.getMinutes()) +
      ":" +
      pad2(d.getSeconds()) +
      " " +
      pad2(d.getDate()) +
      "." +
      pad2(d.getMonth() + 1) +
      "." +
      d.getFullYear()
    );
  }

  function apply() {
    document.querySelectorAll("time.local-time[datetime]").forEach(function (el) {
      var iso = el.getAttribute("datetime");
      if (!iso) {
        return;
      }
      el.textContent = formatLocal(iso);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }
})();
