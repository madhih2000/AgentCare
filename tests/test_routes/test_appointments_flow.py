def register_and_login(client, email):
    client.post(
        "/api/auth/register",
        json={"name": "Flow Patient", "email": email, "password": "Password123!", "role": "patient"},
    )


def test_book_list_cancel_appointment_via_api(client, seeded_clinical):
    register_and_login(client, "flow@example.com")
    doctor = seeded_clinical["doctor"]
    slot = seeded_clinical["slot"]

    book_response = client.post(
        "/api/appointments",
        json={"doctor_id": doctor.id, "slot_id": slot.id, "reason": "Annual checkup"},
    )
    assert book_response.status_code == 200
    appointment = book_response.json()
    assert appointment["status"] == "booked"

    list_response = client.get("/api/appointments")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    cancel_response = client.post(f"/api/appointments/{appointment['id']}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_booking_unavailable_slot_returns_409(client, seeded_clinical):
    register_and_login(client, "flow2@example.com")
    doctor = seeded_clinical["doctor"]
    slot = seeded_clinical["slot"]

    first = client.post("/api/appointments", json={"doctor_id": doctor.id, "slot_id": slot.id})
    assert first.status_code == 200

    second = client.post("/api/appointments", json={"doctor_id": doctor.id, "slot_id": slot.id})
    assert second.status_code == 409
