// Entry point: tab router first, then the parts that need measurements or a visible tab.

import { starten as reiterStarten, sichtbarerReiter } from "./reiter.js";
import { laden, einsetzen } from "./messwerte.js";
import { zeichnen } from "./diagramme.js";
import { starten as planStarten } from "./plan.js";
import { starten as filmStarten } from "./film.js";
import { starten as rechnerStarten } from "./rechner.js";

const plan = planStarten();
const film = filmStarten();
let diagrammeFertig = false;

function anzeigen(id) {
  plan.sichtbar(id === "organigramm");
  film.sichtbar(id === "praesentation");
  if (id === "benchmarks" && !diagrammeFertig) {
    diagrammeFertig = true;
    laden().then(zeichnen).catch(() => { diagrammeFertig = false; });
  }
}

for (const balken of document.querySelectorAll(".vergleich__wert b")) {
  balken.parentElement.style.setProperty("--anteil", String(parseFloat(balken.textContent.replace(",", "."))));
}

document.addEventListener("reiterwechsel", (e) => anzeigen(e.detail.id));
reiterStarten();
anzeigen(sichtbarerReiter());

laden()
  .then((daten) => {
    einsetzen(daten);
    rechnerStarten(daten.q);
  })
  .catch(() => {
    // Without the measurement files the static figures in the HTML stay; the charts show a note.
    for (const ort of document.querySelectorAll(".diagramm__flaeche")) {
      if (!ort.childElementCount) ort.textContent = "Die Messdatei konnte nicht geladen werden. Die Werte stehen in der Tabelle auf der Projektseite.";
    }
  });
