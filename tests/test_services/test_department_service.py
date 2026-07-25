from backend.services import department_service


def test_classify_department_matches_real_row(db, seeded_clinical):
    matched = department_service.classify_department(db, "I have severe chest pain and need a cardiologist")
    assert matched is not None
    assert matched.id == seeded_clinical["department"].id
    assert matched.name == "Cardiology"


def test_classify_department_matches_cardio_without_longer_keyword(db, seeded_clinical):
    # Regression test: "cardio" alone (no "chest"/"heart"/"cardiac") used to
    # fail to match because the keyword list held "cardiology" (the longer
    # form), which isn't a substring of "cardio appointment".
    matched = department_service.classify_department(db, "I need cardio appointment next week")
    assert matched is not None
    assert matched.name == "Cardiology"


def test_classify_department_returns_none_when_no_keyword_match(db, seeded_clinical):
    matched = department_service.classify_department(db, "I want to update my mailing address")
    assert matched is None


def test_get_active_department_returns_real_row(db, seeded_clinical):
    dept = department_service.get_active_department(db, seeded_clinical["department"].id)
    assert dept is not None
    assert dept.name == "Cardiology"


def test_get_active_department_returns_none_for_unknown_id(db, seeded_clinical):
    assert department_service.get_active_department(db, "not-a-real-id") is None


def test_get_active_department_returns_none_for_inactive_department(db, seeded_clinical):
    dept = seeded_clinical["department"]
    dept.active = False
    db.commit()
    assert department_service.get_active_department(db, dept.id) is None
