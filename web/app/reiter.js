// Tab bar at the bottom: deep links (#projekt, #organigramm, #benchmarks, #praesentation),
// links to sections inside a tab (#messung), browser back/forward and keyboard control.

const TITEL = {
  projekt: "Schraubi – Teile-Helfer für Gebrauchtteile-Shops",
  organigramm: "So arbeitet Schraubi – Organigramm",
  benchmarks: "Schraubi – Benchmarks",
  praesentation: "Schraubi – Präsentation",
};

const reiterListe = [...document.querySelectorAll('[role="tab"]')];
const flaechen = new Map(reiterListe.map((r) => [r.getAttribute("aria-controls"), document.getElementById(r.getAttribute("aria-controls"))]));
let aktuell = null;

/** Find the tab id and the optional element to scroll to for a location hash. */
function aufloesen(hash) {
  const ziel = decodeURIComponent(hash.replace(/^#/, ""));
  if (flaechen.has(ziel)) return { reiter: ziel, element: null };
  const element = ziel ? document.getElementById(ziel) : null;
  const flaeche = element?.closest('[role="tabpanel"]');
  if (flaeche) return { reiter: flaeche.id, element };
  return { reiter: "projekt", element: null };
}

function aktivieren(id, { element = null, fokus = null } = {}) {
  const wechsel = id !== aktuell;
  aktuell = id;
  document.documentElement.dataset.reiter = id;
  for (const reiter of reiterListe) {
    const an = reiter.getAttribute("aria-controls") === id;
    reiter.setAttribute("aria-selected", String(an));
    reiter.tabIndex = an ? 0 : -1;
  }
  for (const [flaecheId, flaeche] of flaechen) {
    const an = flaecheId === id;
    flaeche.hidden = !an;
    if (an && wechsel) {
      flaeche.classList.remove("ist-neu");
      void flaeche.offsetWidth;
      flaeche.classList.add("ist-neu");
    }
  }
  document.title = TITEL[id];
  if (element) {
    requestAnimationFrame(() => element.scrollIntoView({ block: "start" }));
  } else if (wechsel) {
    window.scrollTo(0, 0);
  }
  if (fokus) fokus.focus({ preventScroll: true });
  if (wechsel) document.dispatchEvent(new CustomEvent("reiterwechsel", { detail: { id } }));
}

function folgen(hash, fokusAufFlaeche) {
  const { reiter, element } = aufloesen(hash);
  aktivieren(reiter, { element, fokus: fokusAufFlaeche ? element || flaechen.get(reiter) : null });
}

/** Wire up the tab bar; must run once after the DOM is parsed. */
export function starten() {
  document.addEventListener("click", (ereignis) => {
    if (ereignis.defaultPrevented || ereignis.button !== 0 || ereignis.metaKey || ereignis.ctrlKey || ereignis.shiftKey || ereignis.altKey) return;
    const link = ereignis.target.closest('a[href^="#"]');
    if (!link) return;
    const hash = link.getAttribute("href");
    const { reiter, element } = aufloesen(hash);
    const ziel = document.getElementById(hash.slice(1));
    if (!flaechen.has(hash.slice(1)) && !ziel?.closest('[role="tabpanel"]')) return;
    ereignis.preventDefault();
    if (location.hash !== hash) history.pushState(null, "", hash);
    const istReiter = link.getAttribute("role") === "tab";
    aktivieren(reiter, { element, fokus: istReiter ? link : element || flaechen.get(reiter) });
  });

  document.querySelector('[role="tablist"]').addEventListener("keydown", (ereignis) => {
    const index = reiterListe.indexOf(document.activeElement);
    if (index < 0) return;
    const ziele = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: reiterListe.length - 1 };
    if (!(ereignis.key in ziele)) return;
    ereignis.preventDefault();
    const neu = reiterListe[(ziele[ereignis.key] + reiterListe.length) % reiterListe.length];
    history.pushState(null, "", neu.getAttribute("href"));
    aktivieren(neu.getAttribute("aria-controls"), { fokus: neu });
  });

  window.addEventListener("popstate", () => folgen(location.hash, false));
  window.addEventListener("hashchange", () => folgen(location.hash, false));
  // The browser jumps to the panel element named in the hash on load; a tab link should open at the top.
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  folgen(location.hash, false);
  const { element } = aufloesen(location.hash);
  window.addEventListener("load", () => (element ? element.scrollIntoView({ block: "start" }) : window.scrollTo(0, 0)), { once: true });
}

/** The id of the visible tab. */
export function sichtbarerReiter() {
  return aktuell;
}
