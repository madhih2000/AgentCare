import re

DOCUMENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "ecg_report": ["ecg", "ekg", "electrocardiogram"],
    "blood_report": ["blood", "cbc", "lipid", "hba1c", "glucose"],
    "xray_report": ["xray", "radiograph"],
    "mri_report": ["mri", "scan"],
    "prescription": ["prescription", "rx"],
    "discharge_summary": ["discharge"],
    "insurance_card": ["insurance", "policy"],
    "id_proof": ["id", "passport", "license", "aadhaar"],
}

REQUIRED_DOCUMENTS_BY_DEPARTMENT: dict[str, list[str]] = {
    "Cardiology": ["ecg_report", "blood_report"],
    "Orthopedics": ["xray_report"],
    "General Medicine": ["blood_report"],
    "Neurology": ["mri_report"],
}

EMERGENCY_KEYWORDS = [
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "unconscious",
    "severe bleeding",
    "suicidal",
    "heart attack",
    "stroke",
    "not breathing",
    "seizure",
    "emergency",
]

CLINICAL_REQUEST_KEYWORDS = [
    "diagnose",
    "diagnosis",
    "what medicine",
    "prescribe",
    "prescription for",
    "dosage",
    "dose of",
    "what disease",
    "am i having",
    "do i have cancer",
    "is this serious",
]


def _tokenize(text: str) -> set[str]:
    """Splits on any run of non-alphanumeric characters so short keywords
    (e.g. "id") match only as whole tokens — "holiday_photo.png" must not
    match "id" just because it appears inside "holiday"."""
    return set(re.split(r"[^a-z0-9]+", text.lower()))


def infer_document_type(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    tokens = _tokenize(stem)
    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        if tokens & set(keywords):
            return doc_type
    return "other"


def contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def is_emergency_request(text: str) -> bool:
    return contains_any(text, EMERGENCY_KEYWORDS)


def is_clinical_overreach_request(text: str) -> bool:
    return contains_any(text, CLINICAL_REQUEST_KEYWORDS)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
