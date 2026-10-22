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

  /** one / few (2–4) / many (5+) — формы после числа */
  function pluralRu(n, one, few, many) {
    var mod10 = n % 10;
    var mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) {
      return one;
    }
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) {
      return few;
    }
    return many;
  }

  function formatRelative(iso, nowMs) {
    var d = new Date(iso);
    if (Number.isNaN(d.getTime())) {
      return iso;
    }
    var diff = nowMs - d.getTime();
    if (diff < 0) {
      diff = 0;
    }

    var sec = Math.floor(diff / 1000);
    if (sec < 60) {
      return "только что";
    }

    var min = Math.floor(sec / 60);
    if (min < 60) {
      return (
        min +
        " " +
        pluralRu(min, "минуту", "минуты", "минут") +
        " назад"
      );
    }

    var hr = Math.floor(min / 60);
    if (hr < 24) {
      return (
        hr + " " + pluralRu(hr, "час", "часа", "часов") + " назад"
      );
    }

    var days = Math.floor(hr / 24);
    if (days === 1) {
      return "день назад";
    }
    if (days < 7) {
      return (
        days + " " + pluralRu(days, "день", "дня", "дней") + " назад"
      );
    }
    if (days < 14) {
      return "неделю назад";
    }
    if (days < 30) {
      var weeks = Math.floor(days / 7);
      if (weeks < 2) {
        return "неделю назад";
      }
      return (
        weeks +
        " " +
        pluralRu(weeks, "неделю", "недели", "недель") +
        " назад"
      );
    }
    if (days < 60) {
      return "месяц назад";
    }
    if (days < 365) {
      var months = Math.floor(days / 30);
      if (months < 2) {
        return "месяц назад";
      }
      return (
        months +
        " " +
        pluralRu(months, "месяц", "месяца", "месяцев") +
        " назад"
      );
    }

    var years = Math.floor(days / 365);
    if (years < 2) {
      return "год назад";
    }
    return (
      years + " " + pluralRu(years, "год", "года", "лет") + " назад"
    );
  }

  function apply() {
    var nowMs = Date.now();
    document.querySelectorAll("time.local-time[datetime]").forEach(function (el) {
      var iso = el.getAttribute("datetime");
      if (!iso) {
        return;
      }
      var absolute = formatLocal(iso);
      var mode = (el.getAttribute("data-time-mode") || "relative").toLowerCase();

      if (mode === "absolute") {
        el.textContent = absolute;
        el.removeAttribute("title");
        el.removeAttribute("aria-label");
        return;
      }

      var relative = formatRelative(iso, nowMs);
      el.textContent = relative;
      el.setAttribute("title", absolute);
      el.setAttribute("aria-label", relative + ", точное время: " + absolute);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  } else {
    apply();
  }

  window.setInterval(apply, 60000);
})();
