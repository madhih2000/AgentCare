document.addEventListener("DOMContentLoaded", () => {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${target}`).classList.add("active");
      document.dispatchEvent(new CustomEvent("tab-shown", { detail: { tab: target } }));
    });
  });
});

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function formatAgentText(raw) {
  if (!raw) return "";
  const escaped = String(raw)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^[-*]\s+/gm, "&bull; ")
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

function statusBadgeClass(status) {
  const map = {
    booked: "badge-success",
    completed: "badge-success",
    sent: "badge-success",
    approved: "badge-success",
    open: "badge-warning",
    pending: "badge-warning",
    in_progress: "badge-info",
    rescheduled: "badge-info",
    escalated: "badge-danger",
    failed: "badge-danger",
    rejected: "badge-danger",
    cancelled: "badge-neutral",
  };
  return map[status] || "badge-neutral";
}
