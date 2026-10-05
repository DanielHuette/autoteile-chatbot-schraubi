"""Gespraechsfuehrung.

Der Bot erzeugt keine freien Texte. Jede Antwort ist eine Vorlage,
in die gepruefte Werte aus der Datenbank eingesetzt werden. Das hat
drei Gruende:

1. Er kann keine Preise, Lieferzeiten oder Teilenummern erfinden.
   Erfundene Angaben sind bei Ersatzteilen teuer: ein falsch
   bestelltes Teil geht zurück, der Kunde ist weg.
2. Es gibt kein Sprachmodell, das sich durch eingeschmuggelte
   Anweisungen umstimmen liesse.
3. Jede Formulierung ist nachlesbar und aenderbar, ohne das System
   neu zu trainieren. Der Betreiber haftet für Aussagen seines
   Assistenten – also müssen sie an einer Stelle stehen.

Die Intelligenz liegt im Verstehen (pgvector, Volltext, Wortliste),
nicht im Formulieren.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field
from typing import Any

from .embeddings import normalisieren
from .search import Filter, TeileSuche
from .shipping import Versand
from .vokabular import stamm

# ---------------------------------------------------------------------
# Absichten des Kunden
# ---------------------------------------------------------------------
GRUSSWORTE = {stamm(w) for w in ("hallo", "hi", "guten", "tag", "moin", "servus", "gruezi", "hey")}
DANK = {stamm(w) for w in ("danke", "dankeschoen", "vielen", "merci")}
ABSCHIED = {stamm(w) for w in ("tschuess", "wiedersehen", "ciao", "bye", "ende", "feierabend")}
VERSANDWORTE = {stamm(w) for w in (
    "versand", "lieferung", "liefern", "liefert", "versenden", "verschicken",
    "porto", "versandkosten", "zustellung", "paket", "spedition", "lieferzeit",
    "dauer", "dauert", "wann", "ankunft", "ausland", "eu",
)}
MENSCHWORTE = {stamm(w) for w in (
    "mensch", "mitarbeiter", "anrufen", "telefon", "telefonnummer", "rueckruf",
    "sprechen", "berater", "jemand", "kontakt", "erreichen",
)}
KIWORTE = {stamm(w) for w in ("roboter", "computer", "bot", "maschine", "echt", "ki", "programm")}
RUECKGABE = {stamm(w) for w in (
    "ruecksendung", "ruecksenden", "zurueckschicken", "umtausch", "widerruf",
    "garantie", "gewaehrleistung", "reklamation", "defekt", "kaputt", "retoure",
)}
EINBAU = {stamm(w) for w in ("einbauen", "einbau", "montage", "montieren", "anleitung", "wechseln")}
ZAHLUNG = {stamm(w) for w in ("bezahlen", "zahlung", "zahlen", "rechnung", "vorkasse",
                              "paypal", "ueberweisung", "nachnahme", "lastschrift")}
HILFEWORTE = {stamm(w) for w in ("hilfe", "helfen", "weiss", "keine", "ahnung", "finde",
                                 "suche", "brauche", "unsicher")}

# Laendernamen -> Laendercode, für Versandfragen.
LAENDER: dict[str, str] = {
    "deutschland": "DE", "de": "DE", "brd": "DE",
    "oesterreich": "AT", "at": "AT",
    "schweiz": "CH", "ch": "CH",
    "niederlande": "NL", "holland": "NL", "nl": "NL",
    "belgien": "BE", "be": "BE",
    "luxemburg": "LU", "lu": "LU",
    "frankreich": "FR", "fr": "FR",
    "italien": "IT", "it": "IT",
    "spanien": "ES", "es": "ES",
    "polen": "PL", "pl": "PL",
    "daenemark": "DK", "dk": "DK",
    "tschechien": "CZ", "cz": "CZ",
    "schweden": "SE", "se": "SE",
}

# Der Katalog des Klick-Interviews. Reihenfolge ist fest, weil jeder
# Schritt die Auswahl des nächsten einschraenkt.
SCHRITTE = ("marke", "modell", "baujahr", "kategorie", "bauteil")

SCHRITT_FRAGE = {
    "marke": "Welche Automarke fahren Sie?",
    "modell": "Und welches Modell ist es?",
    "baujahr": "Aus welchem Baujahr ist das Fahrzeug?",
    "kategorie": "Wo am Auto sitzt das Teil?",
    "bauteil": "Welches Teil brauchen Sie genau?",
}

SCHRITT_HINWEIS = {
    "marke": "Die Marke steht meist vorne am Kuehlergrill und in Ihrem Fahrzeugschein unter Feld D.1.",
    "modell": "Das Modell steht im Fahrzeugschein unter Feld D.3, zum Beispiel \"Golf\" oder \"Astra\".",
    "baujahr": "Das Baujahr finden Sie im Fahrzeugschein unter Feld B - das ist der Tag der Erstzulassung.",
    "kategorie": "Einfach den Bereich antippen, der am besten passt. Sie können jederzeit zurueckgehen.",
    "bauteil": "Falls Sie unsicher sind: tippen Sie, was am nächsten kommt. Ich zeige Ihnen dann Bilder und Preise.",
}


@dataclass
class Antwort:
    """Eine Bot-Antwort. 'blasen' sind einzelne Sprechblasen, damit kein
    Textblock entsteht, den niemand liest."""
    blasen: list[str] = field(default_factory=list)
    knoepfe: list[dict[str, str]] = field(default_factory=list)
    teile: list[dict[str, Any]] = field(default_factory=list)
    interview: dict[str, Any] | None = None
    art: str = "antwort"
    absicht: str = ""
    hinweis: str = ""
    tabelle: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "blasen": self.blasen,
            "knoepfe": self.knoepfe,
            "teile": self.teile,
            "interview": self.interview,
            "art": self.art,
            "absicht": self.absicht,
            "hinweis": self.hinweis,
            "tabelle": self.tabelle,
        }


def sitzungs_hash(roh: str) -> str:
    return hashlib.blake2b(roh.encode("utf-8"), digest_size=8).hexdigest()


class Gespraech:
    def __init__(self, db, suche: TeileSuche, versand: Versand, settings) -> None:
        self.db = db
        self.suche = suche
        self.versand = versand
        self.s = settings

    # -- Begrueszung (EU-KI-Verordnung Art. 50: Offenlegung) ---------
    def begruessung(self) -> Antwort:
        return Antwort(
            blasen=[
                f"Hallo! Ich bin Schraubi, der automatische Helfer von {self.s.shop_name}. "
                "Ich bin ein Computerprogramm und kein Mensch.",
                "Ich finde für Sie gebrauchte Autoteile, nenne Preise und sage Ihnen, "
                "wie lange die Lieferung dauert.",
                "Sie brauchen keine Teilenummer. Beschreiben Sie einfach, was Sie suchen – "
                "oder lassen Sie sich von mir durchfragen.",
            ],
            knoepfe=[
                {"text": "Teil Schritt für Schritt finden", "aktion": "interview_start"},
                {"text": "Versand und Lieferzeit", "aktion": "frage:Wohin liefern Sie und wie lange dauert es?"},
                {"text": "Ich habe eine Teilenummer", "aktion": "hinweis_nummer"},
            ],
            art="begruessung",
            absicht="begruessung",
        )

    # -- Klick-Interview ---------------------------------------------
    def interview(self, stand: dict[str, Any] | None) -> Antwort:
        stand = dict(stand or {})
        marke = stand.get("marke")
        modell = stand.get("modell")
        jahr = stand.get("jahr")
        kategorie = stand.get("kategorie")
        bauteil = stand.get("bauteil")

        def gerueest(schritt: str, optionen: list[dict], zurueck: str | None) -> Antwort:
            knoepfe = [
                {"text": self._option_text(o), "aktion": f"interview:{schritt}:{o['wert']}"}
                for o in optionen
            ]
            if zurueck:
                knoepfe.append({"text": "< Zurück", "aktion": f"interview_zurueck:{zurueck}"})
            knoepfe.append({"text": "Abbrechen", "aktion": "interview_ende"})
            return Antwort(
                blasen=[SCHRITT_FRAGE[schritt]],
                knoepfe=knoepfe,
                interview={"schritt": schritt, "stand": stand,
                           "fortschritt": SCHRITTE.index(schritt) + 1,
                           "schritte_gesamt": len(SCHRITTE)},
                art="interview",
                absicht="interview",
                hinweis=SCHRITT_HINWEIS[schritt],
            )

        if not marke:
            optionen = self.db.marken()
            if not optionen:
                return self._kein_bestand()
            return gerueest("marke", optionen, None)

        if not modell:
            optionen = self.db.modelle(marke)
            if not optionen:
                stand.pop("marke", None)
                return gerueest("marke", self.db.marken(), None)
            return gerueest("modell", optionen, "marke")

        if not jahr:
            spannen = self.db.baujahre(marke, modell)
            if not spannen:
                # Kein Baujahr erfasst – Schritt ueberspringen statt
                # den Kunden vor eine leere Auswahl zu stellen.
                stand["jahr"] = 0
                return self.interview(stand)
            return gerueest("baujahr", spannen, "modell")

        jahr_filter = int(jahr) if jahr else None
        if not kategorie:
            optionen = self.db.kategorien(marke, modell, jahr_filter)
            if not optionen:
                stand["jahr"] = 0
                optionen = self.db.kategorien(marke, modell, None)
                if not optionen:
                    return self._kein_treffer_interview(stand)
            return gerueest("kategorie", optionen, "baujahr")

        if not bauteil:
            optionen = [
                o for o in self.db.bauteile(marke, modell, kategorie, jahr_filter) if o["wert"]
            ]
            if not optionen:
                # Kategorie hat keine Unterteilung: direkt die Teile zeigen.
                return self.ergebnis_zeigen(stand, kategorie)
            return gerueest("bauteil", optionen, "kategorie")

        return self.ergebnis_zeigen(stand, kategorie, bauteil)

    @staticmethod
    def _option_text(o: dict) -> str:
        anzahl = o.get("anzahl")
        if anzahl:
            return f"{o['wert']}  ({anzahl})"
        return str(o["wert"])

    def ergebnis_zeigen(
        self, stand: dict[str, Any], kategorie: str, bauteil: str | None = None
    ) -> Antwort:
        jahr = int(stand.get("jahr") or 0) or None
        f = Filter(
            marke=stand.get("marke"), modell=stand.get("modell"), jahr=jahr,
            kategorie=kategorie, bauteil=bauteil,
        )
        begriff = " ".join(str(x) for x in [bauteil or kategorie, stand.get("marke"), stand.get("modell")] if x)
        ergebnis = self.suche.suchen_ausfuehrlich(begriff, f, limit=6)
        if not ergebnis.treffer:
            return self._kein_treffer_interview(stand)
        return self._treffer_antwort(
            ergebnis.treffer, begriff, aus_interview=True, gelockert=ergebnis.gelockert
        )

    def _kein_treffer_interview(self, stand: dict[str, Any]) -> Antwort:
        return Antwort(
            blasen=[
                "Dazu habe ich im Moment leider kein passendes Teil auf Lager.",
                "Täglich kommen neue Teile dazu. Am besten fragen Sie direkt nach - "
                "oft können wir ein Teil beschaffen.",
            ],
            knoepfe=[
                {"text": "Noch einmal von vorn", "aktion": "interview_start"},
                {"text": "Kontakt zum Shop", "aktion": "kontakt"},
            ],
            art="kein_treffer",
            absicht="interview",
        )

    def _kein_bestand(self) -> Antwort:
        return Antwort(
            blasen=[
                "Im Moment kann ich den Lagerbestand nicht einsehen.",
                "Bitte wenden Sie sich direkt an den Shop – dort hilft man Ihnen sofort weiter.",
            ],
            knoepfe=[{"text": "Kontakt zum Shop", "aktion": "kontakt"}],
            art="fehler",
            absicht="bestand_leer",
        )

    # -- Freitextsuche -----------------------------------------------
    LOCKERUNG_TEXT = {
        "seite": "Zur genauen Seite (links oder rechts) habe ich nichts gefunden, "
                 "deshalb zeige ich Ihnen beide Seiten. Bitte achten Sie in der "
                 "Teilebezeichnung darauf.",
        "baujahr": "Für das genannte Baujahr habe ich nichts gefunden. Diese Teile "
                   "sind von anderen Baujahren – bitte vor dem Kauf abgleichen oder "
                   "kurz nachfragen.",
        "modell": "Für dieses Modell habe ich das Teil nicht. Hier sind ähnliche "
                  "Teile der Marke – ob sie passen, klaeren Sie am besten direkt "
                  "mit dem Shop.",
        "vorrat": "Diese Teile sind gerade nicht auf Lager. Oft können wir sie "
                  "beschaffen – fragen Sie am besten direkt nach.",
    }

    def _treffer_antwort(
        self, treffer, begriff: str, aus_interview: bool = False,
        gelockert: list[str] | None = None,
    ) -> Antwort:
        teile = [t.as_dict() for t in treffer]
        auf_lager = [t for t in teile if not t["on_ebay"]]
        auf_ebay = [t for t in teile if t["on_ebay"]]

        blasen: list[str] = []
        if len(teile) == 1:
            t = teile[0]
            blasen.append(f"Ich habe genau ein passendes Teil gefunden: {t['title']}.")
        else:
            blasen.append(f"Ich habe {len(teile)} passende Teile gefunden. Hier die besten:")

        if auf_ebay:
            blasen.append(
                f"{'Ein Teil' if len(auf_ebay) == 1 else f'{len(auf_ebay)} dieser Teile'} "
                "verkaufen wir über unseren eBay-Marktplatz. Dort bestellen Sie genauso "
                "sicher – ein Antippen genügt, ich habe den Link gleich mit angelegt."
            )

        # Was musste gelockert werden? Das wird gesagt, nicht verschwiegen -
        # ein unpassendes Teil kostet Rückversand und Vertrauen.
        warnungen = [self.LOCKERUNG_TEXT[g] for g in (gelockert or []) if g in self.LOCKERUNG_TEXT]
        blasen.extend(warnungen)

        knoepfe = [
            {"text": "Versandkosten und Lieferzeit", "aktion": "frage:Was kostet der Versand und wie lange dauert er?"},
        ]
        if not aus_interview:
            knoepfe.append({"text": "Nichts passt – durchfragen lassen", "aktion": "interview_start"})
        knoepfe.append({"text": "Kontakt zum Shop", "aktion": "kontakt"})

        return Antwort(
            blasen=blasen, knoepfe=knoepfe, teile=teile,
            art="treffer", absicht="teilesuche",
            hinweis=(
                "Alle Teile sind gebraucht und geprüft. Die Preise sind Endpreise "
                "inklusive Mehrwertsteuer, zuzüglich Versand."
                if auf_lager else ""
            ),
        )

    def _kein_treffer(self, text: str, ergebnis=None) -> Antwort:
        # Wenn klar ist, WAS gesucht wurde, wird das gesagt. "Ich finde
        # nichts" ist für den Kunden wertlos; "Rückleuchte für den
        # Golf V habe ich nicht" kann er gebrauchen.
        erkannt = getattr(ergebnis, "erkennung", None)
        if erkannt and erkannt.bauteil:
            was = erkannt.bauteil
            fahrzeug = " ".join(x for x in [erkannt.marke, erkannt.modell] if x)
            erste = (
                f"{was} für {fahrzeug} habe ich im Moment nicht auf Lager."
                if fahrzeug else f"{was} habe ich im Moment nicht auf Lager."
            )
            return Antwort(
                blasen=[
                    erste,
                    "Täglich kommen neue Teile dazu, und oft können wir ein Teil "
                    "beschaffen. Ein kurzer Anruf lohnt sich.",
                ],
                knoepfe=[
                    {"text": "Anderes Teil suchen", "aktion": "interview_start"},
                    {"text": "Kontakt zum Shop", "aktion": "kontakt"},
                ],
                art="kein_treffer", absicht="teilesuche",
            )
        return Antwort(
            blasen=[
                "Dazu finde ich im Moment kein passendes Teil.",
                "Das muss nichts heissen – täglich kommen neue Teile dazu, und "
                "manchmal heißt ein Teil bei uns anders.",
                "Am sichersten ist es, wenn ich Sie Schritt für Schritt durchfrage. "
                "Das dauert keine Minute.",
            ],
            knoepfe=[
                {"text": "Ja, durchfragen lassen", "aktion": "interview_start"},
                {"text": "Kontakt zum Shop", "aktion": "kontakt"},
            ],
            art="kein_treffer", absicht="teilesuche",
        )

    # -- Versandauskunft ---------------------------------------------
    def versandauskunft(self, text: str, jetzt: dt.datetime | None = None) -> Antwort:
        norm = normalisieren(text)
        code = None
        for name, c in LAENDER.items():
            if name in norm.split() or (len(name) > 3 and name in norm):
                code = c
                break

        if code is None:
            zonen = self.versand.zonen()
            if not zonen:
                return self._kein_bestand()
            laender = ", ".join(z["country_name"] for z in zonen[:12])
            guenstig = min(zonen, key=lambda z: z["cost_cents"])
            return Antwort(
                blasen=[
                    f"Wir verschicken in diese Laender: {laender}.",
                    f"Innerhalb Deutschlands kostet der Versand ab "
                    f"{guenstig['cost_cents'] / 100:.2f} Euro.",
                    "Sagen Sie mir einfach, wohin es gehen soll – dann nenne ich Ihnen "
                    "Kosten und Liefertag genau.",
                ],
                knoepfe=[
                    {"text": "Deutschland", "aktion": "frage:Versand nach Deutschland"},
                    {"text": "Österreich", "aktion": "frage:Versand nach Österreich"},
                    {"text": "Anderes Land", "aktion": "laenderliste"},
                ],
                art="versand", absicht="versand",
                tabelle=[
                    {
                        "land": z["country_name"],
                        "kosten_euro": round(z["cost_cents"] / 100, 2),
                        "werktage": f"{z['days_min']}-{z['days_max']}",
                    }
                    for z in zonen
                ],
            )

        auskunft = self.versand.auskunft(code, 1000, jetzt)
        if not auskunft:
            return Antwort(
                blasen=["In dieses Land verschicken wir derzeit leider nicht."],
                knoepfe=[{"text": "Kontakt zum Shop", "aktion": "kontakt"}],
                art="versand", absicht="versand",
            )
        return Antwort(
            blasen=[auskunft.als_satz()],
            knoepfe=[
                {"text": "Teil suchen", "aktion": "interview_start"},
                {"text": "Anderes Land", "aktion": "laenderliste"},
            ],
            art="versand", absicht="versand",
            hinweis="Schwere Teile wie Motoren oder Türen gehen per Spedition. "
                    "Das steht beim jeweiligen Teil dabei.",
            tabelle=[auskunft.as_dict()],
        )

    # -- Feste Auskünfte --------------------------------------------
    def kontakt(self) -> Antwort:
        zeilen = ["Gern – hier erreichen Sie einen Menschen:"]
        if self.s.operator_phone:
            zeilen.append(f"Telefon: {self.s.operator_phone}")
        if self.s.operator_email:
            zeilen.append(f"E-Mail: {self.s.operator_email}")
        if len(zeilen) == 1:
            zeilen.append("Die Kontaktdaten stehen im Impressum dieser Webseite.")
        return Antwort(
            blasen=zeilen,
            knoepfe=[{"text": "Doch weitersuchen", "aktion": "interview_start"}],
            art="kontakt", absicht="mensch",
        )

    def ki_offenlegung(self) -> Antwort:
        return Antwort(
            blasen=[
                "Nein, ich bin kein Mensch. Ich bin ein Computerprogramm, das den "
                "Lagerbestand durchsucht.",
                "Ich erfinde keine Angaben: Preise, Bestand und Lieferzeiten lese ich "
                "direkt aus dem Lager. Was ich nicht finde, sage ich Ihnen ehrlich.",
                "Wenn Sie lieber mit einem Menschen sprechen, gebe ich Ihnen die Nummer.",
            ],
            knoepfe=[{"text": "Kontakt zum Shop", "aktion": "kontakt"}],
            art="antwort", absicht="ki_frage",
        )

    def rueckgabe(self) -> Antwort:
        return Antwort(
            blasen=[
                "Als Privatkunde haben Sie 14 Tage Widerrufsrecht – Sie können das Teil "
                "ohne Begruendung zurückschicken.",
                "Bei gebrauchten Teilen gilt ausserdem eine gesetzliche Gewährleistung "
                "von einem Jahr.",
                "Die genauen Bedingungen stehen in den Allgemeinen Geschaeftsbedingungen "
                "dieser Webseite. Für einen konkreten Fall melden Sie sich am besten "
                "direkt beim Shop – dort wird das persoenlich geklaert.",
            ],
            knoepfe=[{"text": "Kontakt zum Shop", "aktion": "kontakt"}],
            art="antwort", absicht="rueckgabe",
            hinweis="Diese Angaben sind allgemein und keine Rechtsberatung.",
        )

    def einbau(self) -> Antwort:
        return Antwort(
            blasen=[
                "Zum Einbau kann ich Ihnen leider nicht raten – das haengt zu sehr vom "
                "Fahrzeug ab, und ein Fehler am Auto kann gefaehrlich werden.",
                "Beim Teil selbst helfe ich gern: ich sage Ihnen, ob es zu Ihrem Fahrzeug "
                "passt, was es kostet und wann es da ist.",
            ],
            knoepfe=[{"text": "Passendes Teil finden", "aktion": "interview_start"}],
            art="antwort", absicht="einbau",
        )

    def zahlung(self) -> Antwort:
        return Antwort(
            blasen=[
                "Welche Zahlungsarten möglich sind, steht beim Bestellvorgang und in "
                "den Allgemeinen Geschaeftsbedingungen dieser Webseite.",
                "Dazu kann ich Ihnen keine verbindliche Auskunft geben – dafuer ist der "
                "Shop selbst zuständig.",
            ],
            knoepfe=[{"text": "Kontakt zum Shop", "aktion": "kontakt"}],
            art="antwort", absicht="zahlung",
        )

    def dank(self) -> Antwort:
        return Antwort(
            blasen=["Gern! Wenn noch etwas ist, bin ich da."],
            knoepfe=[{"text": "Weiteres Teil suchen", "aktion": "interview_start"}],
            art="antwort", absicht="dank",
        )

    def abschied(self) -> Antwort:
        return Antwort(
            blasen=["Alles Gute und gute Fahrt!"],
            art="antwort", absicht="abschied",
        )

    def nummer_hinweis(self) -> Antwort:
        return Antwort(
            blasen=[
                "Sehr gut – mit einer Nummer finde ich das Teil sofort.",
                "Tippen Sie die Nummer einfach ins Feld, mit oder ohne Bindestriche. "
                "Beides geht.",
            ],
            art="antwort", absicht="nummer_hinweis",
        )

    # -- Einstieg ----------------------------------------------------
    def absicht(self, text: str) -> str:
        norm = normalisieren(text)
        staemme = {stamm(w) for w in norm.split()}
        if not staemme:
            return "leer"
        # Reihenfolge nach Eindeutigkeit: wer nach Rückgabe fragt, fragt
        # nicht nach einem Teil, auch wenn "kaputt" nach Teil klingt.
        #
        # "Bist du ein Mensch?" ist eine Frage NACH dem Bot, nicht der
        # Wunsch nach einem Mitarbeiter. Beide enthalten das Wort
        # "Mensch" - unterschieden wird an der Anrede.
        fragt_nach_bot = any(
            m in norm for m in ("bist du", "sind sie ein", "bist du ein", "rede ich mit",
                                "spreche ich mit", "bin ich bei", "wer bist du", "was bist du")
        )
        if fragt_nach_bot and (staemme & (KIWORTE | MENSCHWORTE)):
            return "ki_frage"
        if staemme & KIWORTE and len(staemme) <= 8:
            return "ki_frage"
        if staemme & MENSCHWORTE:
            return "mensch"
        if staemme & RUECKGABE:
            return "rueckgabe"
        if staemme & ZAHLUNG:
            return "zahlung"
        if staemme & EINBAU:
            return "einbau"
        if staemme & VERSANDWORTE:
            return "versand"
        if staemme & ABSCHIED:
            return "abschied"
        if staemme & DANK and len(staemme) <= 4:
            return "dank"
        if staemme & GRUSSWORTE and len(staemme) <= 3:
            return "begruessung"
        if staemme & HILFEWORTE and len(staemme) <= 5:
            return "hilfe"
        return "teilesuche"

    def antworten(self, text: str, jetzt: dt.datetime | None = None) -> Antwort:
        absicht = self.absicht(text)
        if absicht == "leer":
            return self.begruessung()
        if absicht == "begruessung":
            return self.begruessung()
        if absicht == "ki_frage":
            return self.ki_offenlegung()
        if absicht == "mensch":
            return self.kontakt()
        if absicht == "rueckgabe":
            return self.rueckgabe()
        if absicht == "zahlung":
            return self.zahlung()
        if absicht == "einbau":
            return self.einbau()
        if absicht == "versand":
            return self.versandauskunft(text, jetzt)
        if absicht == "abschied":
            return self.abschied()
        if absicht == "dank":
            return self.dank()
        if absicht == "hilfe":
            return self.interview(None)

        ergebnis = self.suche.suchen_ausfuehrlich(text, limit=6)
        if not ergebnis.treffer:
            return self._kein_treffer(text, ergebnis)
        return self._treffer_antwort(ergebnis.treffer, text, gelockert=ergebnis.gelockert)
