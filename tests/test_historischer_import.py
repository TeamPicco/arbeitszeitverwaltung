from datetime import date
from pathlib import Path
import tempfile

from utils.historischer_import import dry_run_import_summary, importiere_in_crewbase, lese_csv_datei


class FakeResponse:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class FakeQuery:
    def __init__(self, table: "FakeTable"):
        self.table = table
        self._filters = []
        self._limit = None
        self._insert_payload = None
        self._update_payload = None
        self._delete_mode = False

    def select(self, columns):
        return self

    def eq(self, key, value):
        self._filters.append(("eq", key, value))
        return self

    def gte(self, key, value):
        self._filters.append(("gte", key, value))
        return self

    def lte(self, key, value):
        self._filters.append(("lte", key, value))
        return self

    def limit(self, value):
        self._limit = value
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def delete(self):
        self._delete_mode = True
        return self

    def execute(self):
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            if "id" not in payload:
                payload["id"] = len(self.table.rows) + 1
            self.table.rows.append(payload)
            self.table.last_insert_payload = payload
            return FakeResponse([payload])

        if self._update_payload is not None:
            rows = self._filtered_rows()
            for row in rows:
                row.update(self._update_payload)
            return FakeResponse(rows)

        if self._delete_mode:
            rows = self._filtered_rows()
            self.table.rows = [r for r in self.table.rows if r not in rows]
            return FakeResponse(rows)

        rows = self._filtered_rows()
        if self._limit is not None:
            rows = rows[: self._limit]
        return FakeResponse(rows)

    def _filtered_rows(self):
        out = []
        for row in self.table.rows:
            if self._match_row(row):
                out.append(row)
        return out

    def _match_row(self, row):
        for op, key, value in self._filters:
            rv = row.get(key)
            if op == "eq" and rv != value:
                return False
            if op == "gte" and rv < value:
                return False
            if op == "lte" and rv > value:
                return False
        return True


class FakeTable:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.last_insert_payload = None
        self.raise_on_insert_msg = None

    def select(self, columns):
        return FakeQuery(self).select(columns)

    def insert(self, payload):
        if self.raise_on_insert_msg:
            msg = self.raise_on_insert_msg
            self.raise_on_insert_msg = None
            raise Exception(msg)
        return FakeQuery(self).insert(payload)

    def update(self, payload):
        return FakeQuery(self).update(payload)

    def delete(self):
        return FakeQuery(self).delete()

    def upsert(self, payload, on_conflict=None):
        # Für Tests reicht insert-ähnliches Verhalten.
        return FakeQuery(self).insert(payload)


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "mitarbeiter": FakeTable(
                [
                    {
                        "id": 1,
                        "eintrittsdatum": "2020-01-01",
                        "monatliche_soll_stunden": 160.0,
                        "stundenlohn_brutto": 15.0,
                        "jahres_urlaubstage": 28.0,
                        "resturlaub_vorjahr": 0.0,
                    }
                ]
            ),
            "zeiterfassung": FakeTable([]),
            "arbeitszeitkonto": FakeTable([]),
            "krankheitstage": FakeTable([]),
            "krankheit_episoden": FakeTable([]),
            "vertraege": FakeTable([]),
            "abwesenheiten": FakeTable([]),
            "azk_monatsabschluesse": FakeTable([]),
            "arbeitszeit_konten": FakeTable([]),
            "ueberstunden_korrekturen": FakeTable([]),
        }

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable([])
        return self.tables[name]


def test_import_triggers_work_account_resync():
    supabase = FakeSupabase()
    daten = {
        "zeitraum": {"monat": 2, "jahr": 2026, "bis": date(2026, 2, 28)},
        "startsaldo": 0.0,
        "tage": [
            {
                "datum": date(2026, 2, 4),
                "wochentag": "Mi",
                "soll": 8.0,
                "plan": 8.0,
                "ist": 8.0,
                "abwesend": 0.0,
                "saldo": 0.0,
                "korrektur": 0.0,
                "korrektur_notiz": "",
                "laufender_saldo": 0.0,
                "std_konto": 0.0,
                "lohn": 120.0,
                "ist_ruhetag": False,
                "ist_korrekturzeile": False,
                "ist_krank": False,
            }
        ],
    }

    result = importiere_in_crewbase(
        daten,
        mitarbeiter_id=1,
        betrieb_id=1,
        supabase_client=supabase,
        ueberschreiben=False,
    )

    assert result["ok"] is True
    assert result["importiert"] >= 1
    assert result.get("azk_sync_monate", 0) >= 1


