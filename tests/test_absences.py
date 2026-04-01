from datetime import date

from utils.absences import store_absence


class FakeResponse:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class FakeQuery:
    def __init__(self, table: "FakeTable"):
        self.table = table
        self._insert_payload = None
        self._upsert_payload = None

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._upsert_payload = payload
        return self

    def execute(self):
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            self.table.rows.append(payload)
            self.table.last_insert_payload = payload
            # Tabelle kann legacy-Constraint simulieren und Fehler triggern.
            if self.table.raise_after_insert:
                exc = self.table.raise_after_insert
                self.table.raise_after_insert = None
                raise exc
            return FakeResponse([payload])
        if self._upsert_payload is not None:
            payload = dict(self._upsert_payload)
            self.table.rows.append(payload)
            self.table.last_upsert_payload = payload
            return FakeResponse([payload])
        return FakeResponse([])


class FakeTable:
    def __init__(self):
        self.rows = []
        self.last_insert_payload = None
        self.last_upsert_payload = None
        self.raise_after_insert = None

    def insert(self, payload):
        return FakeQuery(self).insert(payload)

    def upsert(self, payload, on_conflict=None):
        return FakeQuery(self).upsert(payload, on_conflict=on_conflict)


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "abwesenheiten": FakeTable(),
            "zeiterfassung": FakeTable(),
        }

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable()
        return self.tables[name]


def test_store_absence_fallback_sets_legacy_datum_field():
    sb = FakeSupabase()

    # Erster Insert soll so fehlschlagen wie in Production-Trace (datum NOT NULL).
    sb.table("abwesenheiten").raise_after_insert = Exception(
        "{'message': 'null value in column \"datum\" violates not-null constraint', 'code': '23502'}"
    )

    out = store_absence(
        sb,
        betrieb_id=1,
        mitarbeiter_id=7,
        typ="krankheit",
        start=date(2026, 4, 1),
        end=date(2026, 4, 6),
        monthly_target_hours=160.0,
    )

    assert out["typ"] == "krankheit"
    inserted = sb.table("abwesenheiten").last_insert_payload
    assert inserted is not None
    assert inserted.get("datum") == "2026-04-01"
    # Legacy-Spiegel schreibt keine 24h-Konstrukte.
    for row in sb.table("zeiterfassung").rows:
        assert row.get("arbeitsstunden", 0.0) <= 12.0
