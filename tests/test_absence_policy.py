from __future__ import annotations

from utils.absence_policy import evaluate_paid_absence_credit, include_paid_absence_in_reports


def test_include_paid_absence_switch():
    assert include_paid_absence_in_reports("mit") is True
    assert include_paid_absence_in_reports("ohne") is False


def test_evaluate_paid_absence_credit_for_paid_and_unpaid_types():
    policy = {"urlaub": True, "krankheit": True, "unbezahlter_urlaub": False}

    urlaub_row = {"abwesenheitstyp": "urlaub", "arbeitsstunden": 7.5, "stunden": 0.0}
    unpaid_row = {"abwesenheitstyp": "unbezahlter_urlaub", "arbeitsstunden": 7.5, "stunden": 0.0}
    unknown_row = {"abwesenheitstyp": "fortbildung", "arbeitsstunden": 7.5, "stunden": 0.0}

    assert evaluate_paid_absence_credit(urlaub_row, policy) == 7.5
    assert evaluate_paid_absence_credit(unpaid_row, policy) == 0.0
    assert evaluate_paid_absence_credit(unknown_row, policy) == 0.0

