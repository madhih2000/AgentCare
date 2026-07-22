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
          <td class="text-xs">${r.patient_id.slice(0, 8)}…</td>
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
    if (!deptSelect) return;
    try {
      const departments = await AgentCareAPI.get("/api/clinical/departments");
      deptSelect.innerHTML = departments.map((d) => `<option value="${d.id}">${d.name}</option>`).join("");

      const doctorLists = await Promise.all(
        departments.map((d) => AgentCareAPI.get(`/api/clinical/departments/${d.id}/doctors`))
      );
      const doctors = doctorLists.flat();
      slotDoctorSelect.innerHTML = doctors
        .map((doc) => `<option value="${doc.id}">${doc.name}</option>`)
        .join("");
    } catch (err) {
      console.error(err);
    }
  }

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
    try {
      await AgentCareAPI.post("/api/staff/slots", {
        doctor_id: document.getElementById("slot-doctor").value,
        start_time: document.getElementById("slot-start").value,
        end_time: document.getElementById("slot-end").value,
      });
      AgentCareUI.toast("Slot added", "success");
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
