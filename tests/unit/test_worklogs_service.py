from __future__ import annotations

from datetime import date

import allure
import pytest
from fastapi import HTTPException

from backend.services import worklogs_service


@allure.epic("Worklogs")
@allure.feature("Worklogs Service")
@allure.story("Validation")
@allure.title("validate_hours rejects zero and negative values")
def test_validate_hours_rejects_non_positive_values():
    with pytest.raises(HTTPException) as exc_zero:
        worklogs_service.validate_hours(0)
    assert exc_zero.value.status_code == 400

    with pytest.raises(HTTPException) as exc_negative:
        worklogs_service.validate_hours(-1.5)
    assert exc_negative.value.status_code == 400


@allure.epic("Worklogs")
@allure.feature("Worklogs Service")
@allure.story("Validation")
@allure.title("validate_period rejects inverted date range")
def test_validate_period_rejects_inverted_range():
    with pytest.raises(HTTPException) as exc:
        worklogs_service.validate_period(date(2026, 1, 2), date(2026, 1, 1))
    assert exc.value.status_code == 400


@allure.epic("Worklogs")
@allure.feature("Worklogs Service")
@allure.story("Validation")
@allure.title("update payload must not be empty")
def test_empty_patch_payload_is_invalid():
    with pytest.raises(HTTPException) as exc:
        worklogs_service.ensure_patch_payload_not_empty({})
    assert exc.value.status_code == 400
