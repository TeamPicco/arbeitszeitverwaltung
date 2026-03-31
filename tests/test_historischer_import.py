from datetime import date

from utils.historischer_import import importiere_in_crewbase


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

    def select(self, columns):
        return FakeQuery(self).select(columns)

    def insert(self, payload):
        return FakeQuery(self).insert(payload)

    def update(self, payload):
        return FakeQuery(self).update(payload)

    def delete(self):
        return FakeQuery(self).delete()


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
