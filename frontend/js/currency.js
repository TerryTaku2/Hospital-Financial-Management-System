function formatMoney(amount, currencyCode) {
  const n = Number(amount);
  return `${currencyCode} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function statusBadge(status) {
  return `<span class="badge ${status}">${status.replace(/_/g, " ")}</span>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}
