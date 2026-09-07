async function requireAuth() {
  try {
    return await api.get("/auth/me");
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      window.location.href = "/index.html";
      return null;
    }
    throw err;
  }
}

async function login(username, password) {
  return api.post("/auth/login", { username, password });
}

async function demoLogin() {
  return api.post("/auth/demo-login");
}

async function logout() {
  await api.post("/auth/logout");
  window.location.href = "/index.html";
}

const ROLE_LABELS = {
  admin: "Administrator",
  accountant: "Accountant",
  cashier: "Cashier",
  auditor: "Auditor",
  clinician: "Clinician",
};
