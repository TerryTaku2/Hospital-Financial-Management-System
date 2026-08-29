const NAV_ITEMS = [
  { href: "/dashboard.html", label: "Dashboard" },
  { href: "/patients.html", label: "Patients" },
  { href: "/billing.html", label: "Billing", roles: ["admin", "cashier", "accountant"] },
  { href: "/payment-point.html", label: "Payment Point", roles: ["admin", "cashier", "accountant"] },
  { href: "/deposits.html", label: "Deposits", roles: ["admin", "cashier", "accountant"] },
  { href: "/claims.html", label: "Medical Aid Claims", roles: ["admin", "cashier", "accountant"] },
  { href: "/accounts.html", label: "Chart of Accounts", roles: ["admin", "accountant", "auditor"] },
  { href: "/journal.html", label: "Journal Entries", roles: ["admin", "accountant", "auditor"] },
  { href: "/trial-balance.html", label: "Trial Balance", roles: ["admin", "accountant", "auditor"], section: "Reports" },
  { href: "/income-statement.html", label: "Income Statement", roles: ["admin", "accountant", "auditor"], section: "Reports" },
  { href: "/ar-aging.html", label: "AR Aging", roles: ["admin", "accountant", "auditor"], section: "Reports" },
  { href: "/users.html", label: "Users", roles: ["admin"] },
  { href: "/branches.html", label: "Branches", roles: ["admin"] },
  { href: "/audit-log.html", label: "Audit Log", roles: ["admin", "auditor"] },
];

function renderLayout(user, pageTitle) {
  const sidebarRoot = document.getElementById("sidebar-root");
  const topbarRoot = document.getElementById("topbar-root");
  const currentPath = window.location.pathname;

  if (sidebarRoot) {
    let lastSection = null;
    const links = NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(user.role))
      .map((item) => {
        let label = "";
        if (item.section !== lastSection) {
          lastSection = item.section;
          if (item.section) label = `<div class="nav-section-label">${item.section}</div>`;
        }
        return `${label}<a href="${item.href}" class="${currentPath === item.href ? "active" : ""}">${item.label}</a>`;
      })
      .join("");
    sidebarRoot.innerHTML = `
      <div class="brand">Hospital Finance</div>
      <nav>${links}</nav>
    `;
  }

  if (topbarRoot) {
    topbarRoot.innerHTML = `
      <h1>${pageTitle}</h1>
      <div class="user-badge">
        ${user.full_name} &middot; ${ROLE_LABELS[user.role] || user.role}
        &nbsp;<button class="btn secondary" id="logout-btn">Log out</button>
      </div>
    `;
    document.getElementById("logout-btn").addEventListener("click", logout);
  }
}

async function initPage(pageTitle) {
  const user = await requireAuth();
  if (!user) return null;
  renderLayout(user, pageTitle);
  return user;
}
