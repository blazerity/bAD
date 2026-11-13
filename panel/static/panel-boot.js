/* Shared by panel scripts loaded from base.html. */
window.badDebounce = function (fn, ms) {
  var t;
  return function () {
    var args = arguments;
    var self = this;
    clearTimeout(t);
    t = setTimeout(function () {
      fn.apply(self, args);
    }, ms);
  };
};

window.badOnReady = function (init) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
};
