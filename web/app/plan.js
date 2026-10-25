// Organigramm: a gold pulse walks through the stations; the panel shows what happens there,
// the skills applied and which parts of the database the station touches.

const SPEICHER = { parts: "Teilestamm", hnsw: "Vektorindex", protokoll: "Ereignisprotokoll", sales: "Verkaufsdaten" };
const TAKT_MS = 4200;

/** Set up the animated organigramm; returns hooks for the tab router. */
export function starten() {
  const plan = document.querySelector("[data-plan]");
  if (!plan) return { sichtbar() {} };
  const ruhig = matchMedia("(prefers-reduced-motion: reduce)");
  const stationen = [...plan.querySelectorAll("[data-station]")];
  const wege = [...plan.querySelectorAll("[data-weg]")];
  const titel = plan.querySelector("[data-tafel-titel]");
  const inhalt = plan.querySelector("[data-tafel-inhalt]");
  const zaehler = plan.querySelector("[data-tafel-zaehler]");
  const spielen = plan.querySelector("[data-plan-spielen]");
  const speicher = [...plan.querySelectorAll("[data-speicher]")];
  const salesHinweis = plan.querySelector("[data-sales-hinweis]");

  for (const weg of wege) weg.querySelector(".plan__stationen").append(Object.assign(document.createElement("span"), { className: "puls" }));
  for (const station of stationen) {
    const genutzt = station.dataset.nutzt.split(" ").filter(Boolean);
    if (!genutzt.length) continue;
    const zeile = document.createElement("p");
    zeile.className = "station__nutzt";
    zeile.textContent = `Datenbank: ${genutzt.map((s) => (s === "sales-gesperrt" ? "Verkaufsdaten gesperrt" : SPEICHER[s])).join(", ")}`;
    station.querySelector(".station__mehr").append(zeile);
  }

  let index = 0;
  let laeuft = !ruhig.matches;
  let sichtbar = false;
  let uhr = 0;

  function zeigen(neu) {
    index = (neu + stationen.length) % stationen.length;
    const aktiv = stationen[index];
    const aktiverWeg = aktiv.closest("[data-weg]");
    stationen.forEach((s, i) => {
      s.classList.toggle("ist-aktiv", i === index);
      s.classList.toggle("ist-erledigt", s.closest("[data-weg]") === aktiverWeg && i < index);
      s.querySelector(".station__kopf").setAttribute("aria-expanded", String(i === index));
    });
    for (const weg of wege) {
      const an = weg === aktiverWeg;
      weg.classList.toggle("ist-aktiv", an);
      if (an) {
        const kopf = aktiv.querySelector(".station__kopf");
        weg.querySelector(".plan__stationen").style.setProperty("--puls-y", `${aktiv.offsetTop + kopf.offsetHeight / 2}px`);
      }
    }
    titel.textContent = aktiv.querySelector(".station__name").textContent;
    zaehler.textContent = `Station ${index + 1} von ${stationen.length}`;
    inhalt.replaceChildren(...aktiv.querySelector(".station__mehr").cloneNode(true).childNodes);
    inhalt.classList.remove("ist-neu");
    void inhalt.offsetWidth;
    inhalt.classList.add("ist-neu");
    const genutzt = aktiv.dataset.nutzt.split(" ");
    const kundenweg = aktiverWeg.dataset.weg === "kunde";
    for (const s of speicher) {
      const name = s.dataset.speicher;
      s.classList.toggle("ist-genutzt", genutzt.includes(name));
      s.classList.toggle("ist-gesperrt", name === "sales" && kundenweg);
    }
    salesHinweis.textContent = kundenweg ? "für den Chat gesperrt" : "Tabelle sales";
  }

  function planen() {
    clearTimeout(uhr);
    if (laeuft && sichtbar && !document.hidden) uhr = setTimeout(() => { zeigen(index + 1); planen(); }, TAKT_MS);
  }

  function knopf() {
    spielen.setAttribute("aria-label", laeuft ? "Ablauf anhalten" : "Ablauf abspielen");
    spielen.querySelector("use").setAttribute("href", laeuft ? "#i-pause" : "#i-play");
  }

  stationen.forEach((station, i) => {
    station.querySelector(".station__kopf").addEventListener("click", () => {
      laeuft = false;
      knopf();
      zeigen(i);
      planen();
    });
  });
  plan.querySelector("[data-plan-vor]").addEventListener("click", () => { zeigen(index + 1); planen(); });
  plan.querySelector("[data-plan-zurueck]").addEventListener("click", () => { zeigen(index - 1); planen(); });
  spielen.addEventListener("click", () => { laeuft = !laeuft; knopf(); planen(); });
  document.addEventListener("visibilitychange", planen);
  window.addEventListener("resize", () => zeigen(index));

  knopf();
  zeigen(0);
  return {
    sichtbar(an) {
      sichtbar = an;
      if (an) zeigen(index);
      planen();
    },
  };
}
