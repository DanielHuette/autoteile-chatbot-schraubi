# LinkedIn: fertige Texte zum Einfügen

Drei Bausteine. Die Zahlen stammen aus den Messreihen im Repository und
sind reproduzierbar – bitte vor dem Veröffentlichen gegen
`bench/results/` abgleichen, falls du die Messung mit anderen Werten
wiederholst.

---

## 1. Beitrag für den Feed

> Ein Kunde, 72 Jahre alt, sucht ein Rücklicht. Er hat keine
> Teilenummer. Er schreibt: „das rote Glas hinten links ist kaputt".
>
> Eine reine Vektorsuche antwortet darauf gern mit einer Bremsscheibe
> für denselben Wagen. Marke stimmt, Teil ist falsch. Für den Kunden
> heißt das: Rückversand, Ärger, verlorener Kauf.
>
> Ich habe den Auskunftshelfer für einen Gebrauchtteile-Versandshop
> gebaut und dabei gemessen, woran es wirklich liegt.
>
<!-- MESSWERTE-POST -->
> Die Messreihe über 207 echte Kundenformulierungen gegen
> 10.000 Lagerteile:
>
> → nur Volltextsuche: 61,8 % richtig auf Platz 1
> → nur Vektorsuche (pgvector, HNSW): 50,7 %
> → beides zusammengeführt (Reciprocal Rank Fusion): 77,8 %
> → zusätzlich Bauteilerkennung und Mindestähnlichkeit: 93,2 %
>
> Die interessante Zahl ist nicht die 93. Es ist die 51.
<!-- /MESSWERTE-POST -->
>
> Semantische Ähnlichkeit allein reicht bei Ersatzteilen nicht, weil
> zwei Dinge gleichzeitig stimmen müssen: das Bauteil UND das Fahrzeug.
> Das Einbettungsmodell gewichtet beides gleich. Der Mensch nicht –
> für ihn entscheidet zuerst das Bauteil. Diese Fachlogik muss man
> hineinbauen, sie entsteht nicht aus dem Modell.
>
> Drei Entscheidungen, die ich begründen kann:
>
> 1. pgvector statt eigener Vektordatenbank. Suchvektor, Preis, Bestand
> und eBay-Kennzeichen liegen in derselben Zeile. Eine Abfrage, ein
> Datenstand. Zwei Systeme, die auseinanderlaufen, gibt es nicht.
>
> 2. Kein generatives Sprachmodell in der Antwort. Alle Antworten
> kommen aus festen Vorlagen mit Werten aus der Datenbank. Damit kann
> der Helfer keinen Preis und keine Lieferzeit erfinden – und es gibt
> keine Prompt Injection, weil es keinen Prompt gibt. Nebeneffekt:
> keine Kosten je Gespräch.
>
> 3. Der Shop-Betreiber bekommt seine Umsatzzahlen über eine getrennte
> Anmeldung mit eigenem Verlauf. Der Kundenzugang hat in PostgreSQL
> schlicht kein Leserecht auf die Verkaufstabelle. Das ist kein
> Versprechen im Code, sondern eine Rechtevergabe in der Datenbank.
>
> Dazu: Klick-Interview für Kunden ohne Teilenummer, Transparenzhinweise
> nach EU-KI-Verordnung, Bedienbarkeit ab 17 Pixel Schriftgröße und
> eine Betriebsanleitung, die ein Mensch ohne IT-Kenntnisse befolgen
> kann.
>
> Code, Messreihen und Dokumentation sind offen:
> github.com/DanielHuette/autoteile-chatbot-schraubi
>
> #pgvector #PostgreSQL #FastAPI #SemanticSearch #RAG #EUAIAct
> #Barrierefreiheit #AIEngineering

---

## 2. Text für den Bereich „Im Fokus" (Featured)

**Titel**
> Schraubi – Auskunftshelfer für einen Gebrauchtteile-Versandshop

**Beschreibung**

