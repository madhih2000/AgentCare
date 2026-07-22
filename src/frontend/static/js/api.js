const AgentCareAPI = (() => {
  async function request(method, path, body, isFormData = false) {
    const options = {
      method,
      credentials: "same-origin",
      headers: isFormData ? {} : { "Content-Type": "application/json" },
    };
    if (body !== undefined && body !== null) {
      options.body = isFormData ? body : JSON.stringify(body);
    }

    const response = await fetch(path, options);
    let data = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }

    if (!response.ok) {
      const message = (data && data.detail) || `Request failed (${response.status})`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body),
    patch: (path, body) => request("PATCH", path, body),
    upload: (path, formData) => request("POST", path, formData, true),
    logout: async () => {
      await request("POST", "/api/auth/logout");
      window.location.href = "/login";
    },
  };
})();
