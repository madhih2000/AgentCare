(() => {
  async function loadWorkflows() {
    const body = document.getElementById("workflows-body");
    if (!body) return;
    try {
      const runs = await AgentCareAPI.get("/api/staff/workflows");
      if (!runs.length) {
        body.innerHTML = `<tr><td colspan="4" class="empty-state">No requests yet.</td></tr>`;
        return;
      }
      body.innerHTML = runs
        .map(
          (r) => `
        <tr>
          <td>${r.patient_name}</td>
          <td>${r.current_step}</td>
          <td><span class="badge ${statusBadgeClass(r.status)}">${r.status}</span></td>
          <td>${formatDateTime(r.updated_at)}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="4" class="empty-state">${err.message}</td></tr>`;
    }
  }

  async function loadEscalations() {
    const body = document.getElementById("escalations-body");
    if (!body) return;
    try {
      const escalations = await AgentCareAPI.get("/api/staff/escalations");
      if (!escalations.length) {
        body.innerHTML = `<tr><td colspan="4" class="empty-state">No open escalations. 🎉</td></tr>`;
        return;
      }
      body.innerHTML = escalations
        .map(
          (esc) => `
        <tr>
          <td>${esc.reason}</td>
          <td class="text-xs">${esc.workflow_run_id.slice(0, 8)}…</td>
          <td>${formatDateTime(esc.created_at)}</td>
          <td class="row">
            <button class="btn btn-primary btn-sm" onclick="decideEscalation('${esc.id}', 'approved')">Approve</button>
            <button class="btn btn-danger btn-sm" onclick="decideEscalation('${esc.id}', 'rejected')">Reject</button>
          </td>
        </tr>`
        )
        .join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="4" class="empty-state">${err.message}</td></tr>`;
    }
  }

  window.decideEscalation = async function decideEscalation(id, decision) {
    try {
      await AgentCareAPI.post(`/api/staff/escalations/${id}/decision`, { decision });
      AgentCareUI.toast(`Escalation ${decision}`, decision === "approved" ? "success" : "warning");
      loadEscalations();
      loadWorkflows();
    } catch (err) {
      AgentCareUI.toast(err.message, "danger");
    }
  };

  async function loadAudit() {
    const body = document.getElementById("audit-body");
    if (!body) return;
    try {
      const events = await AgentCareAPI.get("/api/audit");
      if (!events.length) {
        body.innerHTML = `<tr><td colspan="4" class="empty-state">No audit events yet.</td></tr>`;
        return;
      }
      body.innerHTML = events
        .map(
          (ev) => `
        <tr>
          <td>${ev.action}</td>
          <td class="text-xs">${ev.entity_type} · ${ev.entity_id.slice(0, 8)}…</td>
          <td class="text-xs">${ev.actor_id ? ev.actor_id.slice(0, 8) + "…" : "system"}</td>
          <td>${formatDateTime(ev.created_at)}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="4" class="empty-state">${err.message}</td></tr>`;
    }
  }

  async function populateManageForms() {
    const deptSelect = document.getElementById("doctor-department");
    const slotDoctorSelect = document.getElementById("slot-doctor");
    const calendarDoctorSelect = document.getElementById("calendar-doctor");
    if (!deptSelect) return;
    try {
      const departments = await AgentCareAPI.get("/api/clinical/departments");
      deptSelect.innerHTML = departments.map((d) => `<option value="${d.id}">${d.name}</option>`).join("");

      const doctorLists = await Promise.all(
        departments.map((d) => AgentCareAPI.get(`/api/clinical/departments/${d.id}/doctors`))
      );
      const doctors = doctorLists.flat();
      const doctorOptions = doctors.map((doc) => `<option value="${doc.id}">${doc.name}</option>`).join("");
      slotDoctorSelect.innerHTML = doctorOptions;

      if (calendarDoctorSelect) {
        const previouslySelected = calendarDoctorSelect.value;
        calendarDoctorSelect.innerHTML = doctorOptions;
        if (doctors.some((doc) => doc.id === previouslySelected)) {
          calendarDoctorSelect.value = previouslySelected;
        }
        if (calendarDoctorSelect.value) loadDoctorCalendar(calendarDoctorSelect.value);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function calendarSlotCellHtml(slot) {
    let label;
    let title;
    if (slot.status === "booked") {
      label = slot.patient_name || "Booked";
      title = slot.reason ? `${label} — ${slot.reason}` : label;
    } else {
      label = slot.status === "open" ? "Open" : slot.status;
      title = label;
    }
    return `<td class="calendar-cell" data-status="${slot.status}" title="${escapeHtml(title)}">
      <span class="calendar-chip">${escapeHtml(label)}</span>
    </td>`;
  }

  function renderCalendarGrid(slots) {
    const dates = new Map(); // dateKey -> { label, sortValue }
    const times = new Map(); // minutesSinceMidnight -> label
    const cells = new Map(); // "dateKey|minutes" -> slot

    slots.forEach((slot) => {
      const start = new Date(slot.start_time);
      const dateKey = start.toDateString();
      const minutes = start.getHours() * 60 + start.getMinutes();
      if (!dates.has(dateKey)) {
        dates.set(dateKey, {
          label: start.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }),
          sortValue: new Date(start).setHours(0, 0, 0, 0),
        });
      }
      if (!times.has(minutes)) {
        times.set(minutes, start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }));
      }
      cells.set(`${dateKey}|${minutes}`, slot);
    });

    const sortedDates = [...dates.entries()].sort((a, b) => a[1].sortValue - b[1].sortValue);
    const sortedTimes = [...times.entries()].sort((a, b) => a[0] - b[0]);

    let html = `<table class="calendar-table"><thead><tr><th></th>`;
    sortedDates.forEach(([, d]) => {
      html += `<th>${d.label}</th>`;
    });
    html += `</tr></thead><tbody>`;
    sortedTimes.forEach(([minutes, label]) => {
      html += `<tr><th class="calendar-table__time">${label}</th>`;
      sortedDates.forEach(([dateKey]) => {
        const slot = cells.get(`${dateKey}|${minutes}`);
        html += slot ? calendarSlotCellHtml(slot) : `<td class="calendar-cell"></td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    return html;
  }

  async function loadDoctorCalendar(doctorId) {
    const grid = document.getElementById("calendar-grid");
    if (!grid) return;
    if (!doctorId) {
      grid.innerHTML = `<p class="muted">Select a doctor to view their schedule.</p>`;
      return;
    }
    grid.innerHTML = `<p class="muted">Loading…</p>`;
    try {
      const slots = await AgentCareAPI.get(`/api/staff/doctors/${doctorId}/calendar`);
      grid.innerHTML = slots.length
        ? renderCalendarGrid(slots)
        : `<p class="empty-state">No slots scheduled for this doctor yet.</p>`;
    } catch (err) {
      grid.innerHTML = `<p class="empty-state">${err.message}</p>`;
    }
  }

  document.getElementById("calendar-doctor")?.addEventListener("change", (e) => {
    loadDoctorCalendar(e.target.value);
  });

  document.getElementById("doctor-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const doctor = await AgentCareAPI.post("/api/staff/doctors", {
        department_id: document.getElementById("doctor-department").value,
        name: document.getElementById("doctor-name").value,
      });
      document.getElementById("doctor-name").value = "";
      AgentCareUI.toast(`${doctor.name} added`, "success");
      populateManageForms();
    } catch (err) {
      AgentCareUI.toast(err.message, "danger");
    }
  });

  document.getElementById("slot-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const doctorId = document.getElementById("slot-doctor").value;
    try {
      await AgentCareAPI.post("/api/staff/slots", {
        doctor_id: doctorId,
        start_time: document.getElementById("slot-start").value,
        end_time: document.getElementById("slot-end").value,
      });
      AgentCareUI.toast("Slot added", "success");
      const calendarDoctorSelect = document.getElementById("calendar-doctor");
      if (calendarDoctorSelect && calendarDoctorSelect.value === doctorId) {
        loadDoctorCalendar(doctorId);
      }
    } catch (err) {
      AgentCareUI.toast(err.message, "danger");
    }
  });

  document.addEventListener("tab-shown", (e) => {
    if (e.detail.tab === "requests") loadWorkflows();
    if (e.detail.tab === "escalations") loadEscalations();
    if (e.detail.tab === "audit") loadAudit();
    if (e.detail.tab === "manage") populateManageForms();
  });

  loadWorkflows();
  loadEscalations();
})();
