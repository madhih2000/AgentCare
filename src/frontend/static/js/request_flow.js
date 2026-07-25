(() => {
  let activeSource = null;
  let currentWorkflowId = null;

  const form = document.getElementById("request-form");
  const submitBtn = document.getElementById("request-submit-btn");
  const statusCard = document.getElementById("workflow-status");
  const statusBadge = document.getElementById("workflow-status-badge");
  const meta = document.getElementById("workflow-meta");
  const traceEl = document.getElementById("workflow-trace");
  const submitBtnDefaultLabel = submitBtn ? submitBtn.textContent : "";

  const clarificationBox = document.getElementById("clarification-box");
  const clarificationQuestionEl = document.getElementById("clarification-question");
  const clarificationForm = document.getElementById("clarification-form");
  const clarificationAnswerInput = document.getElementById("clarification-answer");
  const clarificationSubmitBtn = document.getElementById("clarification-submit-btn");

  const PIPELINE_STAGES = [
    { key: "coordinator", label: "Coordinator", initials: "CO" },
    { key: "safety", label: "Safety & Escalation", initials: "SF" },
    { key: "routing", label: "Department Routing", initials: "RT" },
    { key: "appointment", label: "Appointment", initials: "AP" },
    { key: "document", label: "Document", initials: "DC" },
    { key: "followup", label: "Follow-up", initials: "FU" },
  ];

  const STATE_LABELS = {
    pending: "Pending",
    active: "Running…",
    done: "Done",
    escalated: "Escalated",
    failed: "Failed",
    skipped: "Skipped",
  };

  const ICONS = {
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M5 13l4.5 4.5L19 7"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M12 4 2.5 20h19z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M9 6l6 6-6 6"/></svg>',
  };

  let reachedAgents = new Set();

  function createPipelineNode(stage) {
    const node = document.createElement("div");
    node.className = "pipeline-node";
    node.dataset.agent = stage.key;
    node.dataset.state = "pending";
    node.innerHTML = `
      <div class="pipeline-node__rail">
        <span class="pipeline-node__circle"><span class="label-text">${stage.initials}</span></span>
        <span class="pipeline-node__line"></span>
      </div>
      <div class="pipeline-node__content">
        <div class="pipeline-node__header">
          <span class="pipeline-node__name">${stage.label}</span>
          <span class="pipeline-node__status-label">Pending</span>
        </div>
        <div class="pipeline-node__output"></div>
        <div class="pipeline-node__tools"></div>
      </div>`;
    return node;
  }

  function renderPipelineSkeleton() {
    traceEl.innerHTML = "";
    PIPELINE_STAGES.forEach((stage, i) => {
      const node = createPipelineNode(stage);
      node.style.animationDelay = `${i * 40}ms`;
      traceEl.appendChild(node);
    });
    reachedAgents = new Set();
  }

  function setNodeState(agentKey, state, details = {}) {
    const node = traceEl.querySelector(`.pipeline-node[data-agent="${agentKey}"]`);
    if (!node) return;
    node.dataset.state = state;

    const statusLabel = node.querySelector(".pipeline-node__status-label");
    const circle = node.querySelector(".pipeline-node__circle");
    const output = node.querySelector(".pipeline-node__output");
    const tools = node.querySelector(".pipeline-node__tools");

    statusLabel.textContent = STATE_LABELS[state] || state;

    if (state === "done") circle.innerHTML = ICONS.check;
    else if (state === "escalated") circle.innerHTML = ICONS.alert;
    else if (state === "failed") circle.innerHTML = ICONS.x;
    else if (state === "skipped") circle.innerHTML = "&ndash;";

    if (details.output !== undefined && details.output !== null) {
      output.innerHTML = formatAgentText(details.output);
    }
    if (details.toolCalls && details.toolCalls.length) {
      tools.innerHTML = details.toolCalls
        .map((call) => `<span class="tool-chip">${call.tool}</span>`)
        .join("");
    }
  }

  function handleStageEvent(step) {
    reachedAgents.add(step.agent);
    setNodeState(step.agent, "active", { output: step.output, toolCalls: step.tool_calls });
    // Hold briefly on the "active" pulse before settling into "done" so the
    // sequence reads as a flowchart lighting up stage by stage, even though
    // the event itself already represents a finished step.
    window.setTimeout(() => setNodeState(step.agent, "done"), 380);
  }

  function finalizePipeline(data) {
    PIPELINE_STAGES.forEach((stage) => {
      if (!reachedAgents.has(stage.key)) {
        setNodeState(stage.key, "skipped");
        return;
      }
      if (stage.key === "safety" && data.escalated) {
        setNodeState("safety", "escalated");
      } else if (data.status === "failed") {
        const node = traceEl.querySelector(`.pipeline-node[data-agent="${stage.key}"]`);
        if (node && node.dataset.state !== "done") setNodeState(stage.key, "failed");
      } else {
        setNodeState(stage.key, "done");
      }
    });
  }

  function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    submitBtn.innerHTML = isSubmitting
      ? '<span class="btn-spinner"></span> Working…'
      : submitBtnDefaultLabel;
  }

  function showCompletionModal(data) {
    if (data.status === "escalated") {
      AgentCareUI.modal({
        tone: "warning",
        title: "Sent for human review",
        body: `This request needs a staff member's attention before it can continue.<br><br><strong>Reason:</strong> ${formatAgentText(data.escalation_reason) || "Flagged by the Safety Agent."}`,
        actionLabel: "Understood",
      });
      return;
    }

    if (data.status === "failed") {
      AgentCareUI.modal({
        tone: "danger",
        title: "Something went wrong",
        body: "The workflow could not complete after retrying. Please try submitting your request again.",
        actionLabel: "Close",
      });
      return;
    }

    const parts = [];
    if (data.appointment_id) {
      const when = data.appointment_start ? formatDateTime(data.appointment_start) : "the selected slot";
      parts.push(`<strong>Appointment confirmed</strong> in ${data.department_name || "the routed department"} for <strong>${when}</strong>.`);
    } else if (data.department_name) {
      parts.push(`Routed to <strong>${data.department_name}</strong>.`);
    }
    if (data.missing_documents && data.missing_documents.length) {
      parts.push(`Still missing: <strong>${data.missing_documents.join(", ").replace(/_/g, " ")}</strong>. A reminder has been set.`);
    }
    if (!parts.length) {
      parts.push(formatAgentText(data.final_summary || data.summary) || "Your request has been processed.");
    }

    AgentCareUI.modal({
      tone: "success",
      title: "Request completed",
      body: parts.join("<br><br>"),
      actionLabel: "Great",
    });
    AgentCareUI.toast("Workflow completed", "success");
  }

  function showClarificationPrompt(data) {
    clarificationQuestionEl.textContent = data.clarification_question || "Could you share a bit more detail about your request?";
    clarificationBox.classList.remove("hidden");
    clarificationAnswerInput.value = "";
    clarificationAnswerInput.focus();
  }

  function streamWorkflow(workflowId) {
    currentWorkflowId = workflowId;
    if (activeSource) activeSource.close();
    activeSource = new EventSource(`/api/workflows/${workflowId}/stream`);

    activeSource.addEventListener("stage", (e) => {
      const step = JSON.parse(e.data);
      handleStageEvent(step);
      statusBadge.textContent = `${step.agent} agent running…`;
      statusBadge.className = "badge badge-info";
    });

    activeSource.addEventListener("done", (e) => {
      const data = JSON.parse(e.data);
      activeSource.close();

      if (data.status === "needs_clarification") {
        setNodeState("coordinator", "done");
        statusBadge.textContent = "waiting for your reply";
        statusBadge.className = "badge badge-warning";
        meta.textContent = `Workflow ${data.id} · paused for clarification`;
        setSubmitting(false);
        showClarificationPrompt(data);
        return;
      }

      finalizePipeline(data);
      statusBadge.textContent = data.status.replace("_", " ");
      statusBadge.className = `badge ${statusBadgeClass(data.status)}`;
      meta.textContent = `Step: ${data.current_step} · Finished ${formatDateTime(data.updated_at)}`;
      setSubmitting(false);
      showCompletionModal(data);
      loadAppointments();
      loadReminders();
      if (typeof loadDocuments === "function") loadDocuments();
    });

    activeSource.onerror = () => {
      activeSource.close();
      setSubmitting(false);
    };
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    setSubmitting(true);
    clarificationBox.classList.add("hidden");
    statusCard.classList.remove("hidden");
    renderPipelineSkeleton();
    statusBadge.textContent = "starting…";
    statusBadge.className = "badge badge-info";

    try {
      const run = await AgentCareAPI.post("/api/workflows", {
        message: document.getElementById("request-text").value,
      });
      meta.textContent = `Workflow ${run.id}`;
      document.getElementById("request-text").value = "";
      streamWorkflow(run.id);
    } catch (err) {
      setSubmitting(false);
      statusBadge.textContent = "error";
      statusBadge.className = "badge badge-danger";
      meta.textContent = err.message;
      AgentCareUI.toast(err.message, "danger");
    }
  });

  clarificationForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentWorkflowId) return;
    const answer = clarificationAnswerInput.value.trim();
    if (!answer) return;

    clarificationSubmitBtn.disabled = true;
    try {
      await AgentCareAPI.post(`/api/workflows/${currentWorkflowId}/respond`, { message: answer });
      clarificationBox.classList.add("hidden");
      setSubmitting(true);
      statusBadge.textContent = "resuming…";
      statusBadge.className = "badge badge-info";
      streamWorkflow(currentWorkflowId);
    } catch (err) {
      AgentCareUI.toast(err.message, "danger");
    } finally {
      clarificationSubmitBtn.disabled = false;
    }
  });

  function appointmentRowHtml(a) {
    const detailId = `appt-detail-${a.id}`;
    const when = a.slot_start ? formatDateTime(a.slot_start) : "—";
    const slotRange = a.slot_start
      ? `${formatDateTime(a.slot_start)} – ${a.slot_end ? new Date(a.slot_end).toLocaleTimeString(undefined, { timeStyle: "short" }) : "—"}`
      : "—";
    return `
      <tr class="data-row" data-expand-target="${detailId}">
        <td><span class="row-chevron">${ICONS.chevron}</span></td>
        <td><span class="badge ${statusBadgeClass(a.status)}">${a.status}</span></td>
        <td>
          <div class="cell-primary">${a.doctor_name}</div>
          <div class="cell-secondary">${a.department_name || "—"} · ${when}</div>
        </td>
        <td>${a.reason || "—"}</td>
        <td>${formatDateTime(a.updated_at)}</td>
        <td>
          ${
            a.status === "booked" || a.status === "rescheduled"
              ? `<button class="btn btn-secondary btn-sm" data-no-expand onclick="cancelAppointment('${a.id}')">Cancel</button>`
              : ""
          }
        </td>
      </tr>
      <tr class="data-row-detail" id="${detailId}">
        <td colspan="6">
          <div class="detail-grid">
            <div><span class="detail-label">Appointment ID</span><span class="detail-value">${a.id}</span></div>
            <div><span class="detail-label">Doctor</span><span class="detail-value">${a.doctor_name}</span></div>
            <div><span class="detail-label">Department</span><span class="detail-value">${a.department_name || "—"}</span></div>
            <div><span class="detail-label">Slot</span><span class="detail-value">${slotRange}</span></div>
            <div><span class="detail-label">Reason</span><span class="detail-value">${a.reason || "—"}</span></div>
            <div><span class="detail-label">Booked</span><span class="detail-value">${formatDateTime(a.created_at)}</span></div>
          </div>
        </td>
      </tr>`;
  }

  window.loadAppointments = async function loadAppointments() {
    const body = document.getElementById("appointments-body");
    if (!body) return;
    try {
      const appointments = await AgentCareAPI.get("/api/appointments");
      if (!appointments.length) {
        body.innerHTML = `<tr><td colspan="6" class="empty-state">No appointments yet. Submit a request to book one.</td></tr>`;
        return;
      }
      body.innerHTML = appointments.map(appointmentRowHtml).join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="6" class="empty-state">${err.message}</td></tr>`;
    }
  };

  window.cancelAppointment = async function cancelAppointment(id) {
    if (!confirm("Cancel this appointment?")) return;
    try {
      await AgentCareAPI.post(`/api/appointments/${id}/cancel`);
      AgentCareUI.toast("Appointment cancelled", "success");
      loadAppointments();
    } catch (err) {
      AgentCareUI.toast(err.message, "danger");
    }
  };

  function reminderRowHtml(r) {
    const detailId = `reminder-detail-${r.id}`;
    return `
      <tr class="data-row" data-expand-target="${detailId}">
        <td><span class="row-chevron">${ICONS.chevron}</span></td>
        <td>${r.reminder_type.replace(/_/g, " ")}</td>
        <td>${formatDateTime(r.scheduled_at)}</td>
        <td><span class="badge ${statusBadgeClass(r.status)}">${r.status}</span></td>
      </tr>
      <tr class="data-row-detail" id="${detailId}">
        <td colspan="4">
          <div class="detail-grid">
            <div><span class="detail-label">Reminder ID</span><span class="detail-value">${r.id}</span></div>
            <div><span class="detail-label">Type</span><span class="detail-value">${r.reminder_type.replace(/_/g, " ")}</span></div>
            <div><span class="detail-label">Scheduled for</span><span class="detail-value">${formatDateTime(r.scheduled_at)}</span></div>
            ${
              r.appointment_id
                ? `<div><span class="detail-label">Linked appointment</span><span class="detail-value">${r.appointment_id}</span></div>`
                : ""
            }
          </div>
        </td>
      </tr>`;
  }

  window.loadReminders = async function loadReminders() {
    const body = document.getElementById("reminders-body");
    if (!body) return;
    try {
      const reminders = await AgentCareAPI.get("/api/reminders");
      if (!reminders.length) {
        body.innerHTML = `<tr><td colspan="4" class="empty-state">No reminders yet.</td></tr>`;
        return;
      }
      body.innerHTML = reminders.map(reminderRowHtml).join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="4" class="empty-state">${err.message}</td></tr>`;
    }
  };

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-no-expand]")) return;
    const row = e.target.closest(".data-row");
    if (!row) return;
    const target = document.getElementById(row.dataset.expandTarget);
    if (!target) return;
    const isOpen = target.classList.toggle("open");
    row.classList.toggle("expanded", isOpen);
  });

  document.addEventListener("tab-shown", (e) => {
    if (e.detail.tab === "appointments") loadAppointments();
    if (e.detail.tab === "reminders") loadReminders();
  });

  if (document.getElementById("appointments-body")) loadAppointments();
  if (document.getElementById("reminders-body")) loadReminders();
})();
