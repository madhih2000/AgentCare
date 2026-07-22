from backend.services import document_service


def test_upload_infers_document_type_from_filename(db, patient_profile, tmp_path, monkeypatch):
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    doc = document_service.save_document(
        db, patient_id=patient_profile.id, filename="ecg_report_march.pdf", content=b"fake-ecg-bytes",
        document_date=None, actor_id=patient_profile.user_id,
    )
    assert doc.document_type == "ecg_report"
    assert doc.is_duplicate_of is None


def test_duplicate_upload_is_flagged_by_checksum(db, patient_profile, tmp_path, monkeypatch):
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    first = document_service.save_document(
        db, patient_id=patient_profile.id, filename="blood_report.pdf", content=b"same-bytes",
        document_date=None, actor_id=patient_profile.user_id,
    )
    second = document_service.save_document(
        db, patient_id=patient_profile.id, filename="blood_report_copy.pdf", content=b"same-bytes",
        document_date=None, actor_id=patient_profile.user_id,
    )
    assert second.is_duplicate_of == first.id


def test_missing_documents_for_department(db, patient_profile, tmp_path, monkeypatch):
    monkeypatch.setattr(document_service.settings, "upload_dir", str(tmp_path))

    missing = document_service.missing_documents_for_department(
        db, patient_id=patient_profile.id, department_name="Cardiology"
    )
    assert set(missing) == {"ecg_report", "blood_report"}

    document_service.save_document(
        db, patient_id=patient_profile.id, filename="ecg_report.pdf", content=b"ecg-bytes",
        document_date=None, actor_id=patient_profile.user_id,
    )
    still_missing = document_service.missing_documents_for_department(
        db, patient_id=patient_profile.id, department_name="Cardiology"
    )
    assert still_missing == ["blood_report"]
