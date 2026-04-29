from __future__ import annotations

from datetime import date

from utils.work_accounts import (
    close_work_account_month,
    compute_work_account_snapshot,
    sync_work_account_for_month,
    sync_work_account_range,
    validate_work_account_cycle,
)


class FakeResponse:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class FakeQuery:
    def __init__(self, table: "FakeTable"):
        self.table = table
        self._filters = []
        self._limit = None
        self._selected = None
        self._insert_payload = None
        self._upsert_payload = None

    def select(self, columns):
        self._selected = columns
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

    def upsert(self, payload, on_conflict=None):
        self._upsert_payload = payload
        self.table.last_upsert_payload = payload
        self.table.last_on_conflict = on_conflict
        return self

    def execute(self):
        if self._insert_payload is not None:
            self.table.rows.append(dict(self._insert_payload))
            self.table.last_insert_payload = dict(self._insert_payload)
            return FakeResponse([dict(self._insert_payload)])
        if self._upsert_payload is not None:
            self.table.rows.append(dict(self._upsert_payload))
            return FakeResponse([dict(self._upsert_payload)])
        rows = [r for r in self.table.rows if self._match_row(r)]
        if self._limit is not None:
            rows = rows[: self._limit]
        return FakeResponse(rows)

    def _match_row(self, row):
        for op, key, value in self._filters:
            rv = row.get(key)
            if op == "eq":
                if rv != value:
                    return False
            elif op == "gte":
                if rv < value:
                    return False
            elif op == "lte":
                if rv > value:
                    return False
        return True


class FakeTable:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.last_insert_payload = None
        self.last_upsert_payload = None
        self.last_on_conflict = None
        self.raise_on_upsert = None

    def select(self, columns):
        return FakeQuery(self).select(columns)

    def insert(self, payload):
        return FakeQuery(self).insert(payload)

    def upsert(self, payload, on_conflict=None):
        return FakeQuery(self).upsert(payload, on_conflict=on_conflict)


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "mitarbeiter": FakeTable(
                [
                    {
                        "id": 1,
                        "monatliche_soll_stunden": 150.0,
                        "jahres_urlaubstage": 30.0,
                        "resturlaub_vorjahr": 2.0,
                    }
                ]
            ),
            "vertraege": FakeTable(
                [
                    {
                        "mitarbeiter_id": 1,
                        "gueltig_ab": "2026-01-01",
                        "gueltig_bis": None,
                        "soll_stunden_monat": 120.0,
                        "wochenstunden": 30.0,
                        "urlaubstage_jahr": 28.0,
                    }
                ]
            ),
            "zeiterfassung": FakeTable(
                [
                    {"mitarbeiter_id": 1, "datum": "2026-03-02", "arbeitsstunden": 50.0, "stunden": None},
                    {"mitarbeiter_id": 1, "datum": "2026-03-11", "arbeitsstunden": 70.0, "stunden": None},
                    {"mitarbeiter_id": 1, "datum": "2026-03-31", "arbeitsstunden": 0.0, "stunden": None},
                ]
            ),
            "abwesenheiten": FakeTable(
                [
                    {"mitarbeiter_id": 1, "typ": "urlaub", "start_datum": "2026-03-04", "ende_datum": "2026-03-04"},
                    {"mitarbeiter_id": 1, "typ": "krankheit", "start_datum": "2026-03-05", "ende_datum": "2026-03-05"},
                ]
            ),
            "azk_monatsabschluesse": FakeTable([]),
            "arbeitszeit_konten": FakeTable([]),
        }

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable([])
        return self.tables[name]


def test_sync_uses_contract_and_is_idempotent():
    sb = FakeSupabase()

    first = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    second = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )

    assert first.soll_stunden == 120.0
    assert first.soll_stunden == second.soll_stunden
    assert first.ueberstunden_saldo == second.ueberstunden_saldo
    assert first.differenz_stunden == 0.0


def test_close_month_creates_immutable_snapshot():
    sb = FakeSupabase()

    closed = close_work_account_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
        created_by=99,
    )
    assert closed.monat_abgeschlossen is True

    # spätere Änderungen in Zeiterfassung dürfen geschlossenen Monat nicht mehr beeinflussen
    sb.table("zeiterfassung").rows.append(
        {"mitarbeiter_id": 1, "datum": "2026-03-20", "arbeitsstunden": 20.0, "stunden": None}
    )

    locked = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    assert locked.monat_abgeschlossen is True
    assert locked.ist_stunden == closed.ist_stunden
    assert locked.ueberstunden_saldo == closed.ueberstunden_saldo


