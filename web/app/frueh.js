// Runs in <head> before first paint so a deep link such as #benchmarks never flashes the first tab.
(() => {
  const reiter = ["projekt", "organigramm", "benchmarks", "praesentation"];
  const ziel = decodeURIComponent(location.hash.slice(1));
  const wurzel = document.documentElement;
  wurzel.classList.add("js");
  wurzel.dataset.reiter = reiter.includes(ziel) ? ziel : "projekt";
})();
