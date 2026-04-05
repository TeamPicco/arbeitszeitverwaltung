from datetime import date

import pytest

from utils.absences import calculate_absence_credit, delete_absence, store_absence, update_absence


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

    def select(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def delete(self):
        self._is_delete = True
        return self

    def eq(self, _field, _value):
        return self

    def gte(self, _field, _value):
        return self

    def lte(self, _field, _value):
        return self

    def limit(self, _value):
        return self

    def execute(self):
        if getattr(self, "_is_delete", False):
            if self.table.rows:
                self.table.rows.pop(0)
            return FakeResponse([])
        if getattr(self, "_update_payload", None) is not None:
            payload = dict(self._update_payload)
            self.table.last_update_payload = payload
            if self.table.rows:
                self.table.rows[0].update(payload)
            else:
                self.table.rows.append(payload)
            return FakeResponse([payload])
        if getattr(self, "_select_mode", False):
            return FakeResponse(self.table.rows)
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
        self.last_update_payload = None
        self.last_upsert_payload = None
        self.raise_after_insert = None
        self.raise_after_insert_queue = []

    def insert(self, payload):
        return FakeQuery(self).insert(payload)

    def upsert(self, payload, on_conflict=None):
        return FakeQuery(self).upsert(payload, on_conflict=on_conflict)

    def select(self, *args, **kwargs):
        q = FakeQuery(self)
        q._select_mode = True
        return q

    def update(self, payload):
        return FakeQuery(self).update(payload)

    def delete(self):
        return FakeQuery(self).delete()


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


def test_store_absence_fallback_maps_krankheit_to_legacy_krank_typ():
    sb = FakeSupabase()
    table = sb.table("abwesenheiten")
    # Legacy-Check auf "typ" schlägt für "krankheit" fehl (mit und ohne datum).
    table.raise_after_insert_queue = [
        Exception(
            "{'message': 'new row violates check constraint \"abwesenheiten_typ_check\"', 'code': '23514'}"
        ),
        Exception(
            "{'message': 'new row violates check constraint \"abwesenheiten_typ_check\"', 'code': '23514'}"
        ),
    ]

    # Patch FakeQuery-Ausführung lokal über Queue-Verhalten.
    original_execute = FakeQuery.execute

    def _queued_execute(self):
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            self.table.rows.append(payload)
            self.table.last_insert_payload = payload
            if self.table.raise_after_insert_queue:
                raise self.table.raise_after_insert_queue.pop(0)
            if self.table.raise_after_insert:
                exc = self.table.raise_after_insert
                self.table.raise_after_insert = None
                raise exc
            return FakeResponse([payload])
        return original_execute(self)

    FakeQuery.execute = _queued_execute
    try:
        out = store_absence(
            sb,
            betrieb_id=1,
            mitarbeiter_id=7,
            typ="krankheit",
            start=date(2026, 4, 1),
            end=date(2026, 4, 2),
            monthly_target_hours=160.0,
        )
    finally:
        FakeQuery.execute = original_execute

    assert out["typ"] == "krankheit"
    inserted = sb.table("abwesenheiten").last_insert_payload
    assert inserted is not None
    assert inserted.get("typ") == "krank"


def test_update_absence_requires_reason():
    sb = FakeSupabase()
    sb.table("abwesenheiten").rows = [
        {
            "id": 10,
            "betrieb_id": 1,
            "mitarbeiter_id": 7,
            "typ": "urlaub",
            "start_datum": "2026-04-01",
            "ende_datum": "2026-04-02",
            "stunden_gutschrift": 8.0,
        }
    ]
    with pytest.raises(ValueError):
        update_absence(
            sb,
            absence_id=10,
            typ="urlaub",
            start=date(2026, 4, 1),
            end=date(2026, 4, 2),
            monthly_target_hours=160.0,
            change_reason="",
        )


def test_delete_absence_requires_reason():
    sb = FakeSupabase()
    sb.table("abwesenheiten").rows = [
        {
            "id": 11,
            "betrieb_id": 1,
            "mitarbeiter_id": 7,
            "typ": "krankheit",
            "start_datum": "2026-04-01",
            "ende_datum": "2026-04-03",
        }
    ]
    with pytest.raises(ValueError):
        delete_absence(
            sb,
            absence_id=11,
            delete_reason="",
        )


def test_absence_credit_uses_month_workdays_not_2165():
    # April 2026 hat im Betriebsmodell (Mi-So) 22 Arbeitstage.
    # Tagesziel muss daher exakt 160/22 sein.
    start = date(2026, 4, 1)
    end = date(2026, 4, 1)
    out = calculate_absence_credit(
        typ="krankheit",
        start=start,
        end=end,
        monthly_target_hours=160.0,
        paid=True,
    )
    assert out.days == 1.0
    assert out.credited_hours == round(160.0 / 22.0, 2)


def test_monthly_target_to_daily_hours_with_zero_returns_zero():
    assert _monthly_target_to_daily_hours(monthly_target_hours=0.0, reference_day=date(2026, 4, 1)) == 0.0
