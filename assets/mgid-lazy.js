/**
 * Lazy MGID slots only — homepage top uses inline _mgc.load in page footer.
 */
(function () {
  var loaded = false;

  function triggerMgidLoad() {
    if (loaded) return;
    loaded = true;
    (function (w, q) {
      w[q] = w[q] || [];
      w[q].push(["_mgc.load"]);
    })(window, "_mgq");
  }

  function init() {
    var lazy = document.querySelectorAll(".mgid-slot--lazy");
    if (!lazy.length) return;

    if (!("IntersectionObserver" in window)) {
      triggerMgidLoad();
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) {
            triggerMgidLoad();
            observer.disconnect();
            return;
          }
        }
      },
      { rootMargin: "320px 0px", threshold: 0.01 }
    );

    for (var j = 0; j < lazy.length; j++) {
      observer.observe(lazy[j]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
