/**
 * Utility functions for the dashboard.
 */
const Utils = {
  formatCurrency(val) {
    if (val == null) return "N/A";
    return "$" + Number(val).toFixed(2);
  },

  formatRating(r) {
    if (!r) return "N/A";
    const full = Math.floor(r);
    const half = r - full >= 0.5;
    let stars = "★".repeat(full);
    if (half) stars += "½";
    return `${stars} ${Number(r).toFixed(1)}`;
  },

  getScoreColor(score) {
    if (score >= 65) return "var(--success)";
    if (score >= 45) return "var(--warning)";
    return "var(--danger)";
  },

  getBadgeClass(winner) {
    if (winner === "client") return "badge-client";
    if (winner === "competitor") return "badge-competitor";
    return "badge-tie";
  },

  getBadgeLabel(winner) {
    if (winner === "client") return "✓ Our Restaurant";
    if (winner === "competitor") return "✗ Competitor";
    return "— Similar";
  },

  truncate(str, len = 60) {
    if (!str) return "";
    return str.length > len ? str.slice(0, len) + "…" : str;
  },

  showToast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const icons = {
      info: '<i class="fa-solid fa-circle-info icon-inline" aria-hidden="true"></i>',
      success:
        '<i class="fa-solid fa-circle-check icon-inline" aria-hidden="true"></i>',
      warning:
        '<i class="fa-solid fa-triangle-exclamation icon-inline" aria-hidden="true"></i>',
      error:
        '<i class="fa-solid fa-circle-xmark icon-inline" aria-hidden="true"></i>',
    };
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  showLoading(containerId, message = "Loading data...") {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `<div class="loading-container"><div class="spinner"></div><div class="loading-text">${message}</div></div>`;
  },

  clearLoading(containerId) {
    const el = document.getElementById(containerId);
    if (el && el.querySelector(".loading-container")) el.innerHTML = "";
  },
};
