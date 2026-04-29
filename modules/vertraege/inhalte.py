"""
Vertragsinhalte: Paragraphen-Generatoren für alle Vertragstypen.
Rechtsstand 2026 (BGB, NachwG, MiLoG, ArbZG, BUrlG).
"""
from datetime import datetime

from modules.vertraege.pdf_base import VertragPDF


def _format_datum_lang(datum_iso):
    """Formatiert ISO-Datum zu: 01. Februar 2026"""
    if not datum_iso:
        return ""
    try:
        if isinstance(datum_iso, str):
            d = datetime.strptime(datum_iso[:10], "%Y-%m-%d")
        else:
            d = datum_iso
        monate = [
            "",
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ]
        return f"{d.day:02d}. {monate[d.month]} {d.year}"
    except Exception:
        return str(datum_iso)


def _monate_text(n):
    worte = {
        1: "einen Monat",
        2: "zwei Monate",
        3: "drei Monate",
        4: "vier Monate",
        5: "fünf Monate",
        6: "sechs Monate",
    }
    return worte.get(n, f"{n} Monate")


def generate_vollzeit(betrieb, arbeitnehmer, daten, logo_bytes=None):
    """Arbeitsvertrag Vollzeit - kompletter rechtssicherer Vertrag."""
    pdf = VertragPDF("vollzeit", betrieb, arbeitnehmer, daten, logo_bytes)
    pdf.draw_cover()

    beginn = _format_datum_lang(daten.get("beginn"))
    probezeit_ende = _format_datum_lang(daten.get("probezeit_ende"))
    wochenstunden = daten.get("wochenstunden", 40)
    stundenlohn = daten.get("stundenlohn", "14,20")
    urlaubstage = daten.get("urlaubstage", 24)
    befristung = daten.get("befristung", False)
    befristung_bis = _format_datum_lang(daten.get("befristung_bis")) if befristung else ""
    taetigkeit = daten.get("taetigkeit", "")
    arbeitsort = daten.get("arbeitsort", betrieb.get("anschrift_ort", ""))

    # § 1 Beginn und Dauer
    body_1 = [
        (
            "sub",
            (
                "1",
                f"Das Arbeitsverhältnis beginnt am {beginn}. "
                + (
                    f"Es ist bis zum {befristung_bis} befristet."
                    if befristung
                    else "Es wird auf unbestimmte Zeit geschlossen."
                ),
            ),
        ),
    ]
    if daten.get("probezeit_monate", 6) > 0:
        monate = daten.get("probezeit_monate", 6)
        body_1.append(
            (
                "sub",
                (
                    "2",
                    f"Die ersten {_monate_text(monate)} des Arbeitsverhältnisses "
                    f"(bis zum {probezeit_ende}) gelten als Probezeit gemäß § 622 Abs. 3 BGB. "
                    f"Während der Probezeit kann das Arbeitsverhältnis von beiden Parteien "
                    f"mit einer Frist von zwei Wochen zu jedem beliebigen Tag gekündigt werden.",
                ),
            )
        )
    body_1.append(
        (
            "sub",
            (
                "3",
                "Nach Ablauf der Probezeit gelten die gesetzlichen Kündigungsfristen "
                "nach § 622 BGB.",
            ),
        )
    )
    pdf.paragraph(1, "Beginn und Dauer des Arbeitsverhältnisses", body_1)

    # § 2 Tätigkeit
    body_2 = [("p", "Die Arbeitnehmerin wird mit folgenden Aufgaben betraut:")]
    if taetigkeit:
        for t in taetigkeit.split("\n"):
            t = t.strip()
            if t:
                body_2.append(("bullet", t))
    body_2.append(
        (
            "p",
            f"Der Arbeitgeber behält sich vor, der Arbeitnehmerin nach pflichtgemäßem Ermessen "
            f"auch andere, ihren Fähigkeiten und Kenntnissen entsprechende, zumutbare Tätigkeiten "
            f"zu übertragen. Der Tätigkeitsort ist {arbeitsort}.",
        )
    )
    pdf.paragraph(2, "Tätigkeit", body_2)

    # § 3 Arbeitszeit
    body_3 = [
        (
            "sub",
            (
                "1",
                f"Die regelmäßige wöchentliche Arbeitszeit beträgt {wochenstunden} Stunden, "
                f"verteilt auf 5 Arbeitstage pro Woche (Montag bis Freitag) oder nach "
                f"betrieblicher Vereinbarung auch an anderen Wochentagen.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Die Lage der Arbeitszeit wird vom Arbeitgeber entsprechend dem "
                "Arbeitsanfall festgelegt. Der Arbeitgeber teilt der Arbeitnehmerin die "
                "Lage ihrer Arbeitszeit jeweils mindestens 4 Tage im Voraus mit.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Gesetzliche Ruhepausen werden gewährt: bei einer Arbeitszeit von mehr "
                "als 6 Stunden mindestens 30 Minuten, bei mehr als 9 Stunden mindestens "
                "45 Minuten (§ 4 ArbZG). Nach Beendigung der täglichen Arbeitszeit wird "
                "eine ununterbrochene Ruhezeit von mindestens 11 Stunden gewährleistet "
                "(§ 5 ArbZG).",
            ),
        ),
        (
            "sub",
            (
                "4",
                "Die Anordnung von Überstunden ist bei betrieblicher Notwendigkeit "
                "zulässig. Überstunden werden dem Arbeitszeitkonto gutgeschrieben und "
                "können durch Freizeit oder Vergütung ausgeglichen werden.",
            ),
        ),
    ]
    pdf.paragraph(3, "Arbeitszeit", body_3)

    # § 4 Vergütung
    try:
        monatslohn_berechnet = float(str(stundenlohn).replace(",", ".")) * wochenstunden * 4.33
    except (ValueError, TypeError):
        monatslohn_berechnet = 0
    body_4 = [
        (
            "sub",
            (
                "1",
                f"Die Vergütung beträgt {stundenlohn} € brutto pro Stunde. "
                f"Der Mindestlohn nach MiLoG wird stets eingehalten.",
            ),
        ),
        (
            "sub",
            (
                "2",
                f"Bei {wochenstunden} Wochenstunden ergibt sich ein durchschnittlicher "
                f"monatlicher Bruttolohn von ca. {monatslohn_berechnet:.2f} €. "
                f"Der tatsächliche Monatslohn ergibt sich aus dem Stundenlohn multipliziert "
                f"mit den geleisteten Arbeitsstunden.",
            ),
        ),
        (
            "sub",
            (
                "3",
                f"Die Auszahlung erfolgt jeweils zum "
                f"{daten.get('auszahlung_tag', 15)}. des Folgemonats, spätestens jedoch "
                f"bis zum nächsten Werktag. Die Zahlung erfolgt bargeldlos auf das von "
                f"der Arbeitnehmerin benannte Konto.",
            ),
        ),
    ]
    if daten.get("abschlag", 0):
        body_4.append(
            (
                "sub",
                (
                    "4",
                    f"Die Arbeitnehmerin erhält zusätzlich eine monatliche Abschlagszahlung "
                    f"in Höhe von {daten['abschlag']} € netto, die spätestens bis zum "
                    f"{daten.get('abschlag_tag', 3)}. Werktag des laufenden Monats ausgezahlt wird. "
                    f"Der Abschlag wird bei der Endabrechnung verrechnet.",
                ),
            )
        )
    pdf.paragraph(4, "Vergütung", body_4)

    # § 5 Urlaub
    body_5 = [
        (
            "p",
            f"Die Arbeitnehmerin hat Anspruch auf einen jährlichen Erholungsurlaub von "
            f"{urlaubstage} Arbeitstagen. Die Urlaubsberechnung erfolgt auf Basis einer "
            f"5-Tage-Woche. Im Übrigen gelten die Bestimmungen des Bundesurlaubsgesetzes (BUrlG). "
            f"Der gesetzliche Mindesturlaub beträgt 20 Arbeitstage (§ 3 BUrlG).",
        ),
    ]
    pdf.paragraph(5, "Urlaub", body_5)

    # § 6 Arbeitsunfähigkeit
    body_6 = [
        (
            "sub",
            (
                "1",
                "Die Arbeitnehmerin ist verpflichtet, jede Arbeitsunfähigkeit und deren "
                "voraussichtliche Dauer unverzüglich mitzuteilen. Dauert die Arbeitsunfähigkeit "
                "länger als drei Kalendertage, ist bis spätestens am darauffolgenden Arbeitstag "
                "eine ärztliche Bescheinigung vorzulegen.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Bei Arbeitsunfähigkeit infolge Krankheit besteht Anspruch auf "
                "Entgeltfortzahlung nach Maßgabe des Entgeltfortzahlungsgesetzes (EFZG) "
                "bis zu sechs Wochen.",
            ),
        ),
    ]
    pdf.paragraph(6, "Arbeitsunfähigkeit", body_6)

    # § 7 Arbeitszeitkonto
    body_7 = [
        (
            "sub",
            (
                "1",
                "Für die Arbeitnehmerin wird ein Arbeitszeitkonto geführt. Plus- und "
                "Minusstunden werden erfasst und bis zum 31. März des Folgejahres "
                "durch Freizeit oder Vergütung ausgeglichen.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Nach § 2 Abs. 2 MiLoG dürfen Plusstunden monatlich höchstens 50 % der "
                "vereinbarten Sollarbeitszeit betragen.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Bei Beendigung des Arbeitsverhältnisses werden Plusstunden mit dem "
                "regulären Stundensatz ausgezahlt.",
            ),
        ),
    ]
    pdf.paragraph(7, "Arbeitszeitkonto", body_7)

    # § 8 Verschwiegenheit (optional)
    if betrieb.get("verschwiegenheit", True):
        body_8 = [
            (
                "sub",
                (
                    "1",
                    "Die Arbeitnehmerin ist verpflichtet, über alle ihr im Rahmen ihrer "
                    "Tätigkeit bekannt gewordenen Betriebs- und Geschäftsgeheimnisse "
                    "sowie vertrauliche betriebsinterne Angelegenheiten gegenüber Dritten "
                    "Stillschweigen zu bewahren.",
                ),
            ),
            (
                "sub",
                (
                    "2",
                    "Die Arbeitnehmerin ist darüber hinaus verpflichtet, über die Höhe "
                    "ihrer Vergütung gegenüber Dritten - einschließlich Arbeitskollegen - "
                    "Stillschweigen zu bewahren.",
                ),
            ),
            (
                "sub",
                (
                    "3",
                    "Die Verschwiegenheitspflicht gilt sowohl während als auch nach "
                    "Beendigung des Arbeitsverhältnisses.",
                ),
            ),
        ]
        pdf.paragraph(8, "Verschwiegenheitspflicht", body_8)

    # § 9 Nebentätigkeit
    body_9 = [
        (
            "p",
            "Eine Nebentätigkeit der Arbeitnehmerin ist dem Arbeitgeber vor Aufnahme "
            "schriftlich anzuzeigen. Der Arbeitgeber kann die Nebentätigkeit untersagen, "
            "wenn berechtigte betriebliche Interessen entgegenstehen.",
        ),
    ]
    pdf.paragraph(9, "Nebentätigkeit", body_9)

    # § 10 Schlussbestimmungen
    body_10 = [
        (
            "sub",
            (
                "1",
                "Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen "
                "dieses Vertrages bedürfen zu ihrer Wirksamkeit der Textform.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Sollten einzelne Bestimmungen dieses Vertrages unwirksam sein oder "
                "werden, so wird hierdurch die Wirksamkeit der übrigen Bestimmungen "
                "nicht berührt.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Hinweis zum Kündigungsschutz: Möchte die Arbeitnehmerin die Unwirksamkeit "
                "einer Kündigung geltend machen, muss sie innerhalb von drei Wochen nach "
                "Zugang der schriftlichen Kündigung Klage beim zuständigen Arbeitsgericht "
                "erheben (§ 4 KSchG). Versäumt sie diese Frist, gilt die Kündigung gemäß "
                "§ 7 KSchG als von Anfang an rechtswirksam.",
            ),
        ),
    ]
    pdf.paragraph(10, "Schlussbestimmungen", body_10)

    pdf.signature_section()
    return pdf.save()


