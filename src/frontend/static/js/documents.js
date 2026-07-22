(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  if (!dropzone) return;

  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const doc = await AgentCareAPI.upload("/api/documents/upload", formData);
      loadDocuments();
      AgentCareUI.toast(
        doc.is_duplicate_of ? `"${file.name}" matches a document already on file` : `"${file.name}" uploaded`,
        doc.is_duplicate_of ? "warning" : "success"
      );
    } catch (err) {
      AgentCareUI.toast(`Upload failed: ${err.message}`, "danger");
    }
  }

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) uploadFile(fileInput.files[0]);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  window.loadDocuments = async function loadDocuments() {
    const body = document.getElementById("documents-body");
    if (!body) return;
    try {
      const documents = await AgentCareAPI.get("/api/documents");
      if (!documents.length) {
        body.innerHTML = `<tr><td colspan="3" class="empty-state">No documents uploaded yet.</td></tr>`;
        return;
      }
      body.innerHTML = documents
        .map(
          (d) => `
        <tr>
          <td>${d.document_type.replace(/_/g, " ")}</td>
          <td>${
            d.is_duplicate_of
              ? `<span class="badge badge-warning">duplicate</span>`
              : `<span class="badge badge-success">on file</span>`
          }</td>
          <td>${formatDateTime(d.created_at)}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      body.innerHTML = `<tr><td colspan="3" class="empty-state">${err.message}</td></tr>`;
    }
  };

  document.addEventListener("tab-shown", (e) => {
    if (e.detail.tab === "documents") loadDocuments();
  });

  loadDocuments();
})();
