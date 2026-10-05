#!/usr/bin/env python3
"""Oberflächentest: spielt das Widget im echten Browser durch.

Geprüft wird, was ein Mensch sieht – nicht, was die Schnittstelle
zurückgibt. Nebenbei entstehen die Bildschirmfotos für die
Projektbeschreibung, damit dort keine veralteten Bilder stehen.

Voraussetzung: Server und Demoseite laufen.

    python scripts/mitenv.py .env uvicorn app.main:app --app-dir backend --port 8099
    python -m http.server 8080 --directory widget

Aufruf:

    python tests/oberflaeche.py --passwort 'IhrPasswort' --bilder docs/bilder
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright fehlt:  pip install playwright && playwright install chromium")
    sys.exit(2)

fehler: list[str] = []
hinweise: list[str] = []


def pruefe(bedingung: bool, meldung: str) -> None:
    if bedingung:
        hinweise.append(f"   ok   {meldung}")
    else:
        fehler.append(meldung)


async def lauf(args) -> None:
    bilder = pathlib.Path(args.bilder)
    bilder.mkdir(parents=True, exist_ok=True)
    konsole: list[tuple[str, str]] = []

    async def foto(seite, name):
        await seite.wait_for_timeout(450)
        await seite.locator(".tt-fenster").screenshot(path=str(bilder / f"{name}.png"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=args.browser or None)
        seite = await browser.new_page(viewport={"width": 1280, "height": 900},
                                       device_scale_factor=2)
        seite.on("console", lambda m: konsole.append((m.type, m.text)))
        seite.on("pageerror", lambda e: konsole.append(("pageerror", str(e))))

        await seite.goto(args.demo)
        await seite.wait_for_timeout(900)
        await seite.screenshot(path=str(bilder / "00-shop-mit-knopf.png"),
                               clip={"x": 760, "y": 540, "width": 520, "height": 360})
        pruefe(await seite.locator(".tt-knopf").is_visible(), "Startknopf ist sichtbar")

        # --- Begrüßung und Offenlegung -----------------------------
        await seite.click(".tt-knopf")
        await seite.wait_for_selector(".tt-blase", timeout=20000)
        await seite.wait_for_timeout(1100)
        await seite.evaluate("document.querySelector('.tt-lauf').scrollTop = 0")
        await foto(seite, "a-begruessung")
        text = await seite.inner_text(".tt-lauf")
        pruefe("Computerprogramm" in text and "kein Mensch" in text,
               "Begrüßung legt offen, dass es eine Maschine ist (EU-KI-Verordnung Art. 50)")
        pruefe(await seite.locator(".tt-kibanner").is_visible(),
               "Hinweisband bleibt dauerhaft sichtbar")

        # --- Schriftgrößen und Knopfhöhen --------------------------
        groesse = await seite.evaluate(
            "parseFloat(getComputedStyle(document.querySelector('.tt-blase')).fontSize)")
        pruefe(groesse >= 16, f"Grundschrift ist {groesse:.0f} px (mindestens 16 gefordert)")
        # Nur sichtbare Knöpfe messen: abgeräumte Auswahlblöcke stehen
        # noch im Dokument, haben aber keine Ausdehnung.
        hoehen = await seite.evaluate(
            "Array.from(document.querySelectorAll('.tt-wahl'))"
            ".filter(b => b.offsetParent !== null)"
            ".map(b => b.getBoundingClientRect().height)"
            ".filter(h => h > 0)")
        pruefe(all(h >= 44 for h in hoehen) if hoehen else True,
               f"alle Auswahlknöpfe mindestens 44 px hoch (kleinster: {min(hoehen):.0f} px)"
               if hoehen else "keine Knöpfe zu prüfen")

        # --- Klick-Interview ---------------------------------------
        await seite.click("button.tt-wahl:has-text('Schritt')")
        await seite.wait_for_selector(".tt-fortschritt", timeout=20000)
        await foto(seite, "b-interview-marke")
        marken = await seite.locator(".tt-knoepfe button.tt-wahl").all_inner_texts()
        pruefe(len(marken) > 3, f"Markenauswahl aus dem Bestand ({len(marken)} Einträge)")
        pruefe(any("(" in m for m in marken), "Auswahl zeigt die Stückzahl je Marke")

        ziel = next((m for m in marken if m.startswith("Opel")), marken[0])
        await seite.click(f".tt-knoepfe button.tt-wahl:has-text('{ziel.split()[0]}')")
        await seite.wait_for_timeout(1700)
        await foto(seite, "c-interview-modell")
        pruefe(await seite.locator("button.tt-wahl.tt-zurueck").count() > 0,
               "jeder Schritt hat einen Zurück-Knopf")

        for _ in range(4):
            knoepfe = seite.locator(".tt-knoepfe button.tt-wahl")
            anzahl = await knoepfe.count()
            if anzahl == 0:
                break
            gewaehlt = False
            for i in range(anzahl):
                klassen = await knoepfe.nth(i).get_attribute("class") or ""
                if "tt-zurueck" not in klassen:
                    await knoepfe.nth(i).click()
                    gewaehlt = True
                    break
            if not gewaehlt:
                break
            await seite.wait_for_timeout(1900)
            if await seite.locator(".tt-teil").count() > 0:
                break
        await seite.evaluate(
            "const l=document.querySelector('.tt-lauf');"
            "const t=document.querySelector('.tt-teil');"
            "if(t) l.scrollTop = t.offsetTop - 70;")
        await foto(seite, "g-interview-ergebnis")
        pruefe(await seite.locator(".tt-teil").count() > 0,
               "Klick-Interview endet bei echten Teilen")

        # --- Freitext in Laiensprache ------------------------------
        seite2 = await browser.new_page(viewport={"width": 1280, "height": 900},
                                        device_scale_factor=2)
        seite2.on("pageerror", lambda e: konsole.append(("pageerror", str(e))))
        await seite2.goto(args.demo)
        await seite2.wait_for_timeout(700)
        await seite2.click(".tt-knopf")
        await seite2.wait_for_selector(".tt-blase", timeout=20000)
        await seite2.wait_for_timeout(800)

        await seite2.fill(".tt-feld", "das rote Glas hinten links für meinen Golf V")
        await seite2.click(".tt-send")
        await seite2.wait_for_timeout(3200)
        await seite2.evaluate(
            "const l=document.querySelector('.tt-lauf');"
            "const t=document.querySelector('.tt-teil');"
            "if(t) l.scrollTop = Math.max(0, t.offsetTop - 150);")
        await foto(seite2, "h-vage-suche")
        text = await seite2.inner_text(".tt-lauf")
        pruefe("Rueckleuchte" in text or "Rückleuchte" in text,
               "Umschreibung mit 'rotes Glas hinten' findet die Rueckleuchte")

        # --- eBay-Weiterleitung ------------------------------------
        # Gesucht wird gezielt ein Teil, das der Shop ueber eBay
        # verkauft - sonst zeigt das Bild den Knopf nicht, um den es geht.
        await seite2.fill(".tt-feld", args.ebay_suche)
        await seite2.click(".tt-send")
        await seite2.wait_for_timeout(3200)
        anzahl_ebay = await seite2.locator("a.tt-ebay").count()
        pruefe(anzahl_ebay > 0, f"Suche nach {args.ebay_suche!r} findet ein Teil auf eBay")
        if anzahl_ebay:
            await seite2.locator("a.tt-ebay").first.scroll_into_view_if_needed()
            await seite2.wait_for_timeout(500)
            ziel_adresse = await seite2.locator("a.tt-ebay").first.get_attribute("href")
            pruefe(bool(ziel_adresse and "ebay." in ziel_adresse),
                   "eBay-Knopf führt zu einer eBay-Adresse")
            pruefe(await seite2.locator("a.tt-ebay").first.get_attribute("rel") ==
                   "noopener noreferrer", "eBay-Link öffnet sicher in neuem Fenster")
        await foto(seite2, "i-ebay")

        # --- Kunde fragt nach Betriebsdaten ------------------------
        await seite2.fill(".tt-feld", "Wie hoch war euer Umsatz letzten Monat?")
        await seite2.click(".tt-send")
        await seite2.wait_for_timeout(2500)
        await seite2.evaluate("const l=document.querySelector('.tt-lauf');l.scrollTop=l.scrollHeight")
        await foto(seite2, "j-kunde-blockiert")
        text = await seite2.inner_text(".tt-lauf")
        pruefe("keine Auskunft" in text, "Umsatzfrage eines Kunden wird abgelehnt")

        # --- Betriebsleitung ---------------------------------------
        await seite2.click(".tt-schloss")
        await seite2.wait_for_selector(".tt-adminform.tt-an")
        await seite2.wait_for_timeout(400)
        await foto(seite2, "k-admin-anmeldung")
        feldart = await seite2.locator("#tt-pw").get_attribute("type")
        pruefe(feldart == "password", "Passwortfeld zeigt die Eingabe nicht im Klartext")

        await seite2.fill("#tt-pw", "mit-sicherheit-falsch")
        await seite2.click(".tt-adminform .tt-send")
        await seite2.wait_for_timeout(1600)
        pruefe(await seite2.locator(".tt-adminfehler.tt-an").count() > 0,
               "falsches Passwort führt zu einer Fehlermeldung, nicht zur Anmeldung")

        await seite2.fill("#tt-pw", args.passwort)
        await seite2.click(".tt-adminform .tt-send")
        await seite2.wait_for_selector(".tt-adminbanner.tt-an", timeout=15000)
        await seite2.wait_for_timeout(1500)
        await foto(seite2, "l-betriebsleitung")
        text = await seite2.inner_text(".tt-lauf")
        pruefe(args.passwort not in text, "das Passwort erscheint NICHT im Gesprächsverlauf")
        pruefe("getrennt" in text, "getrennter Verlauf wird angekündigt")

        await seite2.fill(".tt-feld", "Wie hoch war der Umsatz letzten Monat?")
        await seite2.click(".tt-send")
        await seite2.wait_for_timeout(2600)
        await seite2.evaluate("const l=document.querySelector('.tt-lauf');l.scrollTop=l.scrollHeight")
        await foto(seite2, "m-betreiber-umsatz")
        text_admin = await seite2.inner_text(".tt-lauf")
        pruefe("Umsatz" in text_admin and "Auftr" in text_admin,
               "angemeldete Betriebsleitung erhält die Umsatzauskunft")

        await seite2.fill(".tt-feld", "Welche Suchen hatten keine Treffer?")
        await seite2.click(".tt-send")
        await seite2.wait_for_timeout(2600)
        await seite2.evaluate("const l=document.querySelector('.tt-lauf');l.scrollTop=l.scrollHeight")
        await foto(seite2, "n-nachfrageluecken")

        await seite2.click(".tt-adminbanner button")
        await seite2.wait_for_timeout(1300)
        text = await seite2.inner_text(".tt-lauf")
        pruefe("Auftr" not in text, "nach dem Abmelden ist der Zahlen-Verlauf verschwunden")
        pruefe("Rueckleuchte" in text or "Rückleuchte" in text or "keine Auskunft" in text,
               "der Kundenverlauf ist wieder da")

        # --- Tastaturbedienung -------------------------------------
        await seite2.keyboard.press("Escape")
        await seite2.wait_for_timeout(400)
        pruefe(not await seite2.locator(".tt-fenster").is_visible(),
               "Escape schließt das Fenster")

        # --- Handy -------------------------------------------------
        seite3 = await browser.new_page(viewport={"width": 390, "height": 844},
                                        device_scale_factor=3)
        await seite3.goto(args.demo)
        await seite3.wait_for_timeout(800)
        await seite3.click(".tt-knopf")
        await seite3.wait_for_selector(".tt-blase", timeout=20000)
        await seite3.wait_for_timeout(1400)
        await seite3.screenshot(path=str(bilder / "o-handy.png"))
        ueberlauf = await seite3.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth")
        pruefe(not ueberlauf, "auf dem Handy entsteht kein seitliches Scrollen")

        await browser.close()

    echte_fehler = [
        k for k in konsole
        if k[0] in ("error", "pageerror")
        and "favicon" not in k[1] and " 404 " not in k[1] and " 401 " not in k[1]
    ]
    pruefe(not echte_fehler, f"keine JavaScript-Fehler im Browser ({echte_fehler[:2]})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--demo", default="http://127.0.0.1:8080/demo.html")
    p.add_argument("--passwort", required=True)
    p.add_argument("--bilder", default="docs/bilder")
    p.add_argument("--browser", default="", help="Pfad zu einem Chromium, falls nötig")
    p.add_argument("--ebay-suche", default="Windschutzscheibe Ford Transit",
                   help="Suchbegriff, der ein Teil vom eBay-Marktplatz trifft")
    args = p.parse_args()

    asyncio.run(lauf(args))

    print("\n".join(hinweise))
    print("\n" + "=" * 60)
    if fehler:
        print(f"{len(fehler)} FEHLER:")
        for f in fehler:
            print("   -", f)
        return 1
    print(f"Alle {len(hinweise)} Oberflächenprüfungen bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
