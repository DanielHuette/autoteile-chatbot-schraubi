// Loads the measurement files (copies of bench/results/*.json) and fills every [data-wert] element.
// The same formats are implemented in scripts/messwerte_einsetzen.py, which keeps the static HTML in sync.

const QUELLEN = { q: "daten/qualitaet.json", l: "daten/latenz.json" };
let ladung = null;

/** Format a German number with a fixed number of decimals. */
export function de(wert, stellen = 1) {
  return wert.toLocaleString("de-DE", { minimumFractionDigits: stellen, maximumFractionDigits: stellen });
}

const FORMATE = {
  prozent: (w) => `${de(w, 1)} %`,
  anteil: (w) => `${de(w * 100, 1)} %`,
  ms: (w) => `${de(w, 2)} ms`,
  faktor: (w) => `${de(w, 1)}-mal`,
  zahl: (w) => de(w, 0),
  mb: (w) => `${de(w / 1024 / 1024, 1)} MB`,
  text: (w) => String(w),
};

/** Format a measured value the way the page and README show it. */
export function formatieren(wert, format) {
  const fn = FORMATE[format];
  if (!fn) throw new Error(`Unbekanntes Format: ${format}`);
  return fn(wert);
}

/** Read a dotted path such as "ergebnis.D_voll.top1_prozent" from an object. */
export function lesen(objekt, pfad) {
  return pfad.split(".").reduce((teil, schluessel) => (teil == null ? undefined : teil[schluessel]), objekt);
}

/** Fetch both measurement files once; later calls share the same promise. */
export function laden() {
  if (!ladung) {
    ladung = Promise.all(
      Object.entries(QUELLEN).map(async ([kuerzel, pfad]) => {
        const antwort = await fetch(pfad, { cache: "no-cache" });
        if (!antwort.ok) throw new Error(`${pfad}: HTTP ${antwort.status}`);
        return [kuerzel, await antwort.json()];
      }),
    ).then(Object.fromEntries);
  }
  return ladung;
}

/** Replace the text of every [data-wert] element with the value from the measurement files. */
export function einsetzen(daten, wurzel = document) {
  for (const element of wurzel.querySelectorAll("[data-wert]")) {
    const [kuerzel, pfad] = element.dataset.wert.split(":");
    const wert = lesen(daten[kuerzel], pfad);
    if (wert === undefined) continue;
    const text = formatieren(wert, element.dataset.format);
    if (element.textContent !== text) element.textContent = text;
  }
}
