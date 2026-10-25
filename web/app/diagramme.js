// Draws the benchmark charts and their table views from the measurement files.

import { de, formatieren } from "./messwerte.js";

const VERFAHREN = [
  ["A_volltext", "Nur Volltextsuche"],
  ["B_vektor", "Nur Vektorsuche"],
  ["C_hybrid", "Beides zusammengeführt"],
  ["D_voll", "Schraubi vollständig"],
];

// Labels as in bench/diagramme.py, so page and README charts use the same words.
const GRUPPEN = {
  umgangssprache: "Umgangssprache",
  umschreibung: "Umschreibung",
  synonym: "anderes Wort",
  tippfehler: "Tippfehler",
  schadensbild: "Schadensbild",
  normal: "Fachbegriff",
  aus_bestand: "aus dem Bestand",
  unsinn: "fremde Themen",
};

const prozent = (w) => formatieren(w, "prozent");

function el(tag, klasse, text) {
  const element = document.createElement(tag);
  if (klasse) element.className = klasse;
  if (text !== undefined) element.textContent = text;
  return element;
}

function achse(marken, einheit, klasse = "achse") {
  const zeile = el("div", klasse);
  zeile.setAttribute("aria-hidden", "true");
  zeile.append(el("span"));
  const leiste = el("div", "achse__marken");
  const hoechst = marken[marken.length - 1];
  marken.forEach((wert, i) => {
    const marke = el("span", i % 2 === 1 ? "nur-breit-marke" : "", `${de(wert, 0)}${einheit}`);
    marke.style.left = `${(wert / hoechst) * 100}%`;
    leiste.append(marke);
  });
  zeile.append(leiste, el("span"));
  return zeile;
}

function balken({ name, wert, anteil, farbe, tipp, bestes = false, mitName = true }) {
  const zeile = el("div", `balken${bestes ? " balken--bestes" : ""}`);
  if (mitName) zeile.append(el("span", "balken__name", name));
  const spur = el("div", "balken__spur");
  const fuellung = el("div", `balken__fuellung${farbe ? ` balken__fuellung--${farbe}` : ""}`);
  fuellung.style.setProperty("--wert", String(anteil));
  fuellung.tabIndex = 0;
  fuellung.dataset.tipp = tipp;
  fuellung.setAttribute("role", "img");
  fuellung.setAttribute("aria-label", tipp);
  spur.append(fuellung);
  zeile.append(spur, el("span", "balken__wert", wert));
  return zeile;
}

function verfahrensDiagramm(flaeche, ergebnis, schluessel) {
  for (const [kurz, name] of VERFAHREN) {
    const r = ergebnis[kurz];
    const wert = r[schluessel];
    const tipp = schluessel === "top1_prozent"
      ? `${name}: richtiges Teil auf Platz 1 in ${prozent(wert)} der Anfragen, in den ersten drei in ${prozent(r.top3_prozent)}.`
      : `${name}: falsches Teil ganz oben in ${prozent(wert)} der Anfragen.`;
    flaeche.append(balken({ name, wert: prozent(wert), anteil: wert, farbe: kurz === "D_voll" ? "gold" : "", tipp, bestes: kurz === "D_voll" }));
  }
  flaeche.append(achse([0, 25, 50, 75, 100], " %"));
}

function gruppenDiagramm(flaeche, ergebnis) {
  const vektor = ergebnis.B_vektor.gruppen;
  const voll = ergebnis.D_voll.gruppen;
  const reihen = Object.keys(voll).sort((a, b) => voll[a].top1_prozent - voll[b].top1_prozent);
  for (const gruppe of reihen) {
    const name = GRUPPEN[gruppe] ?? gruppe;
    const von = vektor[gruppe].top1_prozent;
    const bis = voll[gruppe].top1_prozent;
    const zeile = el("div", "hantel");
    const beschriftung = el("span", "hantel__name", name);
    beschriftung.append(el("small", "", `${voll[gruppe].n} Anfragen`));
    const spur = el("div", "hantel__spur");
    spur.style.setProperty("--von", String(Math.min(von, bis)));
    spur.style.setProperty("--bis", String(Math.max(von, bis)));
    const steg = el("span", "hantel__steg");
    const blau = el("span", "hantel__punkt hantel__punkt--blau");
    const gold = el("span", "hantel__punkt hantel__punkt--gold");
    blau.style.setProperty("--von", String(von));
    gold.style.setProperty("--bis", String(bis));
    for (const [punkt, wer, wert] of [[blau, "Vektorsuche allein", von], [gold, "Schraubi vollständig", bis]]) {
      const tipp = `${name}, ${voll[gruppe].n} Anfragen: ${wer} ${prozent(wert)}`;
      punkt.tabIndex = 0;
      punkt.dataset.tipp = tipp;
      punkt.setAttribute("role", "img");
      punkt.setAttribute("aria-label", tipp);
    }
    spur.append(steg, blau, gold);
    const werte = el("span", "hantel__werte");
    werte.append(`${prozent(von)} → `, el("b", "", prozent(bis)));
    zeile.append(beschriftung, spur, werte);
    flaeche.append(zeile);
  }
  flaeche.append(achse([0, 25, 50, 75, 100], " %", "achse achse--hantel"));
}

