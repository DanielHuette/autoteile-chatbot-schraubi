// Presentation tab: scenes that play by themselves. The chapter bar's CSS animation is the clock,
// so pausing it pauses the scene motion and the timing together. A run that reaches the end of
// the last scene opens the project tab; with reduced motion nothing plays or switches by itself.

const DAUER_MS = [5600, 6000, 6000, 5600, 5600, 5600, 7400];

/** Set up the film; returns hooks for the tab router. */
export function starten() {
  const film = document.querySelector("[data-film]");
  if (!film) return { sichtbar() {} };
  const ruhig = matchMedia("(prefers-reduced-motion: reduce)");
  const szenen = [...film.querySelectorAll("[data-szene]")];
  const liste = film.querySelector("[data-film-kapitel]");
  const knopf = film.querySelector("[data-film-spielen]");
  const untertitel = film.querySelector("[data-film-untertitel]");
  let index = 0;
  let laeuft = false;
  let schonGestartet = false;

  const kapitel = szenen.map((szene, i) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const titel = document.createElement("span");
    titel.className = "kapitel__titel";
    titel.textContent = `${i + 1}. ${szene.dataset.szene}`;
    const balken = document.createElement("span");
    balken.className = "kapitel__balken";
    balken.setAttribute("aria-hidden", "true");
    balken.addEventListener("animationend", () => {
      if (!laeuft) return;
      if (index + 1 < szenen.length) zeigen(index + 1, true);
      else if (ruhig.matches || !zumProjekt()) { film.dataset.ende = "ja"; setzeLauf(false); }
    });
    button.append(titel, balken);
    button.addEventListener("click", () => zeigen(i, true));
    li.style.setProperty("--dauer", `${DAUER_MS[i]}ms`);
    li.append(button);
    liste.append(li);
    return li;
  });

  // Played to the end: back to the first scene, armed to start again on the next visit, and over
  // to the project tab through its own link so address, history and tab bar follow.
  function zumProjekt() {
    const reiter = document.querySelector('[role="tab"][aria-controls="projekt"]');
    if (!reiter) return false;
    zeigen(0, false);
    schonGestartet = false;
    reiter.click();
    return true;
  }

  function setzeLauf(an) {
    laeuft = an;
    film.toggleAttribute("data-pausiert", !an);
    knopf.setAttribute("aria-label", an ? "Film anhalten" : "Film abspielen");
    knopf.querySelector("use").setAttribute("href", an ? "#i-pause" : "#i-play");
  }

  function zeigen(neu, weiterLaufen = laeuft) {
    index = neu;
    delete film.dataset.ende;
    szenen.forEach((szene, i) => {
      szene.classList.toggle("ist-aktiv", false);
      szene.setAttribute("aria-hidden", String(i !== index));
    });
    void szenen[index].offsetWidth;
    szenen[index].classList.add("ist-aktiv");
    kapitel.forEach((li, i) => {
      li.classList.toggle("ist-aktiv", false);
      li.classList.toggle("ist-gesehen", i < index);
      const button = li.querySelector("button");
      if (i === index) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
    void kapitel[index].offsetWidth;
    kapitel[index].classList.add("ist-aktiv");
    untertitel.textContent = `${index + 1} / ${szenen.length}  ${szenen[index].dataset.szene}`;
    setzeLauf(weiterLaufen);
  }

  knopf.addEventListener("click", () => {
    if (film.dataset.ende === "ja") zeigen(0, true);
    else setzeLauf(!laeuft);
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) setzeLauf(false); });

  zeigen(0, false);
  return {
    sichtbar(an) {
      if (!an) { setzeLauf(false); return; }
      if (!schonGestartet && !ruhig.matches) {
        schonGestartet = true;
        zeigen(0, true);
      }
    },
  };
}