> Ein Chat-Assistent, der Kunden ohne Teilenummer zum richtigen
> Autoteil führt – gebaut für Menschen, die nicht mit Computern
> aufgewachsen sind.
>
> **Das Problem**
> Gebrauchtteile-Kunden beschreiben, was kaputt ist, nicht was sie
> brauchen: „das rote Glas hinten links", „der Auspufftopf ist
> durchgerostet". Eine Volltextsuche findet darauf nichts. Eine
> Vektorsuche findet irgendetwas vom richtigen Fahrzeug – oft das
> falsche Teil.
>
> **Die Lösung**
> Vier Schichten, die zusammen greifen:
> • exakter Nummerntreffer, wenn eine Teilenummer genannt wird
> • Erkennung von Bauteil, Marke, Modell und Lage, abgeleitet aus dem
>   echten Lagerbestand, mit Tippfehlerkorrektur
> • Vektorsuche (pgvector, HNSW, Kosinus) und deutscher Volltext,
>   zusammengeführt per Reciprocal Rank Fusion
> • Mindestähnlichkeit: unterhalb der Schwelle sagt das System ehrlich
>   „habe ich nicht", statt sechs falsche Teile anzubieten
>
<!-- MESSWERTE-FEATURED -->
> **Gemessen. nicht behauptet** (207 Kundenanfragen. 10.000 Lagerteile)
> • nur Volltextsuche: 61,8 % Treffer auf Platz 1
> • nur Vektorsuche: 50,7 %
> • zusammengeführt: 77,8 %
> • vollständiges System: 93,2 %, Mittelwert der Platzierung 0,932
> • falsches Teil an erster Stelle: von 49,3 % auf 1,9 %
<!-- /MESSWERTE-FEATURED -->
>
> **Antwortzeit** HNSW-Index gegen sequenziellen Durchlauf, inklusive
> Trefferübereinstimmung mit der exakten Suche – denn ein
> Näherungsverfahren ist nur brauchbar, wenn es auch das Richtige
> findet.
>
> **Weitere Bestandteile**
> • Klick-Interview: Marke → Modell → Baujahr → Bereich → Bauteil, nur
>   Knöpfe, Auswahl immer aus dem tatsächlichen Bestand
> • eBay-Anbindung: Teile des Shops auf dem Marktplatz werden mit
>   direktem Link weitergereicht
> • Rollentrennung: Kunden erhalten keine Betriebsdaten – durchgesetzt
>   in der Anwendung und zusätzlich über Datenbankrechte
> • EU-KI-Verordnung: Offenlegung als KI, Auskunft über Zweck,
>   Arbeitsweise und Grenzen, Fehlerprotokollierung
> • Barrierefreiheit: 17 px Grundschrift, 48 px Knopfhöhe, vollständige
>   Tastaturbedienung, Beschriftungen für Vorlesesoftware
> • Einbau beim Betreiber mit einer Zeile HTML
> • <!-- MESSWERTE-TESTZAHL -->139<!-- /MESSWERTE-TESTZAHL --> automatische Tests, Dauerprüfung bei jeder Änderung
> • Betriebsanleitung in Alltagssprache, mit Notfallplan und
>   Rechtsaufklärung
>
> **Technik** Python 3.12 · FastAPI · PostgreSQL 16 · pgvector (HNSW) ·
> mehrsprachiges Einbettungsmodell auf eigenem Server · reines
> JavaScript ohne Framework · Docker
>
> github.com/DanielHuette/autoteile-chatbot-schraubi

---

## 3. Kurzfassung für das Profil-Infofeld

> Baue KI-Systeme, die auch dann noch richtig antworten, wenn der
> Nutzer die Fachbegriffe nicht kennt. Zuletzt: ein Auskunftshelfer
> für einen Autoteile-Versandshop, der Laienbeschreibungen in
> <!-- MESSWERTE-KURZ -->93,2 %<!-- /MESSWERTE-KURZ --> der Fälle dem richtigen
> Bauteil zuordnet – gemessen, nicht geschätzt.
> Schwerpunkt: pgvector, hybride Suche, nachvollziehbare Antworten
> statt freier Texterzeugung.

---

## Hinweise zum Veröffentlichen

- **Bilder zum Beitrag:** Die Bildfassungen liegen fertig bereit, weil
  LinkedIn kein SVG anzeigt. In dieser Reihenfolge anhängen:
  1. `docs/assets/messung-qualitaet.png` – die Zahl, um die es geht
  2. `docs/assets/architektur.png` – wie das System aufgebaut ist
  3. `docs/bilder/h-vage-suche.png` – was der Kunde sieht
  4. `docs/assets/messung-latenz.png` – für Nachfragen zum Index

  Beiträge mit Bild werden deutlich häufiger gesehen; die erste Grafik
  entscheidet, ob jemand stehen bleibt. Deshalb steht dort die Messung
  und nicht das Schaubild.

  Die Bildfassungen entstehen beim Erzeugen der Diagramme von selbst
  (`python bench/diagramme.py` und `python bench/architektur.py`).
- **Im Fokus:** Repository-Adresse einfügen, LinkedIn zieht Titel und
  Vorschaubild automatisch. Titel und Beschreibung danach von Hand auf
  die Texte oben setzen.
- **Kommentare:** Auf die Frage „Warum kein großes Sprachmodell?"
  passt: *Für die Antwortformulierung braucht es keins – und ohne
  Sprachmodell kann der Helfer keine Preise erfinden. Die Intelligenz
  steckt im Verstehen, nicht im Formulieren.*
