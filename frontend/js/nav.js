const NAV_ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3.5 20c0-3.3 2.5-5.6 5.5-5.6s5.5 2.3 5.5 5.6"/><circle cx="17" cy="8.5" r="2.4"/><path d="M15 14.6c2.6.3 4.5 2.3 4.5 5.4"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  receipt: '<path d="M6 3h8l5 5v13a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z"/><path d="M14 3v5h5"/><path d="M8.5 13h7M8.5 17h7"/>',
  card: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10.5h18"/><path d="M7 15h4"/>',
  wallet: '<path d="M3 8a2 2 0 012-2h11a2 2 0 012 2v1h1.5a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5H5a2 2 0 01-2-2V8z"/><circle cx="16.5" cy="13.5" r="1.2"/>',
  shieldCheck: '<path d="M12 3l7 3v6c0 4.6-3 8-7 9-4-1-7-4.4-7-9V6l7-3z"/><path d="M9 12l2 2 4-4.2"/>',
  truck: '<rect x="2" y="7" width="12" height="9" rx="1"/><path d="M14 10h4l3 3v3h-7z"/><circle cx="6.5" cy="18" r="1.6"/><circle cx="17" cy="18" r="1.6"/>',
  clipboardList: '<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="8.5" y="2.5" width="7" height="3.5" rx="1"/><path d="M8.5 11h7M8.5 14.5h7M8.5 18h4"/>',
  book: '<path d="M4 4.5A1.5 1.5 0 015.5 3H12v18H5.5A1.5 1.5 0 014 19.5v-15z"/><path d="M20 4.5A1.5 1.5 0 0018.5 3H12v18h6.5a1.5 1.5 0 001.5-1.5v-15z"/>',
  tag: '<path d="M11.5 3H5a1 1 0 00-1 1v6.5a1 1 0 00.3.7l9.5 9.5a1 1 0 001.4 0l6.5-6.5a1 1 0 000-1.4L12.2 3.3a1 1 0 00-.7-.3z"/><circle cx="8" cy="8" r="1.4"/>',
  fileLines: '<path d="M6 3h8l5 5v13a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z"/><path d="M14 3v5h5"/><path d="M8.5 12.5h7M8.5 16h4.5"/>',
  scale: '<path d="M12 3v17M8 21h8"/><path d="M5 7h5M14 7h5"/><path d="M5 7l-3 6a3 3 0 006 0l-3-6z"/><path d="M19 7l-3 6a3 3 0 006 0l-3-6z"/>',
  trendingUp: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  alertClock: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 1.5"/><path d="M9 2h6"/>',
  building: '<rect x="4" y="3" width="10" height="18" rx="1"/><rect x="14" y="9" width="6" height="12" rx="1"/><path d="M7 7h1M10 7h1M7 11h1M10 11h1M7 15h1M10 15h1"/>',
  shield: '<path d="M12 3l7 3v6c0 4.6-3 8-7 9-4-1-7-4.4-7-9V6l7-3z"/><path d="M12 8v5"/><circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none"/>',
  box: '<path d="M3 7.5l9-4.5 9 4.5-9 4.5-9-4.5z"/><path d="M3 7.5v9l9 4.5 9-4.5v-9"/><path d="M12 12v9"/>',
  pill: '<rect x="4" y="9" width="16" height="7.5" rx="3.75" transform="rotate(-45 12 12.75)"/><path d="M9.5 9.5l5.3 5.3" />',
};

