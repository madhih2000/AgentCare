const AgentCareUI = (() => {
  const TONE_ICONS = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4.5 4.5L19 7"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4 2.5 20h19z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/></svg>',
    danger: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none"/></svg>',
  };

  function ensureToastStack() {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    return stack;
  }

  function toast(message, tone = "info", duration = 4000) {
    const stack = ensureToastStack();
    const el = document.createElement("div");
    el.className = `toast ${tone}`;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 200ms ease";
      setTimeout(() => el.remove(), 200);
    }, duration);
  }

  function modal({ tone = "success", title, body, actionLabel = "Got it" }) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    const iconSvg = TONE_ICONS[tone] || TONE_ICONS.info;
    overlay.innerHTML = `
      <div class="modal-card">
        <div class="modal-icon ${tone}">${iconSvg}</div>
        <h3>${title}</h3>
        <div class="modal-body">${body}</div>
        <div class="modal-actions">
          <button class="btn btn-primary modal-close">${actionLabel}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add("visible"));

    const close = () => {
      overlay.classList.remove("visible");
      setTimeout(() => overlay.remove(), 220);
    };
    overlay.querySelector(".modal-close").addEventListener("click", close);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    document.addEventListener(
      "keydown",
      function onKey(ev) {
        if (ev.key === "Escape") {
          close();
          document.removeEventListener("keydown", onKey);
        }
      },
      { once: true }
    );
    return close;
  }

  return { toast, modal };
})();