def generate_teilzeit(betrieb, arbeitnehmer, daten, logo_bytes=None):
    """Arbeitsvertrag Teilzeit - monatliche Sollstunden."""
    pdf = VertragPDF("teilzeit", betrieb, arbeitnehmer, daten, logo_bytes)
    pdf.draw_cover()

    beginn = _format_datum_lang(daten.get("beginn"))
    probezeit_ende = _format_datum_lang(daten.get("probezeit_ende"))
    monatsstunden = daten.get("monatsstunden", 80)
    stundenlohn = daten.get("stundenlohn", "14,20")
    urlaubstage = daten.get("urlaubstage", 20)
    taetigkeit = daten.get("taetigkeit", "")
    arbeitsort = daten.get("arbeitsort", betrieb.get("anschrift_ort", ""))

    body_1 = [
        (
            "sub",
            (
                "1",
                f"Das Arbeitsverhältnis beginnt am {beginn} und wird in Teilzeit auf "
                f"unbestimmte Zeit geschlossen.",
            ),
        ),
    ]
    if daten.get("probezeit_monate", 6) > 0:
        monate = daten.get("probezeit_monate", 6)
        body_1.append(
            (
                "sub",
                (
                    "2",
                    f"Die ersten {_monate_text(monate)} (bis zum {probezeit_ende}) "
                    f"gelten als Probezeit gemäß § 622 Abs. 3 BGB mit einer "
                    f"Kündigungsfrist von zwei Wochen.",
                ),
            )
        )
    pdf.paragraph(1, "Beginn und Dauer", body_1)

    body_2 = [("p", "Die Arbeitnehmerin wird mit folgenden Aufgaben betraut:")]
    if taetigkeit:
        for t in taetigkeit.split("\n"):
            t = t.strip()
            if t:
                body_2.append(("bullet", t))
    body_2.append(
        (
            "p",
            f"Tätigkeitsort ist {arbeitsort}. Der Arbeitgeber kann nach "
            f"pflichtgemäßem Ermessen auch andere zumutbare Tätigkeiten übertragen.",
        )
    )
    pdf.paragraph(2, "Tätigkeit", body_2)

    body_3 = [
        (
            "sub",
            (
                "1",
                f"Die monatliche Sollarbeitszeit beträgt {monatsstunden} Stunden. "
                f"Die Verteilung erfolgt nach Absprache zwischen Arbeitgeber und Arbeitnehmerin.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Die Lage der Arbeitszeit wird vom Arbeitgeber entsprechend dem "
                "Arbeitsanfall festgelegt und mindestens 4 Tage im Voraus mitgeteilt. "
                "In Krankheitsfällen oder anderen betrieblichen Notfällen kann eine "
                "kurzfristige Änderung erfolgen.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Gesetzliche Ruhepausen und Ruhezeiten werden gewährt (§§ 4, 5 ArbZG). "
                "Bei mehr als 6 Stunden Arbeitszeit: mindestens 30 Minuten Pause; "
                "bei mehr als 9 Stunden: mindestens 45 Minuten.",
            ),
        ),
        (
            "sub",
            (
                "4",
                "Die monatliche Sollarbeitszeit kann bei betrieblicher Notwendigkeit "
                "überschritten werden. Mehrarbeitsstunden werden dem Arbeitszeitkonto "
                "gutgeschrieben.",
            ),
        ),
    ]
    pdf.paragraph(3, "Arbeitszeit", body_3)

    body_4 = [
        (
            "sub",
            (
                "1",
                f"Die Vergütung beträgt {stundenlohn} € brutto pro Stunde. "
                f"Der gesetzliche Mindestlohn wird stets eingehalten.",
            ),
        ),
        (
            "sub",
            (
                "2",
                f"Der monatliche Bruttolohn ergibt sich aus dem Stundenlohn multipliziert "
                f"mit den tatsächlich geleisteten Arbeitsstunden entsprechend der "
                f"vereinbarten monatlichen Sollarbeitszeit von {monatsstunden} Stunden.",
            ),
        ),
        (
            "sub",
            (
                "3",
                f"Die Auszahlung erfolgt zum {daten.get('auszahlung_tag', 15)}. des "
                f"Folgemonats auf das von der Arbeitnehmerin benannte Konto.",
            ),
        ),
    ]
    if daten.get("abschlag", 0):
        body_4.append(
            (
                "sub",
                (
                    "4",
                    f"Die Arbeitnehmerin erhält zusätzlich eine monatliche Abschlagszahlung "
                    f"in Höhe von {daten['abschlag']} € netto, ausgezahlt bis zum "
                    f"{daten.get('abschlag_tag', 3)}. Werktag des laufenden Monats. "
                    f"Der Abschlag wird bei der Endabrechnung verrechnet.",
                ),
            )
        )
    pdf.paragraph(4, "Vergütung", body_4)

    body_5 = [
        (
            "p",
            f"Die Arbeitnehmerin hat Anspruch auf einen jährlichen Erholungsurlaub von "
            f"{urlaubstage} Arbeitstagen. Bei Teilzeit erfolgt die anteilige Berechnung "
            f"entsprechend der vereinbarten Arbeitstage pro Woche. Im Übrigen gelten die "
            f"Bestimmungen des Bundesurlaubsgesetzes.",
        ),
    ]
    pdf.paragraph(5, "Urlaub", body_5)

    body_6 = [
        (
            "sub",
            (
                "1",
                "Jede Arbeitsunfähigkeit und ihre voraussichtliche Dauer ist unverzüglich "
                "mitzuteilen. Eine ärztliche Bescheinigung ist ab dem 4. Krankheitstag "
                "vorzulegen.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Bei Krankheit besteht Anspruch auf Entgeltfortzahlung nach EFZG bis zu "
                "sechs Wochen.",
            ),
        ),
    ]
    pdf.paragraph(6, "Arbeitsunfähigkeit", body_6)

    body_7 = [
        (
            "sub",
            (
                "1",
                f"Plus- und Minusstunden werden auf einem Arbeitszeitkonto erfasst. "
                f"Nach § 2 Abs. 2 MiLoG dürfen Plusstunden monatlich höchstens 50 % "
                f"der Sollarbeitszeit (max. {int(monatsstunden * 0.5)} Std.) betragen.",
            ),
        ),
        (
            "sub",
            ("2", "Minusstunden dürfen den Betrag von 20 Stunden nicht überschreiten."),
        ),
        (
            "sub",
            (
                "3",
                "Der Ausgleichszeitraum beträgt 12 Monate. Plus-/Minusstunden sind bis "
                "zum 31. März des Folgejahres auszugleichen.",
            ),
        ),
        (
            "sub",
            (
                "4",
                f"Bei Beendigung des Arbeitsverhältnisses werden Plusstunden mit dem "
                f"regulären Stundensatz von {stundenlohn} € ausgezahlt.",
            ),
        ),
    ]
    pdf.paragraph(7, "Arbeitszeitkonto", body_7)

    if betrieb.get("verschwiegenheit", True):
        body_8 = [
            (
                "sub",
                (
                    "1",
                    "Die Arbeitnehmerin ist verpflichtet, über Betriebs- und "
                    "Geschäftsgeheimnisse gegenüber Dritten Stillschweigen zu bewahren.",
                ),
            ),
            (
                "sub",
                (
                    "2",
                    "Die Verschwiegenheitspflicht gilt auch über die Vergütungshöhe "
                    "gegenüber Kollegen und Dritten.",
                ),
            ),
            (
                "sub",
                ("3", "Die Pflicht besteht auch nach Beendigung des Arbeitsverhältnisses fort."),
            ),
        ]
        pdf.paragraph(8, "Verschwiegenheitspflicht", body_8)

    body_9 = [
        (
            "sub",
            ("1", "Mündliche Nebenabreden bestehen nicht. Änderungen bedürfen der Textform."),
        ),
        (
            "sub",
            (
                "2",
                "Sollten einzelne Bestimmungen unwirksam sein, bleibt die Wirksamkeit "
                "der übrigen Bestimmungen unberührt.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Zum Kündigungsschutz: Innerhalb von drei Wochen nach Zugang einer "
                "schriftlichen Kündigung muss Klage beim Arbeitsgericht erhoben werden "
                "(§ 4 KSchG), sonst gilt die Kündigung als wirksam (§ 7 KSchG).",
            ),
        ),
    ]
    pdf.paragraph(9, "Schlussbestimmungen", body_9)

    pdf.signature_section()
    return pdf.save()


