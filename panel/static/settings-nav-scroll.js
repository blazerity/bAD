/** Прокрутка активного пункта рельса вкладок в кадр на узком экране. */
(function () {
  var MQ = window.matchMedia("(max-width: 640px)");

  function scrollActive(rail) {
    if (!rail || !MQ.matches) return;
    var active = rail.querySelector(".settings-nav-item.active");
    if (!active) return;
    try {
      active.scrollIntoView({ inline: "center", block: "nearest", behavior: "auto" });
    } catch (e) {
      active.scrollIntoView(false);
    }
  }

  function scan() {
    document.querySelectorAll(".settings-nav-rail, .device-card .device-shell .settings-nav").forEach(scrollActive);
  }

  function init() {
    scan();
    MQ.addEventListener("change", scan);
    window.addEventListener("resize", function () {
      if (MQ.matches) scan();
    });
    document.addEventListener(
      "click",
      function (ev) {
        var link = ev.target.closest(".settings-nav-item");
        if (!link) return;
        var rail = link.closest(".settings-nav-rail, .settings-nav");
        if (!rail || !rail.closest(".device-card .device-shell, .settings-page")) return;
        requestAnimationFrame(function () {
          scrollActive(rail);
        });
      },
      true
    );
  }

  badOnReady(init);
})();
