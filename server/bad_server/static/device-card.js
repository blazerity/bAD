(() => {
  const shell = document.getElementById("device-shell");
  if (!shell) return;

  function showView(viewId) {
    if (!viewId) return;
    const panel = shell.querySelector(`[data-device-panel="${viewId}"]`);
    if (!panel) return;

    shell.querySelectorAll("[data-device-panel]").forEach((el) => {
      el.classList.toggle("is-active", el === panel);
    });
    shell.querySelectorAll("[data-device-nav]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-device-nav") === viewId);
    });
    shell.setAttribute("data-active-view", viewId);

    const url = new URL(window.location.href);
    url.searchParams.set("view", viewId);
    window.history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
  }

  shell.addEventListener("click", (ev) => {
    const link = ev.target.closest("[data-device-nav]");
    if (!link || !shell.contains(link)) return;
    const viewId = link.getAttribute("data-device-nav");
    if (!viewId) return;
    if (shell.querySelector(`[data-device-panel="${viewId}"]`)) {
      ev.preventDefault();
      showView(viewId);
    }
  });
})();