def generate_minijob(betrieb, arbeitnehmer, daten, logo_bytes=None):
    """Minijob-Vertrag (geringfügige Beschäftigung)."""
    pdf = VertragPDF("minijob", betrieb, arbeitnehmer, daten, logo_bytes)
    pdf.draw_cover()

    beginn = _format_datum_lang(daten.get("beginn"))
    stundenlohn = daten.get("stundenlohn", "14,20")
    wochenstunden = daten.get("wochenstunden", "nach Absprache")
    urlaubstage = daten.get("urlaubstage", 20)
    taetigkeit = daten.get("taetigkeit", "")
    arbeitsort = daten.get("arbeitsort", betrieb.get("anschrift_ort", ""))

    body_1 = [
        ("sub", ("1", f"Das Arbeitsverhältnis beginnt am {beginn}.")),
        (
            "sub",
            (
                "2",
                "Es handelt sich um eine geringfügig entlohnte Beschäftigung gemäß "
                "§ 8 Abs. 1 Nr. 1 SGB IV (Minijob). Das monatliche Arbeitsentgelt "
                "überschreitet die Geringfügigkeitsgrenze nicht.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Die Arbeitnehmerin versichert, dass sie durch diese Tätigkeit "
                "zusammen mit anderen geringfügigen Beschäftigungen die "
                "Geringfügigkeitsgrenze nicht überschreitet. Eine Änderung ist "
                "unverzüglich anzuzeigen.",
            ),
        ),
    ]
    pdf.paragraph(1, "Beginn und Art der Beschäftigung", body_1)

    body_2 = [("p", "Die Arbeitnehmerin wird mit folgenden Aufgaben betraut:")]
    if taetigkeit:
        for t in taetigkeit.split("\n"):
            t = t.strip()
            if t:
                body_2.append(("bullet", t))
    body_2.append(("p", f"Tätigkeitsort ist {arbeitsort}."))
    pdf.paragraph(2, "Tätigkeit", body_2)

    body_3 = [
        (
            "sub",
            (
                "1",
                f"Die wöchentliche Arbeitszeit beträgt {wochenstunden}. "
                f"Die Verteilung erfolgt nach Absprache.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Gesetzliche Ruhepausen werden gewährt (§ 4 ArbZG). "
                "Bei mehr als 6 Stunden Arbeitszeit: mindestens 30 Minuten Pause.",
            ),
        ),
    ]
    pdf.paragraph(3, "Arbeitszeit", body_3)

    body_4 = [
        (
            "sub",
            (
                "1",
                f"Die Vergütung beträgt {stundenlohn} € brutto pro Stunde. "
                f"Der gesetzliche Mindestlohn nach MiLoG wird stets eingehalten.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Das monatliche Arbeitsentgelt darf die Geringfügigkeitsgrenze "
                "(2026: voraussichtlich 556 €) nicht überschreiten. Gelegentliches "
                "unvorhersehbares Überschreiten bis zum zweifachen Betrag ist in "
                "maximal 2 Monaten pro Jahr möglich.",
            ),
        ),
        (
            "sub",
            (
                "3",
                f"Die Auszahlung erfolgt zum {daten.get('auszahlung_tag', 15)}. des "
                f"Folgemonats auf das von der Arbeitnehmerin benannte Konto.",
            ),
        ),
    ]
    pdf.paragraph(4, "Vergütung", body_4)

    body_5 = [
        (
            "sub",
            (
                "1",
                "Die Beiträge zur Kranken-, Pflege-, Renten- und Arbeitslosenversicherung "
                "trägt der Arbeitgeber in Form einer Pauschalabgabe an die Minijob-Zentrale "
                "(Deutsche Rentenversicherung Knappschaft-Bahn-See).",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Die Arbeitnehmerin ist in der Rentenversicherung pflichtversichert und "
                "zahlt einen Eigenanteil zur Aufstockung auf den vollen RV-Beitrag. "
                "Sie kann sich auf Antrag von der Rentenversicherungspflicht befreien "
                "lassen (unwiderruflich für die Dauer der Beschäftigung).",
            ),
        ),
    ]
    pdf.paragraph(5, "Sozialversicherung", body_5)

    body_6 = [
        (
            "p",
            f"Die Arbeitnehmerin hat Anspruch auf Erholungsurlaub. Der Urlaubsanspruch "
            f"beträgt bei voller Beschäftigungszeit {urlaubstage} Arbeitstage pro Jahr "
            f"und berechnet sich anteilig entsprechend der tatsächlichen Wochenarbeitstage "
            f"nach BUrlG.",
        ),
    ]
    pdf.paragraph(6, "Urlaub", body_6)

    body_7 = [
        (
            "p",
            "Bei Krankheit besteht Anspruch auf Entgeltfortzahlung nach EFZG bis zu sechs "
            "Wochen. Die Arbeitsunfähigkeit ist unverzüglich anzuzeigen, eine ärztliche "
            "Bescheinigung ist ab dem 4. Krankheitstag vorzulegen.",
        ),
    ]
    pdf.paragraph(7, "Arbeitsunfähigkeit", body_7)

    body_8 = [
        (
            "p",
            "Für die Kündigung gelten die gesetzlichen Bestimmungen nach § 622 BGB. "
            "Während der Probezeit (die ersten 6 Monate) kann das Arbeitsverhältnis mit "
            "einer Frist von 2 Wochen gekündigt werden.",
        ),
    ]
    pdf.paragraph(8, "Kündigung", body_8)

    if betrieb.get("verschwiegenheit", True):
        body_9 = [
            (
                "p",
                "Die Arbeitnehmerin ist verpflichtet, über Betriebs- und Geschäftsgeheimnisse "
                "sowie über die Höhe ihrer Vergütung gegenüber Dritten Stillschweigen zu bewahren. "
                "Diese Pflicht besteht auch nach Beendigung des Arbeitsverhältnisses fort.",
            ),
        ]
        pdf.paragraph(9, "Verschwiegenheitspflicht", body_9)

    body_10 = [
        (
            "sub",
            ("1", "Änderungen bedürfen der Textform. Mündliche Nebenabreden bestehen nicht."),
        ),
        (
            "sub",
            (
                "2",
                "Bei Unwirksamkeit einzelner Bestimmungen bleibt der Vertrag im Übrigen wirksam.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Kündigungsschutzklagen müssen gem. § 4 KSchG innerhalb 3 Wochen nach "
                "Kündigungszugang beim Arbeitsgericht erhoben werden.",
            ),
        ),
    ]
    pdf.paragraph(10, "Schlussbestimmungen", body_10)

    pdf.signature_section()
    return pdf.save()