def test_sync_range_runs_inclusive_months():
    sb = FakeSupabase()
    snapshots = sync_work_account_range(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        start_monat=2,
        start_jahr=2026,
        end_monat=4,
        end_jahr=2026,
    )
    assert len(snapshots) == 3


def test_load_month_ist_hours_ignores_historical_balance_rows():
    sb = FakeSupabase()
    sb.table("zeiterfassung").rows.append(
        {
            "mitarbeiter_id": 1,
            "datum": "2026-03-31",
            "arbeitsstunden": 100.0,
            "stunden": None,
            "quelle": "historischer_saldo",
        }
    )
    snap = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    # 50 + 70 (+ 0) aus den vorhandenen Testzeilen, der historische_saldo darf nicht mitzählen.
    assert snap.ist_stunden == 120.0


def test_validate_work_account_cycle_flags_purpose_mismatch():
    sb = FakeSupabase()
    # Zweckwidriger Eintrag: abwesenheit_system mit positivem Arbeitsstundenwert.
    sb.table("zeiterfassung").rows.append(
        {
            "mitarbeiter_id": 1,
            "datum": "2026-03-12",
            "arbeitsstunden": 5.0,
            "stunden": None,
            "quelle": "abwesenheit_system",
        }
    )
    checks = validate_work_account_cycle(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    assert checks["ok"] is False
    assert checks["invalid_purpose_rows"] >= 1


def test_vacation_entitlement_partial_year_uses_burlg_month_rule():
    sb = FakeSupabase()
    sb.table("mitarbeiter").rows = [
        {
            "id": 1,
            "monatliche_soll_stunden": 150.0,
            "jahres_urlaubstage": 30.0,
            "resturlaub_vorjahr": 2.0,
            "eintrittsdatum": "2026-03-15",
            "austrittsdatum": None,
        }
    ]
    sb.table("vertraege").rows = [
        {
            "mitarbeiter_id": 1,
            "gueltig_ab": "2026-01-01",
            "gueltig_bis": None,
            "soll_stunden_monat": 120.0,
            "wochenstunden": 30.0,
            "urlaubstage_jahr": 24.0,
            "arbeitstage_pro_woche": 5.0,
            "urlaubstage_sind_basis_6tage": "true",
        }
    ]
    sb.table("abwesenheiten").rows = []
    snap = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=6,
        jahr=2026,
    )
    # 24 Basis-Tage (6-Tage-Woche) -> 20 Zieltage bei 5 Arbeitstagen/Woche.
    # Teilurlaub (Eintritt im März): volle Monate bis Ende Juni = Apr, Mai, Jun = 3 Monate.
    # 20 * 3/12 = 5 Tage + 2 Resturlaub Vorjahr = 7 Tage Anspruch.
    assert snap.urlaubstage_gesamt == 7.0


def test_sick_days_with_proof_not_counted_as_vacation_used():
    sb = FakeSupabase()
    sb.table("abwesenheiten").rows = [
        {
            "mitarbeiter_id": 1,
            "typ": "urlaub",
            "start_datum": "2026-03-10",
            "ende_datum": "2026-03-12",
        },
        {
            "mitarbeiter_id": 1,
            "typ": "krankheit",
            "start_datum": "2026-03-11",
            "ende_datum": "2026-03-11",
            "attest_pfad": "storage/au/ma1_2026-03-11.pdf",
        },
    ]
    snap = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    # Im Betriebsmodell (Mi-So) sind hier 2 Urlaubs-Arbeitstage betroffen (11./12.03.),
    # davon 1 Tag krank mit Nachweis (§ 9 BUrlG) => nur 1 Urlaubstag angerechnet.
    assert snap.urlaubstage_genommen == 1.0
    assert snap.krankheitstage_gesamt >= 1.0


def test_vacation_taken_is_cumulative_until_selected_month():
    sb = FakeSupabase()
    sb.table("abwesenheiten").rows = [
        {"mitarbeiter_id": 1, "typ": "urlaub", "start_datum": "2026-01-08", "ende_datum": "2026-01-08"},
        {"mitarbeiter_id": 1, "typ": "urlaub", "start_datum": "2026-03-04", "ende_datum": "2026-03-04"},
    ]
    snap_mar = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=3,
        jahr=2026,
    )
    snap_apr = sync_work_account_for_month(
        sb,
        betrieb_id=1,
        mitarbeiter_id=1,
        monat=4,
        jahr=2026,
    )
    assert snap_mar.urlaubstage_genommen == 2.0
    # Fortlaufender Abzug: April bleibt mindestens auf diesem Stand (ohne neue Urlaube).
    assert snap_apr.urlaubstage_genommen == 2.0
