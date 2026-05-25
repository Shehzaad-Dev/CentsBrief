/**
 * CentsBrief MGID loader
 * - Homepage top banner (.mgid-slot--eager): loads as soon as the page is ready
 * - Article units (.mgid-slot--lazy): load when the slot is near the viewport
 * - One _mgc.load per page (MGID requirement)
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

  function observeLazySlots() {
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
      { rootMargin: "280px 0px", threshold: 0.01 }
    );

    for (var j = 0; j < lazy.length; j++) {
      observer.observe(lazy[j]);
    }
  }

  function init() {
    var eager = document.querySelectorAll(".mgid-slot--eager");
    if (eager.length) {
      triggerMgidLoad();
    }
    observeLazySlots();
    if (!eager.length && !document.querySelectorAll(".mgid-slot--lazy").length) {
      return;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