def test_import_month_overwrite_removes_existing_entries():
    supabase = FakeSupabase()
    # Vorhandener Eintrag im Import-Monat
    supabase.table("zeiterfassung").rows.append(
        {
            "id": 77,
            "mitarbeiter_id": 1,
            "datum": "2026-01-10",
            "quelle": "historischer_import",
            "arbeitsstunden": 4.0,
        }
    )
    # Vorhandener Eintrag außerhalb des Import-Monats (muss erhalten bleiben)
    supabase.table("zeiterfassung").rows.append(
        {
            "id": 88,
            "mitarbeiter_id": 1,
            "datum": "2026-03-10",
            "quelle": "historischer_import",
            "arbeitsstunden": 5.0,
        }
    )

    daten = {
        "zeitraum": {
            "von": date(2026, 1, 1),
            "bis": date(2026, 1, 31),
            "monat": 1,
            "jahr": 2026,
        },
        "startsaldo": 0.0,
        "tage": [
            {
                "datum": date(2026, 1, 15),
                "wochentag": "Do",
                "soll": 8.0,
                "plan": 8.0,
                "ist": 8.0,
                "abwesend": 0.0,
                "saldo": 0.0,
                "korrektur": 0.0,
                "korrektur_notiz": "",
                "laufender_saldo": 0.0,
                "std_konto": 0.0,
                "lohn": 120.0,
                "ist_ruhetag": False,
                "ist_korrekturzeile": False,
                "ist_krank": False,
            }
        ],
    }

    result = importiere_in_crewbase(
        daten,
        mitarbeiter_id=1,
        betrieb_id=1,
        supabase_client=supabase,
        ueberschreiben=True,
    )

    assert result["ok"] is True
    jan_rows = [r for r in supabase.table("zeiterfassung").rows if str(r.get("datum", "")).startswith("2026-01-")]
    mar_rows = [r for r in supabase.table("zeiterfassung").rows if str(r.get("datum", "")).startswith("2026-03-")]
    # Januar wurde überschrieben und neu aufgebaut (kein Alt-Duplikat).
    assert len(jan_rows) >= 1
    assert all(r.get("id") != 77 for r in jan_rows)
    # März-Eintrag bleibt unberührt.
    assert any(r.get("id") == 88 for r in mar_rows)


def test_dry_run_counts_existing_rows():
    supabase = FakeSupabase()
    supabase.table("zeiterfassung").rows.append(
        {"id": 1, "mitarbeiter_id": 1, "datum": "2026-01-05", "quelle": "historischer_import"}
    )
    daten = {
        "zeitraum": {"von": date(2026, 1, 1), "bis": date(2026, 1, 31), "monat": 1, "jahr": 2026},
        "tage": [
            {"datum": date(2026, 1, 10), "ist": 8.0, "ist_korrekturzeile": False},
            {"datum": date(2026, 1, 11), "ist": 0.0, "ist_korrekturzeile": False},
        ],
    }
    res = dry_run_import_summary(daten, mitarbeiter_id=1, supabase_client=supabase)
    assert res["ok"] is True
    assert res["would_import"] == 1
    assert res["would_skip"] == 1
    assert res["would_delete_zeiterfassung"] >= 1


def test_import_arbeitszeitkonto_falls_back_without_feiertagsstunden_column():
    supabase = FakeSupabase()
    # Simuliert Legacy-DB ohne feiertagsstunden-Spalte in arbeitszeitkonto.
    supabase.table("arbeitszeitkonto").raise_on_insert_msg = (
        "Could not find the 'feiertagsstunden' column of 'arbeitszeitkonto' in the schema cache"
    )
    daten = {
        "zeitraum": {"von": date(2026, 1, 1), "bis": date(2026, 1, 31), "monat": 1, "jahr": 2026},
        "startsaldo": 0.0,
        "tage": [
            {
                "datum": date(2026, 1, 10),
                "wochentag": "Sa",
                "soll": 8.0,
                "plan": 8.0,
                "ist": 8.0,
                "abwesend": 0.0,
                "saldo": 0.0,
                "korrektur": 0.0,
                "korrektur_notiz": "",
                "laufender_saldo": 0.0,
                "std_konto": 0.0,
                "lohn": 120.0,
                "ist_ruhetag": False,
                "ist_korrekturzeile": False,
                "ist_krank": False,
            }
        ],
    }
    result = importiere_in_crewbase(
        daten,
        mitarbeiter_id=1,
        betrieb_id=1,
        supabase_client=supabase,
        ueberschreiben=False,
    )
    assert result["ok"] is True
    assert not any("Fehler beim Arbeitszeitkonto" in e for e in result.get("fehler", []))


def test_csv_reader_parses_minimal_planovo_format():
    csv_content = (
        "Arbeitszeitauswertung\n"
        "01.01.2026 - 31.01.2026\n"
        "\n"
        "Silke Beispiel - 1001\n"
        "Datum;Tag;Soll;Plan;Ist;Abwesend;Saldo;Korrektur;Korrektur Notiz;Lauf. Saldo;Std. Konto;Lohn\n"
        "\n"
        "15.01.2026;Do;8;8;8;0;0;0;;10;10;120\n"
        "Summe;;;;;;;0;;;10;10;120\n"
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(csv_content.encode("utf-8"))
        tmp_path = tmp.name
    try:
        parsed = lese_csv_datei(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    assert not parsed.get("fehler")
    assert parsed.get("zeitraum", {}).get("monat") == 1
    assert len(parsed.get("tage", [])) >= 1
