/**
 * Main application controller — handles navigation, data loading,
 * and rendering for all dashboard views.
 */
const App = {
  state: {
    restaurants: [],
    searchData: null,
    activeView: "dashboard",
    activeRadius: "all",
    marketCharts: {},
    loaded: {},
  },

  async init() {
    this.bindNavigation();
    this.bindOverlay();
    this.bindGlobalSearch();
    this.bindRefresh();
    this.bindSettings();
    PlatformComparison.bindControls();
    CategoryAnalytics.bindControls();
    await this.loadDashboard();
  },

  // ── Navigation ──────────────────────────────
  bindNavigation() {
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const view = tab.dataset.view;
        this.switchView(view);
      });
    });
  },

  bindOverlay() {
    const overlay = document.getElementById("comparison-overlay");
    if (overlay) {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) Comparison.close();
      });
    }
    const settingsOverlay = document.getElementById("settings-overlay");
    if (settingsOverlay) {
      settingsOverlay.addEventListener("click", (e) => {
        if (e.target === settingsOverlay) AdminConfig.close();
      });
    }
  },

  bindGlobalSearch() {
    const input = document.getElementById("global-search-input");
    if (input) {
      input.addEventListener("input", Utils.debounce((e) => {
        const term = e.target.value.trim();
        if (term && this.state.activeView === "dashboard") {
          const filtered = this.state.restaurants.filter((r) =>
            r.name.toLowerCase().includes(term.toLowerCase()) ||
            (r.address || "").toLowerCase().includes(term.toLowerCase())
          );
          this.renderRestaurantGrid(filtered);
        } else if (!term && this.state.activeView === "dashboard") {
          this.renderRestaurantGrid(this.state.restaurants);
        }
      }, 250));
    }
  },

  bindRefresh() {
    const btn = document.getElementById("btn-refresh");
    if (btn) {
      btn.addEventListener("click", () => {
        this.state.loaded = {};
        this.switchView(this.state.activeView);
        Utils.showToast("Refreshing data...", "info");
      });
    }
  },

  bindSettings() {
    const btn = document.getElementById("btn-settings");
    if (btn) {
      btn.addEventListener("click", () => AdminConfig.open());
    }
  },

  switchView(view) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    const el = document.getElementById(`view-${view}`);
    if (el) el.classList.add("active");
    this.state.activeView = view;

    // Lazy load views
    if (view === "instore" && !this.state.loaded.instore) {
      this.state.loaded.instore = true;
      PlatformComparison.loadInstore();
    }
    if (view === "ubereats" && !this.state.loaded.ubereats) {
      this.state.loaded.ubereats = true;
      PlatformComparison.loadPlatform("ubereats");
    }
    if (view === "doordash" && !this.state.loaded.doordash) {
      this.state.loaded.doordash = true;
      PlatformComparison.loadPlatform("doordash");
    }
    if (view === "grubhub" && !this.state.loaded.grubhub) {
      this.state.loaded.grubhub = true;
      PlatformComparison.loadPlatform("grubhub");
    }
    if (view === "delivery" && !this.state.loaded.delivery) {
      this.state.loaded.delivery = true;
      DeliveryComparison.load();
    }
    if (view === "categories" && !this.state.loaded.categories) {
      this.state.loaded.categories = true;
      CategoryAnalytics.load();
    }
    if (view === "free-delivery" && !this.state.loaded.freeDelivery) {
      this.state.loaded.freeDelivery = true;
      DeliveryComparison.loadFreeDelivery();
    }

    if (view === "recommendations" && !this.state.loaded.recs) {
      this.state.loaded.recs = true;
      this.loadRecommendations();
    }

  },

  // ── Dashboard ───────────────────────────────
  async loadDashboard() {
    Utils.showLoading("restaurant-grid", "Searching nearby Indian restaurants...");
    try {
      const data = await API.searchRestaurants(20);
      this.state.searchData = data;
      this.state.restaurants = data.restaurants || [];
      this.updateStats(data);
      this.renderRestaurantGrid(this.state.restaurants);
      this.renderFilterBar(this.state.restaurants);
      PlatformComparison.populateCompetitorDropdowns(this.state.restaurants);
      Utils.showToast(`Found ${data.competitors_found} competitor restaurants`, "success");
    } catch (e) {
      document.getElementById("restaurant-grid").innerHTML =
        '<p style="color:var(--danger);text-align:center;padding:40px;">Failed to load restaurants. Is the backend running?</p>';
      Utils.showToast("Failed to connect to backend", "error");
    }
  },

  updateStats(data) {
    document.getElementById("stat-competitors").textContent = data.competitors_found || 0;
    document.getElementById("stat-radius").textContent = data.search_radius_used || "20 miles";
    const restaurants = data.restaurants || [];
    const avgRating = restaurants.length
      ? (restaurants.reduce((s, r) => s + (r.rating || 0), 0) / restaurants.length).toFixed(1)
      : "0";
    document.getElementById("stat-avg-rating").textContent = avgRating;
    const platforms = new Set();
    restaurants.forEach((r) => (r.delivery_platforms || []).forEach((p) => platforms.add(p)));
    document.getElementById("stat-platforms").textContent = platforms.size;
  },

  renderFilterBar(restaurants) {
    const container = document.getElementById("filter-bar");
    if (!container) return;
    const groups = new Set(["all"]);
    restaurants.forEach((r) => { if (r.radius_group) groups.add(r.radius_group); });
    container.innerHTML = '<span style="font-size:0.8rem;color:var(--text-muted);margin-right:4px;">Filter:</span>';
    for (const g of groups) {
      const chip = document.createElement("button");
      chip.className = `filter-chip${g === "all" ? " active" : ""}`;
      chip.textContent = g === "all" ? "All" : `≤ ${g}`;
      chip.onclick = () => {
        document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        this.state.activeRadius = g;
        const filtered = g === "all" ? this.state.restaurants : this.state.restaurants.filter((r) => r.radius_group === g);
        this.renderRestaurantGrid(filtered);
      };
      container.appendChild(chip);
    }
  },

  renderRestaurantGrid(restaurants) {
    const grid = document.getElementById("restaurant-grid");
    if (!grid) return;
    if (!restaurants.length) {
      grid.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:40px;">No restaurants found in this radius.</p>';
      return;
    }
    grid.innerHTML = restaurants.map((r, idx) => {
      const realIdx = this.state.restaurants.indexOf(r);
      const ratingStars = "★".repeat(Math.floor(r.rating || 0));
      const deliveryTags = (r.delivery_platforms || []).map((p) => `<span class="delivery-tag">${p}</span>`).join("");
      const topOffer = r.offers && r.offers.length ? r.offers[0].title : "";
      return `<div class="restaurant-card" id="restaurant-card-${realIdx}">
        <div class="card-header">
          <div>
            <div class="restaurant-name">${r.name}</div>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-top:3px;">${Utils.truncate(r.address || "", 50)}</div>
          </div>
          <span class="distance-badge"><i class="fa-solid fa-location-dot icon-inline" aria-hidden="true"></i>${(r.distance_miles || 0).toFixed(1)} mi</span>
        </div>
        <div class="card-meta">
          <span class="rating">${ratingStars} ${(r.rating || 0).toFixed(1)}</span>
          <span><i class="fa-regular fa-message icon-inline" aria-hidden="true"></i>${r.total_reviews || 0} reviews</span>
          <span class="price-cat">${r.price_category || "$$"}</span>
        </div>
        <div class="delivery-tags">${deliveryTags || '<span class="delivery-tag">Dine-in</span>'}</div>
        ${topOffer ? `<div class="card-offers"><i class="fa-solid fa-tag icon-inline" aria-hidden="true"></i>${topOffer}</div>` : ""}
        <button class="btn-compare" onclick="Comparison.open(${realIdx}, '${r.name.replace(/'/g, "\\'")}')">
          <i class="fa-solid fa-scale-balanced icon-inline" aria-hidden="true"></i>Compare With Our Restaurant
        </button>
      </div>`;
    }).join("");
  },



  // ── Recommendations ─────────────────────────
  async loadRecommendations() {
    Utils.showLoading("recs-content", "Generating AI recommendations...");
    try {
      const data = await API.getRecommendations();
      this.renderRecommendations(data);
    } catch (e) {
      document.getElementById("recs-content").innerHTML =
        '<p style="color:var(--danger);padding:20px;">Failed to load recommendations.</p>';
    }
  },

  renderRecommendations(data) {
    const el = document.getElementById("recs-content");
    if (!el) return;
    const sections = [
      { key: "offer_optimization", icon: '<i class="fa-solid fa-bullseye icon-inline" aria-hidden="true"></i>', title: "Offer Optimization" },
      { key: "menu_optimization", icon: '<i class="fa-solid fa-list icon-inline" aria-hidden="true"></i>', title: "Menu Optimization" },
      { key: "sales_optimization", icon: '<i class="fa-solid fa-chart-line icon-inline" aria-hidden="true"></i>', title: "Sales Optimization" },
    ];
    let html = "";
    for (const sec of sections) {
      const sData = data[sec.key];
      if (!sData) continue;
      html += `<div class="rec-section"><h3>${sec.icon}${sec.title}</h3>`;
      for (const [cat, items] of Object.entries(sData)) {
        if (!Array.isArray(items) || !items.length) continue;
        const label = cat.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
        html += `<div class="rec-category"><h4><i class="fa-solid fa-angle-right icon-inline" aria-hidden="true"></i>${label}</h4><div class="rec-tags">`;
        for (const item of items) html += `<span class="rec-tag">${item}</span>`;
        html += `</div></div>`;
      }
      html += `</div>`;
    }
    if (!html) html = '<div class="rec-section"><p>No recommendations available yet.</p></div>';
    el.innerHTML = html;
  },
};

// ── Boot ────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => App.init());
