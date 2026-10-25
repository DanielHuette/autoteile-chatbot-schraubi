// Worked example for shop owners: extra finds, orders and revenue from the measured hit rates.

const fmt = (n) => Math.round(n).toLocaleString("de-DE");

/** Connect the calculator inputs; hit rates come from bench/results/qualitaet.json. */
export function starten(qualitaet) {
  const form = document.getElementById("rechner");
  if (!form) return;
  const heute = qualitaet.ergebnis.A_volltext.top1_prozent / 100;
  const mitSchraubi = qualitaet.ergebnis.D_voll.top1_prozent / 100;
  const wert = (id, grenze = Infinity) => Math.min(Math.max(0, parseFloat(document.getElementById(id).value) || 0), grenze);

  function rechnen() {
    const gefunden = wert("r-suchen") * (wert("r-anteil", 100) / 100) * (mitSchraubi - heute);
    const bestellungen = gefunden * (wert("r-kauf", 100) / 100);
    document.getElementById("r-gefunden").textContent = fmt(gefunden);
    document.getElementById("r-bestellungen").textContent = fmt(bestellungen);
    document.getElementById("r-umsatz").textContent = `${fmt(bestellungen * wert("r-wert") * 12)} €`;
  }
  form.addEventListener("input", rechnen);
  form.addEventListener("submit", (e) => e.preventDefault());
  rechnen();
}
