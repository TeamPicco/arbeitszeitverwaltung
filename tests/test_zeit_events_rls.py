from postgrest.exceptions import APIError

from utils.zeit_events import _is_rls_error


def test_is_rls_error_detects_code_from_apierror_json():
    err = APIError(
        {
            "message": 'new row violates row-level security policy for table "zeit_eintraege"',
            "code": "42501",
            "hint": None,
            "details": None,
        }
    )
    assert _is_rls_error(err) is True

