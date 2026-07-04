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
  var input = document.getElementById("search-input");
  var resultsEl = document.getElementById("search-results");
  var filterBtns = document.querySelectorAll(".filter-btn");
  var activeFilter = "all";
  var indexData = [];

  fetch("search-index.json")
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      indexData = data;
    })
    .catch(function () {
      indexData = [];
    });

  function render() {
    var query = input.value.trim().toLowerCase();
    resultsEl.innerHTML = "";
    if (!query) return;

    var matches = indexData.filter(function (item) {
      if (activeFilter !== "all" && item.category !== activeFilter) return false;
      var haystack = (item.title + " " + item.snippet).toLowerCase();
      return haystack.indexOf(query) !== -1;
    });

    matches.slice(0, 50).forEach(function (item) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = item.date + ".html#" + item.category;
      a.textContent = item.title;
      var meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = item.date + " · " + item.category;
      li.appendChild(a);
      li.appendChild(meta);
      resultsEl.appendChild(li);
    });

    if (!matches.length) {
      var li = document.createElement("li");
      li.textContent = "검색 결과가 없습니다.";
      resultsEl.appendChild(li);
    }
  }

  input.addEventListener("input", render);
  filterBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filterBtns.forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      activeFilter = btn.dataset.filter;
      render();
    });
  });
});
