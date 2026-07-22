from backend.services import department_service


def test_classify_department_matches_real_row(db, seeded_clinical):
    matched = department_service.classify_department(db, "I have severe chest pain and need a cardiologist")
    assert matched is not None
    assert matched.id == seeded_clinical["department"].id
    assert matched.name == "Cardiology"


def test_classify_department_returns_none_when_no_keyword_match(db, seeded_clinical):
    matched = department_service.classify_department(db, "I want to update my mailing address")
    assert matched is None
