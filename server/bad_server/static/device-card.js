(() => {
  const shell = document.getElementById("device-shell");
  if (!shell) return;

  function showView(viewId) {
    const panel = shell.querySelector(`[data-device-panel="${viewId}"]`);
    if (!panel) return false;

    shell.querySelectorAll("[data-device-panel]").forEach((el) => {
      el.classList.toggle("is-active", el === panel);
    });
    shell.querySelectorAll("[data-device-nav]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-device-nav") === viewId);
    });

    const url = new URL(window.location.href);
    url.searchParams.set("view", viewId);
    window.history.replaceState(null, "", url.pathname + url.search);
    return true;
  }

  shell.addEventListener("click", (ev) => {
    const link = ev.target.closest("[data-device-nav]");
    if (!link) return;
    const viewId = link.getAttribute("data-device-nav");
    if (!viewId) return;
    if (showView(viewId)) {
      ev.preventDefault();
    }
  });
})();
