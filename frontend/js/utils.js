/**
 * Utility functions for the dashboard.
 */
const Utils = {
  formatCurrency(val) {
    if (val == null) return "N/A";
    return "$" + Number(val).toFixed(2);
  },

  formatPercent(val) {
    if (val == null) return "N/A";
    const sign = val > 0 ? "+" : "";
    return `${sign}${Number(val).toFixed(1)}%`;
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

  getPlatformColor(platform) {
    const colors = {
      instore: '#3b82f6',
      ubereats: '#1db954',
      doordash: '#ff3008',
      grubhub: '#f97316',
    };
    return colors[platform] || '#888';
  },

  getPlatformLabel(platform) {
    const labels = {
      instore: 'In-Store',
      ubereats: 'Uber Eats',
      doordash: 'DoorDash',
      grubhub: 'Grubhub',
    };
    return labels[platform] || platform;
  },

  getBadgeClass(winner) {
    if (winner === "client") return "badge-client";
    if (winner === "competitor") return "badge-competitor";
    if (winner === "no_data") return "badge-tie";
    return "badge-tie";
  },

  getBadgeLabel(winner) {
    if (winner === "client") return "✓ Our Restaurant";
    if (winner === "competitor") return "✗ Competitor";
    if (winner === "no_data") return "— No Data";
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
      success: '<i class="fa-solid fa-circle-check icon-inline" aria-hidden="true"></i>',
      warning: '<i class="fa-solid fa-triangle-exclamation icon-inline" aria-hidden="true"></i>',
      error: '<i class="fa-solid fa-circle-xmark icon-inline" aria-hidden="true"></i>',
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

  showEmpty(containerId, message = "No data available") {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `<div class="empty-state"><i class="fa-solid fa-inbox"></i><p>${message}</p></div>`;
  },

  showError(containerId, message = "Failed to load data") {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `<div class="error-state"><i class="fa-solid fa-circle-exclamation"></i><p>${message}</p></div>`;
  },

  // ── Pagination ──────────────────────────────
  paginate(items, page = 1, perPage = 20) {
    const total = items.length;
    const totalPages = Math.ceil(total / perPage);
    const start = (page - 1) * perPage;
    const end = start + perPage;
    return {
      items: items.slice(start, end),
      page,
      totalPages,
      total,
      hasNext: page < totalPages,
      hasPrev: page > 1,
    };
  },

  renderPagination(containerId, pageData, onPageChange) {
    const el = document.getElementById(containerId);
    if (!el || pageData.totalPages <= 1) {
      if (el) el.innerHTML = '';
      return;
    }
    let html = '<div class="pagination">';
    html += `<button class="page-btn" ${pageData.hasPrev ? '' : 'disabled'} onclick="(${onPageChange})(${pageData.page - 1})"><i class="fa-solid fa-chevron-left"></i></button>`;
    const start = Math.max(1, pageData.page - 2);
    const end = Math.min(pageData.totalPages, pageData.page + 2);
    for (let i = start; i <= end; i++) {
      html += `<button class="page-btn ${i === pageData.page ? 'active' : ''}" onclick="(${onPageChange})(${i})">${i}</button>`;
    }
    html += `<button class="page-btn" ${pageData.hasNext ? '' : 'disabled'} onclick="(${onPageChange})(${pageData.page + 1})"><i class="fa-solid fa-chevron-right"></i></button>`;
    html += `<span class="page-info">${pageData.page} of ${pageData.totalPages} (${pageData.total} items)</span>`;
    html += '</div>';
    el.innerHTML = html;
  },

  // ── Debounce ────────────────────────────────
  debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  },

  // ── Sorting helpers ─────────────────────────
  sortItems(items, sortKey) {
    const arr = [...items];
    switch (sortKey) {
      case 'name':
        return arr.sort((a, b) => (a.item_name || '').localeCompare(b.item_name || ''));
      case 'price-low':
        return arr.sort((a, b) => (a.client_price || 999) - (b.client_price || 999));
      case 'price-high':
        return arr.sort((a, b) => (b.client_price || 0) - (a.client_price || 0));
      case 'diff':
        return arr.sort((a, b) => Math.abs(b.price_difference || 0) - Math.abs(a.price_difference || 0));
      case 'markup':
        return arr.sort((a, b) => Math.abs(b.client_markup_pct || 0) - Math.abs(a.client_markup_pct || 0));
      case 'category':
        return arr.sort((a, b) => (a.category || 'zzz').localeCompare(b.category || 'zzz'));
      case 'cheapest':
        return arr.sort((a, b) => (a.price || 999) - (b.price || 999));
      default:
        return arr;
    }
  },

  // ── N/A-safe value ──────────────────────────
  safeVal(val, formatter) {
    if (val == null || val === undefined) return '<span class="na-text">N/A</span>';
    return formatter ? formatter(val) : val;
  },

  // ── Cheapest badge ──────────────────────────
  cheapestBadge(name) {
    if (!name) return '';
    return `<span class="badge-cheapest"><i class="fa-solid fa-trophy icon-inline"></i>${Utils.truncate(name, 20)}</span>`;
  },
};
