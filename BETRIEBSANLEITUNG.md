# Betriebsanleitung: Schraubi, Ihr Auskunftshelfer

Diese Anleitung ist für Sie als Shop-Betreiber geschrieben, nicht für
Programmierer. Sie brauchen keine Vorkenntnisse. Wo ein Fachbegriff
unvermeidlich ist, steht die Erklärung daneben.

**Bewahren Sie diese Anleitung griffbereit auf.** Kapitel 6 brauchen Sie
im Ernstfall schnell.

---

## Inhalt

1. [Was der Helfer tut – und was nicht](#1-was-der-helfer-tut--und-was-nicht)
2. [Einbau in Ihre Webseite](#2-einbau-in-ihre-webseite)
3. [Der tägliche Lagerabgleich](#3-der-tägliche-lagerabgleich)
4. [Teile, die über eBay laufen](#4-teile-die-über-ebay-laufen)
5. [Ihre eigene Anmeldung: Zahlen abfragen](#5-ihre-eigene-anmeldung-zahlen-abfragen)
6. [Notfall: was tun, wenn etwas schiefgeht](#6-notfall-was-tun-wenn-etwas-schiefgeht)
7. [Ihre rechtlichen Pflichten](#7-ihre-rechtlichen-pflichten)
8. [Was Sie aufbewahren müssen](#8-was-sie-aufbewahren-müssen)
9. [Häufige Fragen](#9-häufige-fragen)

---

## 1. Was der Helfer tut – und was nicht

### Er tut dies

| Aufgabe | Wie |
|---|---|
| Teile finden | Der Kunde beschreibt in eigenen Worten, was er sucht. „Das rote Glas hinten links" findet die Rückleuchte. |
| Durchfragen | Wer gar nichts weiß, wird Schritt für Schritt durch Marke, Modell, Baujahr und Bauteil geführt – mit Knöpfen, ohne Tippen. |
| Preise und Bestand nennen | Immer aus Ihrer Datenbank. Nie geschätzt. |
| Versand und Lieferzeit | Rechnet ab dem heutigen Tag, mit Wochenende, Feiertagen und Ihrem Bestellschluss. |
| Zu eBay weiterleiten | Liegt ein Teil bei eBay, bekommt der Kunde den direkten Link dorthin. |
| Ihnen Zahlen geben | Nach Anmeldung: Umsatz, Bestseller, Lagerwert, Suchen ohne Treffer. |

### Er tut dies ausdrücklich nicht

- **Er erfindet nichts.** Was nicht in der Datenbank steht, sagt er nicht.
  Er hat kein frei textendes Sprachmodell. Jede Antwort ist eine feste
  Formulierung, in die Werte aus Ihrem Lager eingesetzt werden. Deshalb
  kann er keine Preise, Lieferzeiten oder Teile halluzinieren – der
  häufigste Ärger mit solchen Helfern fällt damit weg.
- **Er gibt keine Einbauanleitungen.** Zu riskant: Ein falscher Rat am
  Fahrwerk kann Menschen gefährden, und Sie würden dafür haften.
- **Er gibt keine Rechtsberatung.** Zu Widerruf und Gewährleistung nennt
  er die allgemeine Rechtslage und verweist für den Einzelfall an Sie.
- **Er verrät Kunden keine Betriebsdaten.** Fragen nach Umsatz, Marge,
  Einkaufspreisen oder Lieferanten werden freundlich abgelehnt. Das ist
  doppelt abgesichert: in der Programmlogik und zusätzlich in der
  Datenbank selbst, die dem Kundenzugang das Leserecht auf die
  Verkaufstabelle entzieht.

---

## 2. Einbau in Ihre Webseite

Sie fügen **eine Zeile** in Ihre Webseite ein, direkt vor dem
schließenden `</body>`-Zeichen:

```html
<script src="https://IHRE-ADRESSE/widget.js" defer></script>
```

`IHRE-ADRESSE` bekommen Sie von Ihrem Entwickler. Mehr ist nicht nötig:
kein weiteres Programm, keine zusätzliche Datei, keine Änderung am
Shopsystem.

**Wenn Sie ein Shopsystem benutzen:** In Shopware, WooCommerce oder
JTL gibt es dafür ein Feld, meist unter *Einstellungen → Darstellung →
Eigener Code* oder *Theme → Footer*. Fügen Sie die Zeile dort ein.

### Was Sie einstellen können

| Zusatz | Wirkung |
|---|---|
| `data-position="links"` | Der Helfer sitzt unten links statt unten rechts. |
| `data-offen="ja"` | Das Fenster ist beim Seitenaufruf schon geöffnet. |

Beispiel:
```html
<script src="https://IHRE-ADRESSE/widget.js" data-position="links" defer></script>
```

### Einen eigenen Knopf einbauen

Wenn Sie an anderer Stelle einen Knopf möchten, der den Helfer öffnet:

```html
<button onclick="TeileThuns.oeffnen()">Teil finden</button>
```

### Prüfen, ob es läuft

Rufen Sie Ihre Seite auf. Unten rechts muss ein dunkler Knopf mit dem
Schraubenschlüssel erscheinen. Klicken Sie ihn an: Es muss eine
Begrüßung kommen, in der steht, dass Schraubi ein Computerprogramm ist.

**Kommt stattdessen „Gerade erreiche ich den Lagerbestand nicht"?**
Dann ist Ihre Webseiten-Adresse nicht freigeschaltet. Geben Sie Ihrem
Entwickler die genaue Adresse Ihrer Seite (mit `https://` und ohne
Schrägstrich am Ende); er trägt sie unter `ALLOWED_ORIGINS` ein.

---

## 3. Der tägliche Lagerabgleich

Damit der Helfer tagesaktuell ist, schickt Ihr Shop ihm einmal täglich
den Lagerbestand. Das läuft automatisch, sobald es einmal eingerichtet
ist. Sie müssen nichts tun – aber Sie sollten wissen, wie Sie es prüfen.

### Welche Angaben gebraucht werden

Pflicht sind: **Artikelnummer, Bezeichnung, Marke, Modell, Warengruppe,
Preis**. Alles Weitere verbessert die Treffer, ist aber freiwillig.

| Spalte | Beispiel | Pflicht |
|---|---|---|
| Artikelnummer | `TT-004711` | ja |
| Bezeichnung | `Rückleuchte links Golf V` | ja |
| Marke | `Volkswagen` | ja |
| Modell | `Golf V` | ja |
| Warengruppe | `Beleuchtung` | ja |
| Preis | `89,00` oder `8900` (Cent) | ja |
| Bauteil | `Rückleuchte` | sehr empfohlen |
| Baujahr von / bis | `2003` / `2008` | empfohlen |
| Seite | `links`, `rechts`, `vorne`, `hinten`, auch `VL` | empfohlen |
| Bestand | `2` | empfohlen |
| Gewicht | `1200` (Gramm) oder `1,2` (kg) | empfohlen |
| Vergleichsnummern | `1K6945095, 1K6-945-095` | empfohlen |
| eBay | `ja` / `nein` | nur bei eBay-Teilen |
| eBay-Link | `https://www.ebay.de/itm/...` | Pflicht, wenn eBay = ja |

Die Spaltennamen dürfen auf Deutsch oder Englisch sein; gängige
Schreibweisen werden erkannt. Als Dateiformat geht **CSV** (auch mit
Semikolon, wie Excel es speichert) oder **JSON**.

### Was passiert, wenn eine Zeile fehlerhaft ist

**Die Lieferung wird nicht verworfen.** Fehlerhafte Zeilen werden
übersprungen und einzeln gemeldet – mit Zeilennummer, Artikelnummer und
Grund. Alle übrigen Teile sind sofort im Bot. Ein Tippfehler in Zeile
4000 legt Ihren Helfer also nicht einen Tag lahm.

### Prüfen, ob der Abgleich gelaufen ist

Melden Sie sich im Chatfenster als Betriebsleitung an (Kapitel 5) und
fragen Sie: **„Wie ist der Lagerbestand?"** Steht dort eine plausible
Zahl, hat der Abgleich funktioniert.

Stimmt die Zahl seit Tagen nicht mehr, melden Sie sich bei Ihrem
Entwickler. Vermutlich läuft die nächtliche Übertragung nicht mehr.

---

## 4. Teile, die über eBay laufen

Setzen Sie in Ihrer Lagerdatei bei einem Teil `eBay = ja` und tragen Sie
den eBay-Link ein. Dann sagt der Helfer dem Kunden:

> „Dieses Teil verkaufen wir über unseren eBay-Marktplatz. Dort bestellen
> Sie genauso sicher – ein Antippen genügt, ich habe den Link gleich mit
> angelegt."

Darunter erscheint ein großer, auffälliger Knopf, der im neuen Fenster
zu Ihrem eBay-Artikel führt.

**Wichtig:** Ohne Link wird das Teil beim Abgleich abgewiesen. Das ist
Absicht – ein eBay-Hinweis ohne Ziel ärgert den Kunden mehr, als wenn
das Teil gar nicht auftaucht.

---

## 5. Ihre eigene Anmeldung: Zahlen abfragen

### So melden Sie sich an

1. Öffnen Sie den Helfer auf Ihrer Webseite wie ein Kunde.
2. Klicken Sie unten rechts im Fenster auf **„Betriebsleitung anmelden"**.
3. Geben Sie Ihr Passwort ein. Die Eingabe erscheint als Punkte.
4. Der Hintergrund wird grünlich, oben erscheint ein Band: *Betriebsleitung
   angemeldet*.

**Ihr Passwort erscheint nirgendwo im Gespräch.** Es läuft über ein
eigenes Feld und einen eigenen Weg zum Server – nicht als Chatnachricht.
Es steht daher weder im Verlauf, noch auf dem Bildschirm, noch in einem
Protokoll.

### Was Sie fragen können

| Frage | Antwort |
|---|---|
| „Umsatz heute" | Umsatz, Anzahl Aufträge, durchschnittlicher Auftragswert |
| „Wie hoch war der Umsatz letzten Monat?" | dasselbe für 30 Tage |
| „Was sind die Bestseller im Monat?" | die zehn meistverkauften Teile |
| „Wie viel läuft über eBay?" | Umsatz je Verkaufsweg mit Prozentanteil |
| „Wie ist der Lagerbestand?" | Teile, Lagerwert, Verteilung auf Warengruppen |
| **„Welche Suchen hatten keine Treffer?"** | **Die wertvollste Auskunft: wonach Kunden gesucht haben, ohne etwas zu finden. Das ist Nachfrage, die Ihr Bestand nicht deckt – eine fertige Einkaufsliste.** |
| „Gab es Fehler heute?" | Anzahl der Gespräche, Fehler, Antwortzeiten |

Zeiträume erkennt er von selbst: *heute, gestern, diese Woche, im Monat,
im Quartal, im Jahr*.

### Abmelden

Klicken Sie oben im grünen Band auf **„Betriebsleitung abmelden"**. Ihr
Zahlen-Verlauf wird verworfen, der normale Kundenverlauf kommt zurück.

**Die Anmeldung endet außerdem automatisch nach 30 Minuten.** Falls Sie
den Rechner im Laden stehen lassen, kann niemand Ihre Zahlen sehen.

### Wenn Sie das Passwort vergessen haben

Es lässt sich nicht wiederherstellen – auch Ihr Entwickler kann es nicht
auslesen, es ist nur verschlüsselt gespeichert. Er kann Ihnen aber in
wenigen Minuten ein neues setzen.

---

## 6. Notfall: was tun, wenn etwas schiefgeht

### 6.1 Der Helfer erscheint gar nicht

1. Laden Sie die Seite neu (Strg + F5, am Mac Cmd + Shift + R).
2. Probieren Sie einen anderen Browser oder Ihr Handy. Erscheint er dort,
   liegt es an Ihrem Browser, nicht am Helfer.
3. Prüfen Sie, ob die `<script>`-Zeile noch in der Webseite steht. Nach
   einem Update des Shopsystems ist sie manchmal verschwunden.
4. Hilft nichts: Entwickler anrufen.

**Solange er fehlt, ist nichts kaputt.** Ihr Shop funktioniert normal
weiter. Es gibt nur keine Teile-Hilfe.

### 6.2 Der Helfer antwortet „bei mir ist etwas schiefgelaufen"

Das ist die vorgesehene Antwort bei einer Störung. Der Kunde wird
gleichzeitig an Sie verwiesen.

**Was Sie tun:**
1. Warten Sie fünf Minuten und versuchen Sie es erneut.
2. Besteht die Störung weiter: Entwickler informieren und dabei
   **Uhrzeit und Wortlaut Ihrer Frage** nennen. Damit findet er den
   Vorgang im Fehlerprotokoll sofort.
3. Dauert es länger: Nehmen Sie die `<script>`-Zeile vorübergehend aus
   der Webseite. Besser kein Helfer als ein kaputter.

### 6.3 Der Helfer hat etwas Falsches gesagt

**Das ist der wichtigste Abschnitt dieser Anleitung.**

Der Helfer erfindet keine Angaben – aber er kann falsche Angaben aus
Ihrem Lager weitergeben. Steht im Lager ein falscher Preis, nennt er den
falschen Preis.

**Sofort, in dieser Reihenfolge:**

1. **Schreiben Sie auf, was passiert ist.** Datum, Uhrzeit, was der Kunde
   gefragt hat, was der Helfer geantwortet hat. Am besten mit
   Bildschirmfoto. Das brauchen Sie unter Umständen als Nachweis.
2. **Nehmen Sie Kontakt zum Kunden auf**, bevor er sich beschwert.
   Entschuldigen Sie sich sachlich und nennen Sie die richtige Angabe.
3. **Prüfen Sie Ihre Lagerdaten.** In den allermeisten Fällen stimmt dort
   etwas nicht: falscher Preis, falsches Modell, Teil längst verkauft.
   Korrigieren Sie es und lassen Sie den Abgleich neu laufen.
4. **Informieren Sie Ihren Entwickler**, auch wenn Sie die Ursache selbst
   gefunden haben. Nur so lässt sich derselbe Fehler für alle anderen
   Kunden verhindern.

**Ihre Haftung:** Ein falscher Preis im Chat ist kein bindendes Angebot.
Bindend wird es erst mit Ihrer Auftragsbestätigung. Sie müssen also nicht
zum Falschpreis liefern. Aus Kulanz ist es bei kleinen Beträgen oft
trotzdem klüger – eine schlechte Bewertung kostet mehr.

### 6.4 Ein Kunde beschwert sich über den Helfer

**Antwortvorlage:**

> Sehr geehrte/r …,
>
> vielen Dank, dass Sie uns darauf hinweisen. Die Auskunft in unserem
> Chat war in Ihrem Fall nicht richtig – das tut mir leid.
>
> Richtig ist: [richtige Angabe].
>
> Unser Chat ist ein automatischer Helfer. Er arbeitet mit unseren
> Lagerdaten, und in diesem Fall war dort ein Fehler, den wir
> inzwischen korrigiert haben.
>
> [Falls der Kunde einen Nachteil hatte: Für die Umstände möchte ich
> mich mit [Gutschrift / kostenlosem Versand / Rücknahme] entschuldigen.]
>
> Mit freundlichen Grüßen
> …

**Was Sie dabei vermeiden sollten:**
- Nicht „der Computer war schuld" – Sie sind verantwortlich, das erwartet
  der Kunde auch.
- Nicht behaupten, der Helfer sei ein Mensch gewesen. Das wäre ein
  Verstoß gegen die Transparenzpflicht (siehe Kapitel 7).
- Nicht ohne Prüfung Recht geben – lesen Sie erst nach, was tatsächlich
  gesagt wurde.

### 6.5 Jemand versucht, dem Helfer Interna zu entlocken

Das kommt vor. Der Helfer blockiert solche Fragen und vermerkt sie im
Protokoll. Sie müssen nichts tun.

Fragt jemand Sie direkt danach: Der Helfer kann Betriebsdaten nicht
preisgeben, weil der Kundenzugang in der Datenbank schlicht kein
Leserecht auf die Verkaufstabelle hat.

### 6.6 Verdacht auf Datenpanne

Wenn personenbezogene Daten abgeflossen sein könnten, haben Sie nach der
Datenschutz-Grundverordnung (DSGVO) **72 Stunden Zeit**, dies der
Aufsichtsbehörde zu melden (in Nordrhein-Westfalen: Landesbeauftragte
für Datenschutz und Informationsfreiheit NRW).

**Zur Einordnung:** Der Helfer speichert von sich aus keine Namen, keine
E-Mail-Adressen und keine IP-Adressen. Ein Datenabfluss über ihn ist
daher unwahrscheinlich. Melden Sie trotzdem im Zweifel – die Frist ist
kurz, und eine Meldung zu viel schadet nicht.

**Rufen Sie bei Verdacht sofort Ihren Entwickler an.** Nicht erst morgen.

---

## 7. Ihre rechtlichen Pflichten

> Dieses Kapitel ersetzt keine Rechtsberatung. Es nennt die Pflichten,
> die bei einem Helfer dieser Art üblicherweise greifen. Für
> verbindliche Auskünfte fragen Sie bitte eine Anwältin oder einen Anwalt.

### 7.1 Transparenz (EU-Verordnung über künstliche Intelligenz)

Seit dem 2. August 2026 gilt die Transparenzpflicht aus Artikel 50 der
KI-Verordnung: Wer mit einem KI-System spricht, muss das wissen.

**Das ist bereits erfüllt**, und zwar dreifach:
- Im Begrüßungssatz: „Ich bin ein Computerprogramm und kein Mensch."
- In einem Hinweisband, das dauerhaft im Fenster stehen bleibt.
- Über den Link „Was heißt das?", der Zweck, Arbeitsweise und Grenzen
  erklärt.

**Was Sie nicht tun dürfen:** diese Hinweise entfernen oder dem Helfer
einen Namen geben, der ihn als Mitarbeiter erscheinen lässt
(„Frau Müller vom Kundenservice"). Beides wäre ein Verstoß.

**Einstufung:** Der Helfer ist kein Hochrisiko-System im Sinne der
Verordnung. Er entscheidet nichts über Personen, bewertet niemanden und
betrifft keinen der im Anhang III genannten Bereiche. Es gelten daher nur
die Transparenzpflichten, nicht die umfangreichen Pflichten für
Hochrisiko-Systeme.

### 7.2 Datenschutz (DSGVO)

**Was gespeichert wird:**

| Angabe | Zweck | Dauer |
|---|---|---|
| Art des Vorgangs (Frage, Treffer, Fehler) | Störungen erkennen | 90 Tage |
| Suchbegriffe ohne Treffer | Einkauf steuern | 90 Tage |
| Nicht zurückrechenbare Sitzungskennung | Gespräche zuordnen | 90 Tage |
| Antwortzeiten | Betrieb überwachen | 90 Tage |

**Was nicht gespeichert wird:** Namen, E-Mail-Adressen, Telefonnummern,
IP-Adressen, Standorte. Es werden keine Cookies gesetzt und keine Daten
an Dritte übertragen.

**Was Sie trotzdem tun müssen:**

1. **Datenschutzerklärung ergänzen.** Textvorschlag:

   > **Chat-Assistent**
   > Auf unserer Webseite setzen wir einen automatischen Auskunftshelfer
   > ein. Er durchsucht unseren Lagerbestand und beantwortet Fragen zu
   > Teilen, Versand und Lieferzeiten. Er wird auf unseren eigenen
   > Servern betrieben; es werden keine Daten an Dritte übermittelt.
   >
   > Wir speichern pro Anfrage die Art des Vorgangs, eine nicht
   > zurückrechenbare Sitzungskennung und – bei erfolgloser Suche – den
   > Suchbegriff. Namen, E-Mail-Adressen und IP-Adressen werden nicht
   > gespeichert. Die Löschung erfolgt nach 90 Tagen.
   >
   > Rechtsgrundlage ist unser berechtigtes Interesse an einer
   > funktionierenden Kundenauskunft (Art. 6 Abs. 1 lit. f DSGVO).

2. **Verzeichnis von Verarbeitungstätigkeiten ergänzen.** Jedes
   Unternehmen muss ein solches Verzeichnis führen. Tragen Sie den
   Helfer dort als eigene Tätigkeit ein.

3. **Auftragsverarbeitungsvertrag.** Nötig, sobald ein Dienstleister die
   Daten für Sie verarbeitet – etwa der Anbieter, bei dem der Server oder
   die Datenbank läuft. Ihr Entwickler sagt Ihnen, welche Verträge Sie
   brauchen; die Anbieter stellen sie fertig bereit.

### 7.3 Pflichten als Händler

Der Helfer nennt Preise und Lieferzeiten. Dafür gelten die üblichen
Regeln:
- **Preisangabenverordnung:** Endpreise einschließlich Mehrwertsteuer.
  Der Helfer weist ausdrücklich darauf hin.
- **Lieferzeitangaben** müssen belastbar sein. Lassen Sie die hinterlegten
  Laufzeiten prüfen, wenn Sie den Versanddienstleister wechseln.
- **Widerrufsrecht:** Der Helfer nennt die 14 Tage und verweist für den
  Einzelfall an Sie. Ihre Widerrufsbelehrung bleibt maßgeblich.

### 7.4 Barrierefreiheit

Seit dem 28. Juni 2025 gilt das Barrierefreiheitsstärkungsgesetz für
Online-Shops. Der Helfer ist darauf ausgelegt: Schrift ab 17 Pixel,
Knöpfe ab 48 Pixel Höhe, starke Kontraste, vollständige
Tastaturbedienung, Beschriftungen für Vorlesesoftware, keine
Zeitbegrenzung.

**Ihre Pflicht bleibt bestehen**, auch die übrige Webseite barrierefrei
zu halten.

---

## 8. Was Sie aufbewahren müssen

| Unterlage | Wo | Wie lange |
|---|---|---|
| Diese Betriebsanleitung | ausgedruckt oder als Datei | solange der Helfer läuft |
| Notizen zu Zwischenfällen (6.3) | eigener Ordner | 3 Jahre |
| Beschwerden und Ihre Antworten | Kundenakte | 3 Jahre |
| Verzeichnis der Verarbeitungstätigkeiten | bei den Datenschutzunterlagen | fortlaufend |
| Auftragsverarbeitungsverträge | bei den Verträgen | solange genutzt + 3 Jahre |

Die drei Jahre entsprechen der regelmäßigen Verjährungsfrist. Bei einem
Rechtsstreit sind diese Notizen Ihr wichtigster Nachweis.

---

## 9. Häufige Fragen

**Kostet mich der Helfer laufend Geld?**
Nur den Server und die Datenbank. Es gibt keine Gebühr je Gespräch, weil
kein fremder Sprachmodell-Dienst angefragt wird. Die Bedeutungssuche
läuft auf Ihrem eigenen Server.

**Kann ich die Texte ändern?**
Ja. Alle Formulierungen stehen an einer Stelle im Programm und sind in
wenigen Minuten angepasst. Sagen Sie Ihrem Entwickler, was anders heißen
soll.

**Was passiert, wenn der Server ausfällt?**
Der Knopf erscheint, das Fenster öffnet sich, und der Helfer sagt, dass
er den Lagerbestand gerade nicht erreicht. Ihr Shop läuft weiter.

**Kann der Helfer bestellen?**
Nein, und das ist Absicht. Er führt zum richtigen Teil, bestellt wird im
Shop oder bei eBay. So bleibt der Kaufvorgang dort, wo Ihre
Allgemeinen Geschäftsbedingungen und Ihre Zahlungsabwicklung greifen.

**Lernt er aus den Gesprächen?**
Nein. Er verändert sich nicht von selbst. Das ist bewusst so: Ein System,
das sich selbst umbaut, lässt sich nicht verlässlich betreiben, und Sie
haften für jede Aussage. Besser wird er, wenn Ihre Lagerdaten besser
werden – oder wenn Ihr Entwickler etwas ändert.

**Versteht er auch andere Sprachen?**
Das Modell für die Bedeutungssuche ist mehrsprachig, die Antworten sind
auf Deutsch. Eine englische Anfrage findet oft das richtige Teil, die
Antwort kommt aber deutsch.

**Wie viele Kunden kann er gleichzeitig bedienen?**
Bei normaler Shopgröße genügt die kleinste Serverstufe. Falls Ihr Shop
stark wächst, braucht es nur mehr Rechenleistung – nicht ein anderes
System.

---

*Stand: Oktober 2026. Bei Rückfragen zu dieser Anleitung wenden Sie sich
an Ihren Entwickler.*
