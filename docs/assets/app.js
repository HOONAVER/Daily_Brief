(function initTheme() {
  var saved = localStorage.getItem("theme");
  var theme = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme");
      var next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
    });
  });
})();

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".accordion-header").forEach(function (header) {
    header.addEventListener("click", function () {
      header.parentElement.classList.toggle("open");
    });
  });

  var container = document.getElementById("swipe-container");
  var dots = document.querySelectorAll(".dot");
  if (!container || !dots.length) return;

  function setActive(index) {
    dots.forEach(function (dot, i) {
      dot.classList.toggle("active", i === index);
    });
  }

  container.addEventListener("scroll", function () {
    var index = Math.round(container.scrollLeft / container.clientWidth);
    setActive(index);
  });

  dots.forEach(function (dot) {
    dot.addEventListener("click", function () {
      var index = parseInt(dot.dataset.index, 10);
      container.scrollTo({ left: index * container.clientWidth, behavior: "smooth" });
    });
  });

  var hash = window.location.hash.replace("#", "");
  var panels = Array.prototype.slice.call(document.querySelectorAll(".panel"));
  var targetIndex = panels.findIndex(function (p) {
    return p.id === hash;
  });
  if (targetIndex >= 0) {
    container.scrollLeft = targetIndex * container.clientWidth;
    setActive(targetIndex);
  } else {
    setActive(0);
  }
});