function navIcon(key) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${NAV_ICONS[key] || ""}</svg>`;
}

const NAV_ITEMS = [
  { href: "/dashboard.html", label: "Dashboard", icon: "grid" },
  { href: "/patients.html", label: "Patients", icon: "users" },

  { href: "/daily-transactions.html", label: "Daily Transactions", icon: "clock", roles: ["admin", "cashier", "accountant", "auditor"], section: "Front Desk" },
  { href: "/billing.html", label: "Billing", icon: "receipt", roles: ["admin", "cashier", "accountant"], section: "Front Desk" },
  { href: "/payment-point.html", label: "Payment Point", icon: "card", roles: ["admin", "cashier", "accountant"], section: "Front Desk" },
  { href: "/deposits.html", label: "Deposits", icon: "wallet", roles: ["admin", "cashier", "accountant"], section: "Front Desk" },
  { href: "/claims.html", label: "Medical Aid Claims", icon: "shieldCheck", roles: ["admin", "cashier", "accountant"], section: "Front Desk" },

  { href: "/stores.html", label: "Stores", icon: "box", roles: ["admin", "cashier", "accountant", "auditor"], section: "Stores" },
  { href: "/suppliers.html", label: "Suppliers", icon: "truck", roles: ["admin", "cashier", "accountant", "auditor"], section: "Stores" },
  { href: "/purchase-orders.html", label: "Purchase Orders", icon: "clipboardList", roles: ["admin", "cashier", "accountant", "auditor"], section: "Stores" },

  { href: "/pharmacy.html", label: "Pharmacy", icon: "pill", roles: ["admin", "cashier", "accountant", "auditor"], section: "Pharmacy" },

  { href: "/accounts.html", label: "Chart of Accounts", icon: "book", roles: ["admin", "accountant", "auditor"], section: "Accounting" },
  { href: "/charge-items.html", label: "Charge Items", icon: "tag", roles: ["admin", "accountant", "auditor"], section: "Accounting" },
  { href: "/journal.html", label: "Journal Entries", icon: "fileLines", roles: ["admin", "accountant", "auditor"], section: "Accounting" },

  { href: "/trial-balance.html", label: "Trial Balance", icon: "scale", roles: ["admin", "accountant", "auditor"], section: "Reports" },
  { href: "/income-statement.html", label: "Income Statement", icon: "trendingUp", roles: ["admin", "accountant", "auditor"], section: "Reports" },
  { href: "/ar-aging.html", label: "AR Aging", icon: "alertClock", roles: ["admin", "accountant", "auditor"], section: "Reports" },

  { href: "/users.html", label: "Users", icon: "users", roles: ["admin"], section: "Admin" },
  { href: "/branches.html", label: "Branches", icon: "building", roles: ["admin"], section: "Admin" },
  { href: "/audit-log.html", label: "Audit Log", icon: "shield", roles: ["admin", "auditor"], section: "Admin" },
];

function closeSidebar() {
  document.getElementById("sidebar-root")?.classList.remove("open");
  document.getElementById("sidebar-overlay")?.classList.remove("show");
}

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
        return `${label}<a href="${item.href}" class="${currentPath === item.href ? "active" : ""}">${navIcon(item.icon)}<span>${item.label}</span></a>`;
      })
      .join("");
    sidebarRoot.innerHTML = `
      <div class="brand">
        <span class="brand-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 3v18M3 12h18" stroke="#fff" stroke-width="3" stroke-linecap="round" />
          </svg>
        </span>
        <span>Hospital Finance</span>
      </div>
      <nav>${links}</nav>
    `;
    if (!document.getElementById("sidebar-overlay")) {
      const overlay = document.createElement("div");
      overlay.id = "sidebar-overlay";
      overlay.className = "sidebar-overlay";
      overlay.addEventListener("click", closeSidebar);
      document.body.appendChild(overlay);
    }
    if (!document.getElementById("menu-toggle-btn")) {
      const toggle = document.createElement("button");
      toggle.id = "menu-toggle-btn";
      toggle.className = "menu-toggle";
      toggle.type = "button";
      toggle.setAttribute("aria-label", "Toggle menu");
      toggle.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>`;
      toggle.addEventListener("click", () => {
        document.getElementById("sidebar-root")?.classList.toggle("open");
        document.getElementById("sidebar-overlay")?.classList.toggle("show");
      });
      document.body.appendChild(toggle);
    }
    sidebarRoot.querySelectorAll("nav a").forEach((a) => a.addEventListener("click", closeSidebar));
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
