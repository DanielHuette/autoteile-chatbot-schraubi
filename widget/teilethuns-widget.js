/*!
 * Teile Thuns - Auskunftshelfer "Schraubi"
 * Einbindung in eine beliebige Webseite mit einer Zeile:
 *
 *   <script src="https://IHRE-ADRESSE/widget.js" defer></script>
 *
 * Es wird nichts weiter benoetigt: kein Framework, kein Aufbauwerkzeug,
 * keine zusaetzliche Datei. Alles steckt hier drin.
 *
 * Gestaltung fuer aeltere Nutzer:
 *   - Schrift ab 17 Pixel, Knoepfe mindestens 48 Pixel hoch
 *   - starke Kontraste, keine grauen Hinweistexte auf hellgrau
 *   - jeder Schritt hat einen Zurueck-Knopf, nichts ist eine Falle
 *   - keine Zeitbegrenzung, kein automatisches Schliessen
 *   - Tastaturbedienung und Screenreader-Beschriftungen durchgaengig
 */
(function () {
  "use strict";

  if (window.__teilethunsGeladen) return;
  window.__teilethunsGeladen = true;

  // ---------------------------------------------------------------
  // Einstellungen. Lassen sich im script-Tag ueberschreiben:
  //   <script src="..." data-api="https://bot.example.de" defer></script>
  // ---------------------------------------------------------------
  var skript = document.currentScript ||
    (function () {
      var alle = document.getElementsByTagName("script");
      return alle[alle.length - 1];
    })();

  var API = (skript && skript.getAttribute("data-api")) ||
    (skript && skript.src ? skript.src.replace(/\/widget\.js.*$/, "") : "");
  var START_OFFEN = skript && skript.getAttribute("data-offen") === "ja";
  var POSITION = (skript && skript.getAttribute("data-position")) || "rechts";

  var T = {
    titel: "Schraubi",
    untertitel: "Schraubi \u2013 Ihr Teile-Helfer",
    eingabe: "Z. B.: Rücklicht links Golf",
    senden: "Senden",
    oeffnen: "Hilfe zu Autoteilen",
    schliessen: "Fenster schließen",
    laedt: "Schraubi sucht ...",
    fehler: "Verbindung unterbrochen. Bitte noch einmal versuchen.",
    kiHinweis: "Automatischer Helfer \u2013 kein Mensch",
    adminAn: "Betriebsleitung anmelden",
    adminPasswort: "Passwort der Betriebsleitung",
    adminAnmelden: "Anmelden",
    adminAb: "Betriebsleitung abmelden",
    adminAbbruch: "Abbrechen"
  };

  // ---------------------------------------------------------------
  // Gestaltung. Alles in einem eigenen Namensraum (tt-), damit nichts
  // mit der Webseite des Betreibers kollidiert.
  // ---------------------------------------------------------------
  var CSS = `
/* ---------------------------------------------------------------
   Farbwelt aus dem Logo von Teile Thuns. Die Werte sind aus der
   Bilddatei gemessen, nicht geschaetzt:
     #3575A8  Schriftband        -> Hauptfarbe
     #5189B8  Sechseck innen     -> helle Flaechen
     #2C5078  Rand des Sechsecks -> Kopfzeile, Tiefe
     #30597F  unteres Band       -> Zwischenton
   Das Bernstein ist die einzige Fremdfarbe: nur fuer den Weg nach
   draussen (eBay) und den Fortschritt, damit beides sofort auffaellt.
   --------------------------------------------------------------- */
.tt-wrap{
  --tt-blau:#3575A8; --tt-blau-hell:#5189B8; --tt-blau-tief:#2C5078;
  --tt-nacht:#1E3A5C; --tt-band:#30597F;
  --tt-signal:#E8872B; --tt-signal-tief:#C56D16;
  --tt-papier:#F2F6FA; --tt-weiss:#FFFFFF;
  --tt-linie:#C8D6E4; --tt-text:#15293D; --tt-text-leise:#4A6782;
  --tt-gruen:#157347; --tt-gruen-feld:#DFF3E8;
  --tt-rot:#9A2222; --tt-rot-feld:#FCE9E9;
  --tt-r-gross:22px; --tt-r-mittel:16px; --tt-r-klein:12px;
  --tt-schatten:0 1px 2px rgba(21,41,61,.08), 0 4px 12px rgba(21,41,61,.10), 0 18px 40px rgba(21,41,61,.16);
  --tt-schatten-knopf:0 1px 1px rgba(255,255,255,.35) inset, 0 2px 5px rgba(21,41,61,.16);
  position:fixed;z-index:2147483000;bottom:20px;
  font:400 17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--tt-text)
}
.tt-wrap.tt-rechts{right:20px}.tt-wrap.tt-links{left:20px}
.tt-wrap *,.tt-wrap *::before,.tt-wrap *::after{box-sizing:border-box}

/* Startknopf: das Logozeichen auf einem plastischen Kissen */
.tt-knopf{display:flex;align-items:center;gap:13px;
  background:linear-gradient(180deg,#3F82B8 0%,var(--tt-blau) 46%,#2F699B 100%);
  color:#fff;border:0;border-radius:999px;padding:10px 26px 10px 12px;
  font-size:18px;font-weight:650;letter-spacing:.1px;cursor:pointer;min-height:66px;
  box-shadow:0 1px 0 rgba(255,255,255,.28) inset, 0 -2px 6px rgba(13,36,58,.25) inset,
             0 6px 16px rgba(21,41,61,.26), 0 16px 34px rgba(21,41,61,.22);
  transition:transform .14s ease, box-shadow .14s ease}
.tt-knopf:hover{transform:translateY(-2px);
  box-shadow:0 1px 0 rgba(255,255,255,.3) inset, 0 -2px 6px rgba(13,36,58,.25) inset,
             0 10px 22px rgba(21,41,61,.3), 0 22px 44px rgba(21,41,61,.24)}
.tt-knopf:active{transform:translateY(1px)}
.tt-knopf:focus-visible{outline:4px solid var(--tt-signal);outline-offset:3px}
.tt-knopf img{width:42px;height:42px;flex:0 0 42px;
  filter:drop-shadow(0 2px 3px rgba(13,36,58,.35))}

/* Fenster */
.tt-fenster{display:none;flex-direction:column;width:min(436px,calc(100vw - 32px));
  height:min(660px,calc(100vh - 110px));background:var(--tt-papier);
  border-radius:var(--tt-r-gross);overflow:hidden;box-shadow:var(--tt-schatten);
  border:1px solid rgba(44,80,120,.14)}
.tt-fenster.tt-offen{display:flex}

/* Kopfzeile mit dem Logo */
.tt-kopf{display:flex;align-items:center;gap:12px;padding:13px 14px;flex:0 0 auto;
  background:linear-gradient(170deg,#3C78AC 0%,var(--tt-blau-tief) 68%,#24456A 100%);
  box-shadow:0 1px 0 rgba(255,255,255,.14) inset, 0 3px 10px rgba(21,41,61,.2);
  position:relative}
.tt-kopf::after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;
  background:linear-gradient(90deg,transparent,rgba(232,135,43,.75),transparent)}
.tt-kopf-zeichen{height:44px;width:auto;display:block;flex:0 0 auto;
  filter:drop-shadow(0 2px 5px rgba(10,28,46,.45))}
.tt-kopf-text{flex:1;min-width:0}
.tt-kopf-marke{font-size:21px;font-weight:800;color:#fff;line-height:1.1;letter-spacing:-.3px;
  text-shadow:0 1px 3px rgba(10,28,46,.5)}
.tt-kopf-marke span{font-weight:400}
.tt-kopf-rolle{font-size:13px;color:#BDD4E8;font-weight:600;letter-spacing:.2px;margin-top:2px}
.tt-zu{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.22);color:#fff;
  border-radius:11px;width:42px;height:42px;font-size:22px;line-height:1;cursor:pointer;flex:0 0 42px;
  transition:background .15s ease}
.tt-zu:hover{background:var(--tt-signal);border-color:var(--tt-signal-tief)}
.tt-zu:focus-visible{outline:3px solid var(--tt-signal);outline-offset:2px}

/* Offenlegung */
.tt-kibanner{background:linear-gradient(180deg,#FFF6EC,#FDEDDC);
  border-bottom:1px solid #F2D5B4;color:#6E3B07;padding:9px 16px;font-size:14px;
  display:flex;align-items:center;gap:9px;flex:0 0 auto}
.tt-kibanner b{font-weight:700}
.tt-kibanner a{color:#8A4708}
.tt-kiz{width:19px;height:19px;flex:0 0 19px;border-radius:50%;background:var(--tt-signal);
  color:#fff;font-size:13px;font-weight:800;display:grid;place-items:center;line-height:1}

.tt-adminbanner{background:linear-gradient(180deg,#14543C,#0E3F2C);color:#CFF3E2;
  padding:10px 16px;font-size:14px;display:none;align-items:center;justify-content:space-between;
  gap:10px;flex:0 0 auto;box-shadow:0 2px 6px rgba(0,0,0,.18)}
.tt-adminbanner.tt-an{display:flex}
.tt-adminbanner button{background:#CFF3E2;color:#0E3F2C;border:0;border-radius:9px;
  padding:7px 13px;font-size:14px;font-weight:700;cursor:pointer;min-height:36px;
  box-shadow:var(--tt-schatten-knopf)}

/* Verlauf */
.tt-lauf{flex:1 1 auto;overflow-y:auto;padding:18px 16px;scroll-behavior:smooth;
  background:
    radial-gradient(120% 60% at 50% 0%, rgba(81,137,184,.1), transparent 60%),
    var(--tt-papier)}
.tt-lauf.tt-adminmodus{background:
    radial-gradient(120% 60% at 50% 0%, rgba(21,115,71,.12), transparent 60%), #EEF6F1}

.tt-reihe{display:flex;gap:10px;margin:0 0 15px}
.tt-reihe.tt-ich{justify-content:flex-end}
.tt-av{width:40px;height:40px;flex:0 0 40px;align-self:flex-end;
  filter:drop-shadow(0 2px 4px rgba(21,41,61,.18))}
.tt-blase{max-width:84%;padding:13px 16px;border-radius:var(--tt-r-mittel);
  background:var(--tt-weiss);border:1px solid rgba(44,80,120,.1);
  border-bottom-left-radius:6px;word-wrap:break-word;
  box-shadow:0 1px 1px rgba(21,41,61,.04), 0 3px 10px rgba(21,41,61,.08)}
.tt-ich .tt-blase{background:linear-gradient(170deg,var(--tt-blau-hell),var(--tt-blau) 70%);
  color:#fff;border-color:transparent;border-bottom-left-radius:var(--tt-r-mittel);
  border-bottom-right-radius:6px;
  box-shadow:0 1px 0 rgba(255,255,255,.2) inset, 0 3px 12px rgba(44,80,120,.3)}

.tt-hinweis{background:linear-gradient(180deg,#EAF2F9,#E2ECF6);
  border-left:4px solid var(--tt-blau);padding:11px 14px;border-radius:0 var(--tt-r-klein) var(--tt-r-klein) 0;
  font-size:15px;margin:0 0 15px 50px;color:#2B4863;
  box-shadow:0 1px 4px rgba(21,41,61,.07)}

/* Auswahlknoepfe */
.tt-knoepfe{display:flex;flex-direction:column;gap:10px;margin:0 0 17px 50px}
.tt-wahl{display:block;width:100%;text-align:left;
  background:linear-gradient(180deg,#fff,#F4F8FC);
  border:1.5px solid var(--tt-linie);color:var(--tt-text);
  border-radius:var(--tt-r-klein);padding:14px 16px;font-size:17px;font-weight:600;
  cursor:pointer;min-height:54px;
  box-shadow:0 1px 0 rgba(255,255,255,.9) inset, 0 2px 6px rgba(21,41,61,.09);
  transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease}
.tt-wahl:hover{border-color:var(--tt-blau);transform:translateY(-1px);
  background:linear-gradient(180deg,#fff,#EAF2F9);
  box-shadow:0 1px 0 rgba(255,255,255,.9) inset, 0 5px 14px rgba(44,80,120,.2)}
.tt-wahl:active{transform:translateY(1px);box-shadow:0 1px 3px rgba(21,41,61,.14) inset}
.tt-wahl:focus-visible{outline:4px solid var(--tt-signal);outline-offset:2px}
.tt-wahl.tt-zurueck{background:transparent;border-style:dashed;color:var(--tt-text-leise);
  font-weight:500;box-shadow:none}
.tt-wahl.tt-zurueck:hover{background:#E8EFF6;border-style:solid;color:var(--tt-text)}

/* Fortschritt */
.tt-fortschritt{margin:0 0 14px 50px;font-size:13.5px;color:var(--tt-text-leise);font-weight:650}
.tt-fortschritt-bar{height:9px;background:#DCE6F0;border-radius:99px;margin-top:6px;overflow:hidden;
  box-shadow:0 1px 2px rgba(21,41,61,.12) inset}
.tt-fortschritt-bar i{display:block;height:100%;border-radius:99px;transition:width .3s ease;
  background:linear-gradient(90deg,var(--tt-signal),#F2A94E)}

/* Teilekarte */
.tt-teil{background:var(--tt-weiss);border:1px solid rgba(44,80,120,.12);
  border-radius:var(--tt-r-mittel);padding:15px;margin:0 0 12px 50px;
  box-shadow:0 1px 2px rgba(21,41,61,.05), 0 4px 14px rgba(21,41,61,.09);
  transition:transform .14s ease, box-shadow .14s ease}
.tt-teil:hover{transform:translateY(-2px);
  box-shadow:0 2px 4px rgba(21,41,61,.07), 0 10px 26px rgba(21,41,61,.14)}
.tt-teil-titel{font-size:17.5px;font-weight:700;margin:0 0 5px;color:var(--tt-text);line-height:1.3}
.tt-teil-info{font-size:14.5px;color:var(--tt-text-leise);margin:0 0 11px}
.tt-teil-preis{font-size:25px;font-weight:800;color:var(--tt-blau-tief);letter-spacing:-.5px}
.tt-teil-zeile{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}
.tt-marke{display:inline-block;font-size:13px;font-weight:700;padding:5px 11px;border-radius:99px;
  white-space:nowrap;box-shadow:0 1px 2px rgba(21,41,61,.1)}
.tt-lager{background:var(--tt-gruen-feld);color:var(--tt-gruen)}
.tt-leer{background:var(--tt-rot-feld);color:var(--tt-rot)}
.tt-ebaymarke{background:#FDEEDA;color:#8A4708}
.tt-ebay{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:13px;
  background:linear-gradient(180deg,#F09A3E,var(--tt-signal) 55%,var(--tt-signal-tief));
  color:#2B1703;border:0;border-radius:var(--tt-r-klein);padding:14px;font-size:17px;font-weight:800;
  text-decoration:none;min-height:54px;
  box-shadow:0 1px 0 rgba(255,255,255,.4) inset, 0 3px 10px rgba(197,109,22,.4);
  transition:transform .12s ease, box-shadow .12s ease}
.tt-ebay:hover{transform:translateY(-1px);
  box-shadow:0 1px 0 rgba(255,255,255,.4) inset, 0 7px 18px rgba(197,109,22,.5)}
.tt-ebay:active{transform:translateY(1px)}
.tt-ebay:focus-visible{outline:4px solid var(--tt-blau-tief);outline-offset:2px}
.tt-nummern{font-size:12.5px;color:#60798F;margin-top:9px;
  font-family:ui-monospace,Menlo,Consolas,monospace;word-break:break-all;
  background:#F4F8FC;border-radius:8px;padding:6px 9px}

/* Tabelle */
.tt-tabelle{margin:0 0 15px 50px;overflow-x:auto;border-radius:var(--tt-r-klein);
  box-shadow:0 2px 8px rgba(21,41,61,.1)}
.tt-tabelle table{border-collapse:collapse;font-size:14.5px;background:#fff;min-width:100%}
.tt-tabelle th,.tt-tabelle td{border-bottom:1px solid #E4EBF2;padding:9px 12px;text-align:left;white-space:nowrap}
.tt-tabelle th{background:linear-gradient(180deg,#EDF3F9,#E3ECF4);font-weight:700;color:var(--tt-blau-tief)}
.tt-tabelle tr:last-child td{border-bottom:0}

/* Fussbereich */
.tt-fuss{flex:0 0 auto;background:var(--tt-weiss);padding:13px;
  box-shadow:0 -1px 0 rgba(44,80,120,.1), 0 -6px 18px rgba(21,41,61,.06)}
.tt-eingabe-zeile{display:flex;gap:10px;align-items:flex-end}
.tt-feld{flex:1;min-width:0;font:inherit;font-size:17px;padding:13px 15px;
  border:1.5px solid var(--tt-linie);border-radius:var(--tt-r-klein);resize:none;
  min-height:54px;max-height:120px;color:var(--tt-text);background:#FAFCFE;
  box-shadow:0 1px 3px rgba(21,41,61,.07) inset;transition:border-color .12s ease, box-shadow .12s ease}
.tt-feld:focus{outline:none;border-color:var(--tt-blau);
  box-shadow:0 1px 3px rgba(21,41,61,.07) inset, 0 0 0 4px rgba(53,117,168,.18)}
.tt-send{background:linear-gradient(180deg,#4284BB,var(--tt-blau) 50%,#2E6796);
  color:#fff;border:0;border-radius:var(--tt-r-klein);padding:0 20px;height:54px;
  font-size:17px;font-weight:700;cursor:pointer;flex:0 0 auto;
  box-shadow:0 1px 0 rgba(255,255,255,.26) inset, 0 3px 9px rgba(44,80,120,.35);
  transition:transform .12s ease, box-shadow .12s ease}
.tt-send:hover{transform:translateY(-1px);
  box-shadow:0 1px 0 rgba(255,255,255,.26) inset, 0 6px 16px rgba(44,80,120,.42)}
.tt-send:active{transform:translateY(1px)}
.tt-send:focus-visible{outline:4px solid var(--tt-signal);outline-offset:2px}
.tt-send[disabled]{opacity:.5;cursor:default;transform:none}
.tt-fussleiste{display:flex;align-items:center;justify-content:space-between;gap:10px;
  margin-top:10px;font-size:12.5px;color:var(--tt-text-leise)}
.tt-schloss{background:none;border:0;color:var(--tt-text-leise);cursor:pointer;font-size:12.5px;
  text-decoration:underline;padding:6px;min-height:34px;border-radius:7px}
.tt-schloss:hover{color:var(--tt-blau-tief);background:#EEF4FA}

/* Anmeldung */
.tt-adminform{display:none;gap:10px;flex-direction:column}
.tt-adminform.tt-an{display:flex}
.tt-adminform label{font-size:15px;font-weight:700;color:var(--tt-text)}
.tt-adminhinweis{font-size:12.5px;color:var(--tt-text-leise)}
.tt-adminfehler{color:var(--tt-rot);font-size:15px;font-weight:650;display:none;
  background:var(--tt-rot-feld);padding:9px 12px;border-radius:9px}
.tt-adminfehler.tt-an{display:block}
.tt-adminzeile{display:flex;gap:10px}

/* Schraubi tippt */
.tt-tippt{display:flex;gap:6px;padding:15px 17px;align-items:center}
.tt-tippt i{width:10px;height:10px;background:var(--tt-blau-hell);border-radius:50%;animation:tt-h 1.3s infinite}
.tt-tippt i:nth-child(2){animation-delay:.18s}.tt-tippt i:nth-child(3){animation-delay:.36s}
@keyframes tt-h{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-7px);opacity:1}}

.tt-nurlesbar{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}

@media (max-width:480px){
  .tt-wrap{bottom:12px;right:12px;left:12px}
  .tt-wrap.tt-links{left:12px}
  .tt-fenster{width:100%;height:min(620px,calc(100vh - 90px))}
  .tt-knopf{width:100%;justify-content:center}
  .tt-knoepfe,.tt-teil,.tt-hinweis,.tt-fortschritt,.tt-tabelle{margin-left:0}
}
@media (prefers-reduced-motion:reduce){
  .tt-tippt i{animation:none}.tt-lauf{scroll-behavior:auto}
  .tt-fortschritt-bar i{transition:none}
  .tt-knopf,.tt-wahl,.tt-teil,.tt-send,.tt-ebay{transition:none}
  .tt-knopf:hover,.tt-wahl:hover,.tt-teil:hover,.tt-send:hover,.tt-ebay:hover{transform:none}
}
@media (prefers-contrast:more){
  .tt-blase,.tt-teil,.tt-wahl{border-color:var(--tt-blau-tief);border-width:2px}
  .tt-teil-info,.tt-fussleiste{color:#2B4863}
}
`;

  // Das Logo von Teile Thuns, direkt eingebettet: so laedt das
  // Widget kein zusaetzliches Bild nach und bleibt eine einzige Datei.
  var LOGO = "data:image/png;base64,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";
  var ZEICHEN = "data:image/png;base64,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";

  // ---------------------------------------------------------------
  // Schraubi: ein freundlicher Ringschluessel. Als SVG direkt im Code,
  // damit kein Bild nachgeladen werden muss und das Maskottchen bei
  // jeder Groesse scharf bleibt.
  // ---------------------------------------------------------------
  function schraubiSVG(groesse, blinkt) {
    var id = "tt" + Math.random().toString(36).slice(2, 8);
    return (
      '<svg viewBox="0 0 64 64" width="' + groesse + '" height="' + groesse + '" ' +
      'role="img" aria-label="Schraubi, der Teile-Helfer" focusable="false">' +
      '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="#EDF3F9"/><stop offset="1" stop-color="#A9BFD4"/>' +
      '</linearGradient></defs>' +
      // Griff des Schluessels
      '<path d="M26 34h12v22a6 6 0 0 1-12 0z" fill="url(#' + id + ')" stroke="#2C5078" stroke-width="2.5"/>' +
      '<path d="M29 40h6M29 46h6" stroke="#7FA0BC" stroke-width="2" stroke-linecap="round"/>' +
      // Ringkopf = Gesicht
      '<circle cx="32" cy="22" r="18" fill="url(#' + id + ')" stroke="#2C5078" stroke-width="2.5"/>' +
      '<circle cx="32" cy="22" r="8.5" fill="#F7FAFD" stroke="#2C5078" stroke-width="2"/>' +
      // Sechskant-Innenkontur: macht aus dem Ring einen Ringschluessel
      '<path d="M32 15.2l5 3v5.6l-5 3-5-3v-5.6z" fill="#D4E2EE" stroke="#6E8CA8" stroke-width="1.3"/>' +
      // Augen
      '<circle cx="24.5" cy="18.5" r="2.5" fill="#2C5078"/>' +
      '<circle cx="39.5" cy="18.5" r="2.5" fill="#2C5078"/>' +
      '<circle cx="25.3" cy="17.7" r=".9" fill="#fff"/>' +
      '<circle cx="40.3" cy="17.7" r=".9" fill="#fff"/>' +
      (blinkt
        ? '<path d="M22 18.5h5M37 18.5h5" stroke="#2C5078" stroke-width="2.5" stroke-linecap="round"/>'
        : "") +
      // Laecheln
      '<path d="M25 28.5q7 5 14 0" stroke="#2C5078" stroke-width="2.3" fill="none" stroke-linecap="round"/>' +
      // Signalfarbe als Mütze - greift die Shopfarbe auf
      '<path d="M15.5 13.5q16.5-13 33 0z" fill="#E8872B" stroke="#2C5078" stroke-width="2.2"/>' +
      "</svg>"
    );
  }

  // ---------------------------------------------------------------
  // Hilfsfunktionen
  // ---------------------------------------------------------------
  function el(tag, klasse, text) {
    var n = document.createElement(tag);
    if (klasse) n.className = klasse;
    if (text != null) n.textContent = text;
    return n;
  }

  function euro(zahl) {
    try {
      return new Intl.NumberFormat("de-DE", {
        style: "currency", currency: "EUR"
      }).format(zahl);
    } catch (e) {
      return zahl.toFixed(2).replace(".", ",") + " Euro";
    }
  }

  var sitzung = (function () {
    // Nur eine Zufallskennung fuer diesen Besuch. Kein Name, keine
    // Kennung ueber Besuche hinweg, kein Cookie.
    try {
      var vorhanden = sessionStorage.getItem("tt-sitzung");
      if (vorhanden) return vorhanden;
      var neu = "s" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sessionStorage.setItem("tt-sitzung", neu);
      return neu;
    } catch (e) {
      return "s" + Math.random().toString(36).slice(2);
    }
  })();

  // ---------------------------------------------------------------
  // Aufbau
  // ---------------------------------------------------------------
  var stil = el("style");
  stil.textContent = CSS;
  document.head.appendChild(stil);

  var wrap = el("div", "tt-wrap tt-" + (POSITION === "links" ? "links" : "rechts"));

  var starter = el("button", "tt-knopf");
  starter.type = "button";
  starter.setAttribute("aria-label", T.oeffnen);
  starter.innerHTML = '<img src="' + ZEICHEN + '" alt="" aria-hidden="true">' +
    "<span>Teile finden</span>";

  var fenster = el("div", "tt-fenster");
  fenster.setAttribute("role", "dialog");
  fenster.setAttribute("aria-label", "Teile-Hilfe von Schraubi");
  fenster.setAttribute("aria-modal", "false");

  // Kopf
  var kopf = el("div", "tt-kopf");
  kopf.innerHTML =
    '<img class="tt-kopf-zeichen" src="' + ZEICHEN + '" alt="">' +
    '<div class="tt-kopf-text">' +
    '<div class="tt-kopf-marke">Teile<span>Thuns</span></div>' +
    '<div class="tt-kopf-rolle">' + T.untertitel + "</div></div>";
  var zu = el("button", "tt-zu", "×");
  zu.type = "button";
  zu.setAttribute("aria-label", T.schliessen);
  kopf.appendChild(zu);

  // Offenlegung nach EU-KI-Verordnung: dauerhaft sichtbar, nicht nur
  // in der Begruessung, die man wegscrollt.
  var kibanner = el("div", "tt-kibanner");
  kibanner.innerHTML = "<span class='tt-kiz' aria-hidden='true'>i</span><span><b>Hinweis:</b> " +
    T.kiHinweis + ". <a href='#' class='tt-kilink'>Was heißt das?</a></span>";

  var adminbanner = el("div", "tt-adminbanner");
  var adminbannerText = el("span", null, "Betriebsleitung angemeldet \u2013 getrennter Verlauf");
  var adminAb = el("button", null, T.adminAb);
  adminAb.type = "button";
  adminbanner.appendChild(adminbannerText);
  adminbanner.appendChild(adminAb);

  var lauf = el("div", "tt-lauf");
  lauf.setAttribute("role", "log");
  lauf.setAttribute("aria-live", "polite");
  lauf.setAttribute("aria-relevant", "additions");
  lauf.setAttribute("tabindex", "0");

  // Fuss: Eingabe oder Anmeldeformular
  var fuss = el("div", "tt-fuss");
  var eingabeZeile = el("div", "tt-eingabe-zeile");
  var feld = el("textarea", "tt-feld");
  feld.rows = 1;
  feld.placeholder = T.eingabe;
  feld.setAttribute("aria-label", T.eingabe);
  feld.maxLength = 500;
  var senden = el("button", "tt-send", T.senden);
  senden.type = "button";
  eingabeZeile.appendChild(feld);
  eingabeZeile.appendChild(senden);

  var fussleiste = el("div", "tt-fussleiste");
  var fussText = el("span", null, "Preise aus dem Lager, keine erfundenen Angaben.");
  var schloss = el("button", "tt-schloss", T.adminAn);
  schloss.type = "button";
  schloss.setAttribute("aria-label", T.adminAn);
  fussleiste.appendChild(fussText);
  fussleiste.appendChild(schloss);

  // Anmeldeformular. Eigenes Passwortfeld, eigener Endpunkt -
  // das Passwort wird NIE als Chatnachricht verschickt und steht
  // dadurch nie im Verlauf.
  var adminform = el("form", "tt-adminform");
  var adminLabel = el("label", null, T.adminPasswort);
  adminLabel.setAttribute("for", "tt-pw");
  var adminPw = el("input");
  adminPw.type = "password";
  adminPw.id = "tt-pw";
  adminPw.className = "tt-feld";
  adminPw.autocomplete = "current-password";
  adminPw.setAttribute("aria-describedby", "tt-pw-hinweis");
  var adminFehler = el("div", "tt-adminfehler");
  adminFehler.setAttribute("role", "alert");
  var adminHinweis = el("div", "tt-adminhinweis",
    "Die Eingabe erscheint nicht im Gesprächsverlauf und wird nicht protokolliert.");
  adminHinweis.id = "tt-pw-hinweis";
  var adminZeile = el("div", "tt-adminzeile");
  var adminOk = el("button", "tt-send", T.adminAnmelden);
  adminOk.type = "submit";
  var adminAbbruch = el("button", "tt-wahl tt-zurueck", T.adminAbbruch);
  adminAbbruch.type = "button";
  adminZeile.appendChild(adminOk);
  adminZeile.appendChild(adminAbbruch);
  adminform.appendChild(adminLabel);
  adminform.appendChild(adminPw);
  adminform.appendChild(adminFehler);
  adminform.appendChild(adminHinweis);
  adminform.appendChild(adminZeile);

  fuss.appendChild(eingabeZeile);
  fuss.appendChild(fussleiste);
  fuss.appendChild(adminform);

  fenster.appendChild(kopf);
  fenster.appendChild(kibanner);
  fenster.appendChild(adminbanner);
  fenster.appendChild(lauf);
  fenster.appendChild(fuss);

  wrap.appendChild(fenster);
  wrap.appendChild(starter);

  function einbauen() {
    document.body.appendChild(wrap);
    if (START_OFFEN) oeffnen();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", einbauen);
  } else {
    einbauen();
  }

  // ---------------------------------------------------------------
  // Zustand
  // ---------------------------------------------------------------
  var zustand = {
    offen: false,
    begruesst: false,
    laeuft: false,
    adminToken: null,
    adminAblauf: 0,
    interviewStand: {},
    verlaufKunde: [],   // getrennt gehaltene Verlaeufe
    verlaufAdmin: []
  };

  // ---------------------------------------------------------------
  // Darstellung
  // ---------------------------------------------------------------
  function istAdmin() {
    return !!zustand.adminToken && Date.now() < zustand.adminAblauf;
  }

  function blaseBot(text) {
    var reihe = el("div", "tt-reihe");
    var av = el("div", "tt-av");
    av.innerHTML = schraubiSVG(38, false);
    reihe.appendChild(av);
    reihe.appendChild(el("div", "tt-blase", text));
    lauf.appendChild(reihe);
    return reihe;
  }

  function blaseIch(text) {
    var reihe = el("div", "tt-reihe tt-ich");
    reihe.appendChild(el("div", "tt-blase", text));
    lauf.appendChild(reihe);
  }

  function tipptAn() {
    var reihe = el("div", "tt-reihe");
    reihe.id = "tt-tippt";
    var av = el("div", "tt-av");
    av.innerHTML = schraubiSVG(38, true);
    var blase = el("div", "tt-blase tt-tippt");
    blase.innerHTML = "<i></i><i></i><i></i>";
    blase.appendChild(el("span", "tt-nurlesbar", T.laedt));
    reihe.appendChild(av);
    reihe.appendChild(blase);
    lauf.appendChild(reihe);
    runter();
  }

  function tipptAus() {
    var n = document.getElementById("tt-tippt");
    if (n) n.remove();
  }

  function runter() {
    lauf.scrollTop = lauf.scrollHeight;
  }

  function teilKarte(t) {
    var karte = el("div", "tt-teil");
    karte.appendChild(el("div", "tt-teil-titel", t.title));

    var infoTeile = [];
    if (t.year_from && t.year_to) infoTeile.push("Baujahr " + t.year_from + "-" + t.year_to);
    if (t.side) infoTeile.push("Lage: " + t.side);
    if (t.condition) infoTeile.push(t.condition);
    karte.appendChild(el("div", "tt-teil-info", infoTeile.join(" · ")));

    var zeile = el("div", "tt-teil-zeile");
    zeile.appendChild(el("div", "tt-teil-preis", euro(t.preis_euro)));
    var marke = el("span", "tt-marke " + (t.on_ebay ? "tt-ebaymarke" : (t.stock > 0 ? "tt-lager" : "tt-leer")));
    marke.textContent = t.on_ebay
      ? "über eBay"
      : (t.stock > 0 ? "auf Lager" : "zurzeit nicht da");
    zeile.appendChild(marke);
    karte.appendChild(zeile);

    if (t.oem_numbers && t.oem_numbers.length) {
      karte.appendChild(el("div", "tt-nummern", "Vergleichsnummern: " + t.oem_numbers.join(", ")));
    }

    if (t.on_ebay && t.ebay_url) {
      var a = el("a", "tt-ebay");
      a.href = t.ebay_url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.innerHTML = "<span aria-hidden='true'>→</span><span>Bei eBay ansehen und bestellen</span>";
      a.setAttribute("aria-label", "Teil " + t.title + " bei eBay ansehen, öffnet neues Fenster");
      karte.appendChild(a);
    }
    lauf.appendChild(karte);
  }

  function tabelleZeigen(zeilen) {
    if (!zeilen || !zeilen.length) return;
    var spalten = Object.keys(zeilen[0]).filter(function (k) {
      return k !== "text" && k !== "hinweis";
    });
    if (!spalten.length) return;
    var huelle = el("div", "tt-tabelle");
    var tab = el("table");
    var kopfz = el("tr");
    spalten.forEach(function (s) {
      kopfz.appendChild(el("th", null, s.replace(/_/g, " ")));
    });
    tab.appendChild(kopfz);
    zeilen.slice(0, 25).forEach(function (z) {
      var tr = el("tr");
      spalten.forEach(function (s) {
        var w = z[s];
        tr.appendChild(el("td", null, w == null ? "-" : String(w)));
      });
      tab.appendChild(tr);
    });
    huelle.appendChild(tab);
    lauf.appendChild(huelle);
  }

  function knoepfeZeigen(knoepfe) {
    if (!knoepfe || !knoepfe.length) return;
    var box = el("div", "tt-knoepfe");
    knoepfe.forEach(function (k) {
      var b = el("button", "tt-wahl" +
        (/^(interview_zurueck|interview_ende)/.test(k.aktion) ? " tt-zurueck" : ""), k.text);
      b.type = "button";
      b.addEventListener("click", function () {
        box.remove();
        aktion(k);
      });
      box.appendChild(b);
    });
    lauf.appendChild(box);
  }

  function fortschrittZeigen(iv) {
    if (!iv || !iv.fortschritt) return;
    var box = el("div", "tt-fortschritt");
    box.appendChild(el("div", null, "Schritt " + iv.fortschritt + " von " + iv.schritte_gesamt));
    var bar = el("div", "tt-fortschritt-bar");
    var i = el("i");
    i.style.width = Math.round((iv.fortschritt / iv.schritte_gesamt) * 100) + "%";
    bar.appendChild(i);
    box.appendChild(bar);
    lauf.appendChild(box);
  }

  function antwortZeigen(d) {
    (d.blasen || []).forEach(function (b) { blaseBot(b); });
    if (d.interview) {
      zustand.interviewStand = d.interview.stand || {};
      fortschrittZeigen(d.interview);
    }
    (d.teile || []).forEach(teilKarte);
    if (d.tabelle && d.tabelle.length && d.art !== "versand") tabelleZeigen(d.tabelle);
    if (d.hinweis) lauf.appendChild(el("div", "tt-hinweis", d.hinweis));
    knoepfeZeigen(d.knoepfe);
    runter();
  }

  // ---------------------------------------------------------------
  // Netzzugriff
  // ---------------------------------------------------------------
  function holen(pfad, daten) {
    var kopfzeilen = { "Content-Type": "application/json" };
    if (istAdmin()) kopfzeilen["X-Admin-Token"] = zustand.adminToken;
    return fetch(API + pfad, {
      method: "POST",
      headers: kopfzeilen,
      body: JSON.stringify(daten)
    }).then(function (r) {
      if (r.status === 429) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          throw new Error(j.detail || "Bitte einen Moment warten.");
        });
      }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function senden_(text) {
    if (zustand.laeuft) return;
    zustand.laeuft = true;
    senden.disabled = true;
    tipptAn();
    holen("/api/chat", { nachricht: text, sitzung: sitzung })
      .then(function (d) {
        tipptAus();
        antwortZeigen(d);
      })
      .catch(function (e) {
        tipptAus();
        blaseBot(e && e.message && e.message.indexOf("HTTP") !== 0 ? e.message : T.fehler);
        knoepfeZeigen([{ text: "Noch einmal versuchen", aktion: "frage:" + text }]);
        runter();
      })
      .finally(function () {
        zustand.laeuft = false;
        senden.disabled = false;
      });
  }

  function interviewSchritt(stand) {
    if (zustand.laeuft) return;
    zustand.laeuft = true;
    tipptAn();
    holen("/api/interview", { stand: stand, sitzung: sitzung })
      .then(function (d) {
        tipptAus();
        antwortZeigen(d);
      })
      .catch(function () {
        tipptAus();
        blaseBot(T.fehler);
        runter();
      })
      .finally(function () { zustand.laeuft = false; });
  }

  // ---------------------------------------------------------------
  // Aktionen der Knoepfe
  // ---------------------------------------------------------------
  function aktion(k) {
    var a = k.aktion || "";
    if (a === "interview_start") {
      zustand.interviewStand = {};
      blaseIch(k.text);
      interviewSchritt({});
      return;
    }
    if (a === "interview_ende") {
      blaseIch(k.text);
      zustand.interviewStand = {};
      blaseBot("In Ordnung. Sie können mir auch einfach schreiben, was Sie suchen.");
      runter();
      return;
    }
    if (a.indexOf("interview:") === 0) {
      var stuecke = a.split(":");
      var schritt = stuecke[1];
      var wert = stuecke.slice(2).join(":");
      blaseIch(wert);
      var stand = Object.assign({}, zustand.interviewStand);
      if (schritt === "baujahr") {
        // "2003-2007" -> mittleres Jahr, das trifft die Spanne sicher.
        var jahre = wert.split("-");
        var von = parseInt(jahre[0], 10);
        var bis = parseInt(jahre[1] || jahre[0], 10);
        stand.jahr = Math.floor((von + bis) / 2);
      } else {
        stand[schritt] = wert.replace(/\s+\(\d+\)$/, "");
      }
      zustand.interviewStand = stand;
      interviewSchritt(stand);
      return;
    }
    if (a.indexOf("interview_zurueck:") === 0) {
      var ziel = a.split(":")[1];
      var reihenfolge = ["marke", "modell", "jahr", "kategorie", "bauteil"];
      var abbildung = { marke: "marke", modell: "modell", baujahr: "jahr",
        kategorie: "kategorie", bauteil: "bauteil" };
      var ab = reihenfolge.indexOf(abbildung[ziel] || ziel);
      var neu = {};
      reihenfolge.forEach(function (f, i) {
        if (i < ab && zustand.interviewStand[f] != null) neu[f] = zustand.interviewStand[f];
      });
      zustand.interviewStand = neu;
      interviewSchritt(neu);
      return;
    }
    if (a.indexOf("frage:") === 0) {
      var frage = a.slice(6);
      blaseIch(k.text);
      senden_(frage);
      return;
    }
    if (a === "kontakt") {
      blaseIch(k.text);
      senden_("Ich moechte mit einem Mitarbeiter sprechen");
      return;
    }
    if (a === "laenderliste") {
      blaseIch(k.text);
      senden_("Wohin liefern Sie?");
      return;
    }
    if (a === "hinweis_nummer") {
      blaseIch(k.text);
      senden_("Ich habe eine Teilenummer");
      feld.focus();
      return;
    }
    blaseIch(k.text);
    senden_(k.text);
  }

  // ---------------------------------------------------------------
  // Fenster oeffnen und schliessen
  // ---------------------------------------------------------------
  function oeffnen() {
    zustand.offen = true;
    fenster.classList.add("tt-offen");
    starter.style.display = "none";
    if (!zustand.begruesst) {
      zustand.begruesst = true;
      tipptAn();
      fetch(API + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nachricht: "", sitzung: sitzung })
      })
        .then(function (r) { return r.json(); })
        .then(function (d) { tipptAus(); antwortZeigen(d); })
        .catch(function () {
          tipptAus();
          blaseBot("Hallo! Ich bin Schraubi, der automatische Helfer. " +
            "Gerade erreiche ich den Lagerbestand nicht \u2013 bitte versuchen Sie es " +
            "in einem Moment noch einmal.");
          runter();
        });
    }
    setTimeout(function () { feld.focus(); }, 60);
  }

  function schliessen() {
    zustand.offen = false;
    fenster.classList.remove("tt-offen");
    starter.style.display = "flex";
    starter.focus();
  }

  starter.addEventListener("click", oeffnen);
  zu.addEventListener("click", schliessen);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && zustand.offen) schliessen();
  });

  senden.addEventListener("click", function () {
    var text = feld.value.trim();
    if (!text) { feld.focus(); return; }
    blaseIch(text);
    feld.value = "";
    feld.style.height = "auto";
    senden_(text);
  });

  feld.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      senden.click();
    }
  });

  feld.addEventListener("input", function () {
    feld.style.height = "auto";
    feld.style.height = Math.min(feld.scrollHeight, 120) + "px";
  });

  kibanner.addEventListener("click", function (e) {
    var ziel = e.target;
    if (ziel && ziel.className === "tt-kilink") {
      e.preventDefault();
      if (!zustand.offen) oeffnen();
      fetch(API + "/api/ki-hinweis")
        .then(function (r) { return r.json(); })
        .then(function (d) {
          blaseBot("Ich bin ein automatischer Helfer, kein Mensch.");
          blaseBot(d.funktionsweise);
          blaseBot(d.daten);
          if (d.grenzen) lauf.appendChild(el("div", "tt-hinweis", d.grenzen));
          knoepfeZeigen([{ text: "Verstanden, weiter", aktion: "interview_start" }]);
          runter();
        })
        .catch(function () { blaseBot(T.fehler); });
    }
  });

  // ---------------------------------------------------------------
  // Umschalten auf Betriebsleitung
  // ---------------------------------------------------------------
  function adminFormZeigen(an) {
    adminform.classList.toggle("tt-an", an);
    eingabeZeile.style.display = an ? "none" : "flex";
    fussleiste.style.display = an ? "none" : "flex";
    adminFehler.classList.remove("tt-an");
    adminPw.value = "";
    if (an) setTimeout(function () { adminPw.focus(); }, 50);
  }

  schloss.addEventListener("click", function () {
    if (!zustand.offen) oeffnen();
    adminFormZeigen(true);
  });

  adminAbbruch.addEventListener("click", function () { adminFormZeigen(false); });

  adminform.addEventListener("submit", function (e) {
    e.preventDefault();
    var pw = adminPw.value;
    if (!pw) return;
    adminOk.disabled = true;
    // Eigener Endpunkt, eigenes Feld: das Passwort geht nicht durch
    // /api/chat und erscheint daher nirgends im Verlauf.
    fetch(API + "/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passwort: pw })
    })
      .then(function (r) {
        return r.json().then(function (j) {
          if (!r.ok) throw new Error(j.detail || "Anmeldung nicht möglich");
          return j;
        });
      })
      .then(function (j) {
        adminPw.value = "";
        zustand.adminToken = j.token;
        zustand.adminAblauf = Date.now() + (j.gueltig_sekunden * 1000) - 2000;
        adminFormZeigen(false);
        // Verlauf trennen: der Kundenverlauf wird beiseite gelegt und
        // beim Abmelden wieder hergestellt.
        zustand.verlaufKunde = Array.prototype.slice.call(lauf.childNodes);
        lauf.innerHTML = "";
        lauf.classList.add("tt-adminmodus");
        adminbanner.classList.add("tt-an");
        blaseBot(j.hinweis);
        blaseBot("Fragen Sie zum Beispiel: Umsatz heute. Bestseller im Monat. " +
          "Welche Suchen hatten keine Treffer? Wie ist der Lagerbestand?");
        knoepfeZeigen([
          { text: "Umsatz heute", aktion: "frage:Umsatz heute" },
          { text: "Bestseller im Monat", aktion: "frage:Welche Teile sind die Bestseller im Monat?" },
          { text: "Suchen ohne Treffer", aktion: "frage:Welche Suchen hatten keine Treffer?" },
          { text: "Lagerbestand", aktion: "frage:Wie ist der Lagerbestand?" }
        ]);
        // Automatisch abmelden, wenn die Sitzung ablaeuft.
        setTimeout(function () {
          if (istAdmin()) return;
          abmelden(true);
        }, j.gueltig_sekunden * 1000);
        runter();
      })
      .catch(function (err) {
        adminFehler.textContent = err.message || "Anmeldung nicht möglich";
        adminFehler.classList.add("tt-an");
        adminPw.value = "";
        adminPw.focus();
      })
      .finally(function () { adminOk.disabled = false; });
  });

  function abmelden(abgelaufen) {
    var token = zustand.adminToken;
    zustand.adminToken = null;
    zustand.adminAblauf = 0;
    if (token) {
      fetch(API + "/api/admin/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Token": token },
        body: "{}"
      }).catch(function () { /* Abmeldung ist auch lokal wirksam */ });
    }
    lauf.innerHTML = "";
    lauf.classList.remove("tt-adminmodus");
    adminbanner.classList.remove("tt-an");
    // Kundenverlauf zurueckholen.
    zustand.verlaufKunde.forEach(function (n) { lauf.appendChild(n); });
    if (abgelaufen) {
      blaseBot("Die Anmeldung der Betriebsleitung ist abgelaufen. Der Verlauf wurde verworfen.");
    }
    runter();
  }

  adminAb.addEventListener("click", function () { abmelden(false); });

  // Oeffentliche Schnittstelle, falls der Betreiber den Bot aus einem
  // eigenen Knopf heraus oeffnen will: window.TeileThuns.oeffnen()
  window.TeileThuns = {
    oeffnen: oeffnen,
    schliessen: schliessen,
    fragen: function (text) {
      oeffnen();
      blaseIch(text);
      senden_(text);
    }
  };
})();
