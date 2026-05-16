/**
 * Main application controller — handles navigation, data loading,
 * and rendering for all dashboard views.
 */
const App = {
  state: {
    restaurants: [],
    searchData: null,
    activeView: 'dashboard',
    activeRadius: 'all',
    marketCharts: {},
  },

  async init() {
    this.bindNavigation();
    this.bindOverlay();
    await this.loadDashboard();
  },

  // ── Navigation ──────────────────────────────
  bindNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const view = tab.dataset.view;
        this.switchView(view);
      });
    });
  },

  bindOverlay() {
    const overlay = document.getElementById('comparison-overlay');
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) Comparison.close();
      });
    }
  },

  switchView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const el = document.getElementById(`view-${view}`);
    if (el) el.classList.add('active');
    this.state.activeView = view;

    if (view === 'market' && !this.state.marketLoaded) this.loadMarketAnalysis();
    if (view === 'recommendations' && !this.state.recsLoaded) this.loadRecommendations();
    if (view === 'pricing' && !this.state.pricingLoaded) this.loadPricingAnalysis();
  },

  // ── Dashboard ───────────────────────────────
  async loadDashboard() {
    Utils.showLoading('restaurant-grid', 'Searching nearby Indian restaurants...');
    try {
      const data = await API.searchRestaurants(20);
      this.state.searchData = data;
      this.state.restaurants = data.restaurants || [];
      this.updateStats(data);
      this.renderRestaurantGrid(this.state.restaurants);
      this.renderFilterBar(this.state.restaurants);
      Utils.showToast(`Found ${data.competitors_found} competitor restaurants`, 'success');
    } catch (e) {
      document.getElementById('restaurant-grid').innerHTML =
        '<p style="color:var(--danger);text-align:center;padding:40px;">Failed to load restaurants. Is the backend running?</p>';
      Utils.showToast('Failed to connect to backend', 'error');
    }
  },

  updateStats(data) {
    document.getElementById('stat-competitors').textContent = data.competitors_found || 0;
    document.getElementById('stat-radius').textContent = data.search_radius_used || '20 miles';

    const restaurants = data.restaurants || [];
    const avgRating = restaurants.length
      ? (restaurants.reduce((s, r) => s + (r.rating || 0), 0) / restaurants.length).toFixed(1)
      : '0';
    document.getElementById('stat-avg-rating').textContent = avgRating;

    const platforms = new Set();
    restaurants.forEach(r => (r.delivery_platforms || []).forEach(p => platforms.add(p)));
    document.getElementById('stat-platforms').textContent = platforms.size;
  },

  renderFilterBar(restaurants) {
    const container = document.getElementById('filter-bar');
    if (!container) return;

    const groups = new Set(['all']);
    restaurants.forEach(r => { if (r.radius_group) groups.add(r.radius_group); });

    container.innerHTML = '<span style="font-size:0.8rem;color:var(--text-muted);margin-right:4px;">Filter:</span>';
    for (const g of groups) {
      const chip = document.createElement('button');
      chip.className = `filter-chip${g === 'all' ? ' active' : ''}`;
      chip.textContent = g === 'all' ? 'All' : `≤ ${g}`;
      chip.onclick = () => {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.state.activeRadius = g;
        const filtered = g === 'all' ? this.state.restaurants : this.state.restaurants.filter(r => r.radius_group === g);
        this.renderRestaurantGrid(filtered);
      };
      container.appendChild(chip);
    }
  },

  renderRestaurantGrid(restaurants) {
    const grid = document.getElementById('restaurant-grid');
    if (!grid) return;

    if (!restaurants.length) {
      grid.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:40px;">No restaurants found in this radius.</p>';
      return;
    }

    grid.innerHTML = restaurants.map((r, idx) => {
      const realIdx = this.state.restaurants.indexOf(r);
      const ratingStars = '★'.repeat(Math.floor(r.rating || 0));
      const deliveryTags = (r.delivery_platforms || []).map(p => `<span class="delivery-tag">${p}</span>`).join('');
      const topOffer = (r.offers && r.offers.length) ? r.offers[0].title : '';

      return `<div class="restaurant-card" id="restaurant-card-${realIdx}">
        <div class="card-header">
          <div>
            <div class="restaurant-name">${r.name}</div>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-top:3px;">${Utils.truncate(r.address || '', 50)}</div>
          </div>
          <span class="distance-badge">📍 ${(r.distance_miles || 0).toFixed(1)} mi</span>
        </div>
        <div class="card-meta">
          <span class="rating">${ratingStars} ${(r.rating || 0).toFixed(1)}</span>
          <span>📝 ${r.total_reviews || 0} reviews</span>
          <span class="price-cat">${r.price_category || '$$'}</span>
        </div>
        <div class="delivery-tags">${deliveryTags || '<span class="delivery-tag">Dine-in</span>'}</div>
        ${topOffer ? `<div class="card-offers">🏷️ ${topOffer}</div>` : ''}
        <button class="btn-compare" onclick="Comparison.open(${realIdx}, '${r.name.replace(/'/g, "\\'")}')">
          ⚔️ Compare With Our Restaurant
        </button>
      </div>`;
    }).join('');
  },

  // ── Market Analysis ─────────────────────────
  async loadMarketAnalysis() {
    Utils.showLoading('market-content', 'Generating market analysis...');
    try {
      const data = await API.getMarketAnalysis();
      this.state.marketLoaded = true;
      this.renderMarketAnalysis(data);
    } catch (e) {
      document.getElementById('market-content').innerHTML =
        '<p style="color:var(--danger);padding:20px;">Failed to load market analysis.</p>';
    }
  },

  renderMarketAnalysis(data) {
    const el = document.getElementById('market-content');
    if (!el) return;
    Charts.destroyAll(this.state.marketCharts);

    const ma = data.market_analysis || {};
    let html = `
      <div class="chart-container" style="height:320px;margin-bottom:20px;">
        <canvas id="market-ratings-chart"></canvas>
      </div>
      <div class="market-section">
        <h3>📈 Market Overview</h3>
        <div class="market-grid">
          <div class="market-item"><div class="label">Cheapest Restaurant</div><div class="value">${ma.cheapest_restaurant || 'N/A'}</div></div>
          <div class="market-item"><div class="label">Premium Restaurant</div><div class="value">${ma.premium_restaurant || 'N/A'}</div></div>
          <div class="market-item"><div class="label">Best Rated</div><div class="value">${ma.best_rated || 'N/A'}</div></div>
          <div class="market-item"><div class="label">Most Discounted</div><div class="value">${ma.most_discounted || 'N/A'}</div></div>
        </div>
      </div>`;

    const patterns = ma.common_pricing_patterns || [];
    const trends = ma.customer_trends || [];
    if (patterns.length || trends.length) {
      html += `<div class="market-section"><h3>🔍 Patterns & Trends</h3><div class="chart-row">`;
      if (patterns.length) {
        html += `<div><h4 style="font-size:0.88rem;color:var(--accent-blue);margin-bottom:8px;">Pricing Patterns</h4><ul class="rec-list">`;
        for (const p of patterns) html += `<li>${p}</li>`;
        html += `</ul></div>`;
      }
      if (trends.length) {
        html += `<div><h4 style="font-size:0.88rem;color:var(--accent-gold);margin-bottom:8px;">Customer Trends</h4><ul class="rec-list">`;
        for (const t of trends) html += `<li>${t}</li>`;
        html += `</ul></div>`;
      }
      html += `</div></div>`;
    }
    el.innerHTML = html;

    setTimeout(() => {
      if (this.state.restaurants.length) {
        this.state.marketCharts.ratings = Charts.createMarketPriceChart('market-ratings-chart', this.state.restaurants);
      }
    }, 100);
  },

  // ── Pricing Analysis ────────────────────────
  async loadPricingAnalysis() {
    Utils.showLoading('pricing-content', 'Analyzing pricing strategies...');
    try {
      const data = await API.getPricingAnalysis();
      this.state.pricingLoaded = true;
      this.renderPricingAnalysis(data);
    } catch (e) {
      document.getElementById('pricing-content').innerHTML =
        '<p style="color:var(--danger);padding:20px;">Failed to load pricing analysis.</p>';
    }
  },

  renderPricingAnalysis(data) {
    const el = document.getElementById('pricing-content');
    if (!el) return;

    let html = '';
    const reduce = data.reduce_price || [];
    const increase = data.increase_price || [];

    if (reduce.length) {
      html += `<div class="market-section"><h3>🔻 Consider Reducing Price</h3>
        <table class="comp-table"><thead><tr><th>Item</th><th>Current</th><th>Suggested</th><th>Reason</th></tr></thead><tbody>`;
      for (const r of reduce) {
        html += `<tr><td style="color:var(--text-primary);">${r.item}</td>
          <td style="color:var(--danger);">${Utils.formatCurrency(r.current)}</td>
          <td style="color:var(--success);">${Utils.formatCurrency(r.suggested)}</td>
          <td>${r.reason}</td></tr>`;
      }
      html += `</tbody></table></div>`;
    }

    if (increase.length) {
      html += `<div class="market-section"><h3>🔺 Opportunity to Increase Price</h3>
        <table class="comp-table"><thead><tr><th>Item</th><th>Current</th><th>Suggested</th><th>Reason</th></tr></thead><tbody>`;
      for (const i of increase) {
        html += `<tr><td style="color:var(--text-primary);">${i.item}</td>
          <td>${Utils.formatCurrency(i.current)}</td>
          <td style="color:var(--accent-gold);">${Utils.formatCurrency(i.suggested)}</td>
          <td>${i.reason}</td></tr>`;
      }
      html += `</tbody></table></div>`;
    }

    if (data.summary) {
      html += `<div class="market-section"><h3>📋 Summary</h3><p style="font-size:0.9rem;color:var(--text-secondary);">${data.summary}</p></div>`;
    }

    if (!html) html = '<div class="market-section"><p style="color:var(--text-muted);">All items are competitively priced! 🎉</p></div>';
    el.innerHTML = html;
  },

  // ── Recommendations ─────────────────────────
  async loadRecommendations() {
    Utils.showLoading('recs-content', 'Generating AI recommendations...');
    try {
      const data = await API.getRecommendations();
      this.state.recsLoaded = true;
      this.renderRecommendations(data);
    } catch (e) {
      document.getElementById('recs-content').innerHTML =
        '<p style="color:var(--danger);padding:20px;">Failed to load recommendations.</p>';
    }
  },

  renderRecommendations(data) {
    const el = document.getElementById('recs-content');
    if (!el) return;

    const sections = [
      { key: 'offer_optimization', icon: '🎯', title: 'Offer Optimization' },
      { key: 'menu_optimization', icon: '📋', title: 'Menu Optimization' },
      { key: 'sales_optimization', icon: '📈', title: 'Sales Optimization' },
    ];

    let html = '';
    for (const sec of sections) {
      const sData = data[sec.key];
      if (!sData) continue;
      html += `<div class="rec-section"><h3>${sec.icon} ${sec.title}</h3>`;
      for (const [cat, items] of Object.entries(sData)) {
        if (!Array.isArray(items) || !items.length) continue;
        const label = cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += `<div class="rec-category"><h4>▸ ${label}</h4><div class="rec-tags">`;
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
document.addEventListener('DOMContentLoaded', () => App.init());