function latenzDiagramm(flaeche, latenz) {
  const groessen = Object.keys(latenz.ergebnis).sort((a, b) => Number(a) - Number(b));
  const hoechst = Math.ceil(Math.max(...groessen.map((g) => latenz.ergebnis[g].sequenziell.median_ms)) / 2) * 2;
  for (const groesse of groessen) {
    const r = latenz.ergebnis[groesse];
    const name = `${formatieren(r.teile, "zahl")} Teile`;
    const gruppe = el("div", "balkengruppe");
    gruppe.append(el("span", "balken__name", name));
    gruppe.append(balken({
      name, mitName: false, farbe: "blau", wert: formatieren(r.sequenziell.median_ms, "ms"), anteil: (r.sequenziell.median_ms / hoechst) * 100,
      tipp: `${name}, ohne Index: Median ${formatieren(r.sequenziell.median_ms, "ms")}, langsamste Messung ${formatieren(r.sequenziell.max_ms, "ms")}.`,
    }));
    gruppe.append(balken({
      name, mitName: false, farbe: "gold", wert: formatieren(r.hnsw.median_ms, "ms"), anteil: (r.hnsw.median_ms / hoechst) * 100,
      tipp: `${name}, mit HNSW-Index: Median ${formatieren(r.hnsw.median_ms, "ms")}, ${formatieren(r.recall_at_k, "anteil")} gleiche Treffer, Index ${formatieren(r.indexgroesse_bytes, "mb")}.`,
    }));
    flaeche.append(gruppe);
  }
  const marken = [];
  for (let wert = 0; wert <= hoechst; wert += hoechst / 4) marken.push(wert);
  flaeche.append(achse(marken, " ms", "achse achse--gruppe"));
}

function tabelle(kopf, zeilen) {
  const t = el("table");
  const thead = el("thead");
  const kopfzeile = el("tr");
  for (const spalte of kopf) kopfzeile.append(el("th", "", spalte));
  thead.append(kopfzeile);
  const tbody = el("tbody");
  for (const zeile of zeilen) {
    const tr = el("tr");
    for (const zelle of zeile) tr.append(el("td", "", zelle));
    tbody.append(tr);
  }
  t.append(thead, tbody);
  return t;
}

function tabellenEinsetzen(q, l) {
  const e = q.ergebnis;
  const ziele = {
    verfahren: tabelle(
      ["Verfahren", "Platz 1", "erste 3", "falsch oben"],
      VERFAHREN.map(([k, n]) => [n, prozent(e[k].top1_prozent), prozent(e[k].top3_prozent), prozent(e[k].falsch_top1_prozent)]),
    ),
    gruppen: tabelle(
      ["Anfrageart", "Anzahl", "Vektor allein", "Schraubi"],
      Object.keys(GRUPPEN).filter((g) => g in e.D_voll.gruppen).map((g) => [GRUPPEN[g], String(e.D_voll.gruppen[g].n), prozent(e.B_vektor.gruppen[g].top1_prozent), prozent(e.D_voll.gruppen[g].top1_prozent)]),
    ),
    latenz: tabelle(
      ["Teile", "ohne Index", "mit Index", "gleiche Treffer"],
      Object.keys(l.ergebnis).sort((a, b) => Number(a) - Number(b)).map((g) => {
        const r = l.ergebnis[g];
        return [formatieren(r.teile, "zahl"), formatieren(r.sequenziell.median_ms, "ms"), formatieren(r.hnsw.median_ms, "ms"), formatieren(r.recall_at_k, "anteil")];
      }),
    ),
  };
  for (const [name, inhalt] of Object.entries(ziele)) {
    const ort = document.querySelector(`[data-tabelle="${name}"]`);
    ort.querySelector("table")?.remove();
    ort.append(inhalt);
  }
}

let tipp = null;

function tippZeigen(ziel, x, y) {
  tipp.textContent = ziel.dataset.tipp;
  tipp.classList.add("ist-sichtbar");
  const rahmen = tipp.getBoundingClientRect();
  const links = Math.min(Math.max(8, x - rahmen.width / 2), window.innerWidth - rahmen.width - 8);
  const oben = y - rahmen.height - 14 < 8 ? y + 18 : y - rahmen.height - 14;
  tipp.style.left = `${links}px`;
  tipp.style.top = `${oben}px`;
}

function tippEinrichten(wurzel) {
  tipp = el("div", "tipp");
  tipp.setAttribute("aria-hidden", "true");
  document.body.append(tipp);
  const verstecken = () => tipp.classList.remove("ist-sichtbar");
  wurzel.addEventListener("pointermove", (e) => {
    const ziel = e.target.closest("[data-tipp]");
    if (ziel) tippZeigen(ziel, e.clientX, e.clientY);
    else verstecken();
  });
  wurzel.addEventListener("pointerleave", verstecken);
  wurzel.addEventListener("focusin", (e) => {
    const ziel = e.target.closest("[data-tipp]");
    if (!ziel) return;
    const r = ziel.getBoundingClientRect();
    tippZeigen(ziel, r.left + r.width / 2, r.top);
  });
  wurzel.addEventListener("focusout", verstecken);
  window.addEventListener("scroll", verstecken, { passive: true });
}

/** Draw all charts on the benchmarks tab. */
export function zeichnen(daten) {
  const wurzel = document.getElementById("benchmarks");
  const flaeche = (name) => {
    const ort = wurzel.querySelector(`[data-diagramm="${name}"] .diagramm__flaeche`);
    ort.replaceChildren();
    return ort;
  };
  verfahrensDiagramm(flaeche("treffer"), daten.q.ergebnis, "top1_prozent");
  verfahrensDiagramm(flaeche("falsch"), daten.q.ergebnis, "falsch_top1_prozent");
  gruppenDiagramm(flaeche("gruppen"), daten.q.ergebnis);
  latenzDiagramm(flaeche("latenz"), daten.l);
  tabellenEinsetzen(daten.q, daten.l);
  if (!tipp) tippEinrichten(wurzel);
}