def generate_aenderungsvertrag(betrieb, arbeitnehmer, daten, logo_bytes=None):
    """Änderungsvertrag - nur die geänderten Paragraphen."""
    pdf = VertragPDF("aenderungsvertrag", betrieb, arbeitnehmer, daten, logo_bytes)
    pdf.draw_cover()

    inkrafttreten = _format_datum_lang(daten.get("inkrafttreten"))
    urspruenglich = _format_datum_lang(daten.get("urspruenglicher_vertrag_datum"))

    body_1 = [
        (
            "p",
            f"Die nachfolgenden Änderungen treten mit Wirkung zum {inkrafttreten} in Kraft "
            f"und ersetzen die bisherigen Regelungen der entsprechenden Paragrafen des "
            f"Arbeitsvertrages vom {urspruenglich}.",
        ),
    ]
    pdf.paragraph(1, "Inkrafttreten der Änderungen", body_1)

    paragraph_nr = 2

    if daten.get("aendere_arbeitszeit"):
        wochenstunden = daten.get("neue_wochenstunden", 40)
        monatsstunden = daten.get("neue_monatsstunden")
        body = []
        if monatsstunden:
            body.append(
                ("sub", ("1", f"Die monatliche Sollarbeitszeit beträgt {monatsstunden} Stunden."))
            )
        else:
            body.append(
                ("sub", ("1", f"Die wöchentliche Arbeitszeit beträgt {wochenstunden} Stunden."))
            )
        body.append(
            (
                "sub",
                (
                    "2",
                    "Die Lage der Arbeitszeit wird vom Arbeitgeber entsprechend dem "
                    "Arbeitsanfall festgelegt und mindestens 4 Tage im Voraus mitgeteilt.",
                ),
            )
        )
        body.append(
            (
                "sub",
                (
                    "3",
                    "Gesetzliche Ruhepausen werden gewährt: mindestens 30 Minuten bei "
                    "mehr als 6 Stunden, 45 Minuten bei mehr als 9 Stunden (§ 4 ArbZG).",
                ),
            )
        )
        pdf.paragraph(paragraph_nr, "Arbeitszeit", body)
        paragraph_nr += 1

    if daten.get("aendere_verguetung"):
        stundenlohn = daten.get("neuer_stundenlohn", "14,20")
        body = [
            (
                "sub",
                (
                    "1",
                    f"Die Vergütung beträgt {stundenlohn} € brutto pro Stunde. "
                    f"Der gesetzliche Mindestlohn wird stets eingehalten.",
                ),
            ),
            (
                "sub",
                (
                    "2",
                    f"Die Auszahlung erfolgt zum {daten.get('auszahlung_tag', 15)}. des "
                    f"Folgemonats auf das von der Arbeitnehmerin benannte Konto.",
                ),
            ),
        ]
        if daten.get("neuer_abschlag"):
            body.append(
                (
                    "sub",
                    (
                        "3",
                        f"Die Arbeitnehmerin erhält eine monatliche Abschlagszahlung "
                        f"in Höhe von {daten['neuer_abschlag']} € netto, ausgezahlt bis "
                        f"zum {daten.get('abschlag_tag', 3)}. Werktag.",
                    ),
                )
            )
        pdf.paragraph(paragraph_nr, "Vergütung", body)
        paragraph_nr += 1

    if daten.get("aendere_urlaub"):
        body = [
            (
                "p",
                f"Die Arbeitnehmerin hat Anspruch auf einen jährlichen Erholungsurlaub von "
                f"{daten.get('neue_urlaubstage', 24)} Arbeitstagen. Im Übrigen gelten die "
                f"Bestimmungen des Bundesurlaubsgesetzes.",
            ),
        ]
        pdf.paragraph(paragraph_nr, "Urlaub", body)
        paragraph_nr += 1

    if daten.get("aendere_taetigkeit"):
        body = [("p", "Die Arbeitnehmerin wird künftig mit folgenden Aufgaben betraut:")]
        for t in daten.get("neue_taetigkeit", "").split("\n"):
            t = t.strip()
            if t:
                body.append(("bullet", t))
        pdf.paragraph(paragraph_nr, "Tätigkeit", body)
        paragraph_nr += 1

    if daten.get("aendere_probezeit"):
        body = [
            (
                "p",
                f"Die Probezeit wird {daten.get('probezeit_aenderung', 'beendet')}. "
                f"Ab dem {inkrafttreten} gelten die gesetzlichen Kündigungsfristen nach § 622 BGB.",
            ),
        ]
        pdf.paragraph(paragraph_nr, "Probezeit", body)
        paragraph_nr += 1

    body_end = [
        (
            "sub",
            (
                "1",
                "Alle nicht durch diesen Änderungsvertrag ausdrücklich geänderten "
                "Bestimmungen des ursprünglichen Arbeitsvertrages bleiben unverändert in Kraft.",
            ),
        ),
        (
            "sub",
            (
                "2",
                "Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen dieses "
                "Vertrages bedürfen zu ihrer Wirksamkeit der Textform.",
            ),
        ),
        (
            "sub",
            (
                "3",
                "Sollten einzelne Bestimmungen dieses Änderungsvertrages unwirksam sein "
                "oder werden, so wird hierdurch die Wirksamkeit der übrigen Bestimmungen "
                "nicht berührt.",
            ),
        ),
    ]
    pdf.paragraph(paragraph_nr, "Schlussbestimmungen", body_end)

    pdf.signature_section()
    return pdf.save()


# Haupt-API
VERTRAGSTYPEN = {
    "vollzeit": {
        "name": "Arbeitsvertrag Vollzeit",
        "beschreibung": "Unbefristetes oder befristetes Arbeitsverhältnis in Vollzeit (35-40 Std/Woche)",
        "generator": generate_vollzeit,
    },
    "teilzeit": {
        "name": "Arbeitsvertrag Teilzeit",
        "beschreibung": "Teilzeitbeschäftigung mit festen monatlichen Sollstunden",
        "generator": generate_teilzeit,
    },
    "minijob": {
        "name": "Minijob-Vertrag",
        "beschreibung": "Geringfügige Beschäftigung (bis 556 €/Monat) nach § 8 SGB IV",
        "generator": generate_minijob,
    },
    "aenderungsvertrag": {
        "name": "Änderungsvertrag",
        "beschreibung": "Änderung bestehender Vertragsparagraphen (Arbeitszeit, Vergütung, Urlaub etc.)",
        "generator": generate_aenderungsvertrag,
    },
}

