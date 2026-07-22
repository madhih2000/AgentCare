import pytest

from backend.utils.validators import (
    infer_document_type,
    is_clinical_overreach_request,
    is_emergency_request,
)


@pytest.mark.parametrize(
    "text",
    [
        "I have severe chest pain and can't breathe",
        "My father is unconscious, please help",
        "This is an emergency, call for help",
    ],
)
def test_emergency_language_is_detected(text):
    assert is_emergency_request(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "I need a cardiology appointment next week",
        "Please attach my blood report to my file",
    ],
)
def test_non_emergency_text_is_not_flagged(text):
    assert is_emergency_request(text) is False


@pytest.mark.parametrize(
    "text",
    [
        "Can you diagnose what disease I have?",
        "What medicine should I take for this?",
        "What dosage of my medication should I use?",
    ],
)
def test_clinical_overreach_is_detected(text):
    assert is_clinical_overreach_request(text) is True


def test_administrative_request_is_not_clinical_overreach():
    assert is_clinical_overreach_request("I'd like to book an appointment with cardiology") is False


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("ecg_report_march.pdf", "ecg_report"),
        ("blood_test_results.pdf", "blood_report"),
        ("random_scan.jpg", "mri_report"),
        ("holiday_photo.png", "other"),
    ],
)
def test_infer_document_type(filename, expected):
    assert infer_document_type(filename) == expected
