/**
 * Platform Comparison module — handles in-store, Uber Eats, DoorDash,
 * Grubhub comparison views, plus platform-vs-platform and restaurant-vs-restaurant.
 */
const PlatformComparison = {
  state: {},
  charts: {},

  async loadInstore() {
    const contentId = 'instore-content';
    Utils.showLoading(contentId, 'Comparing in-store prices...');
    try {
      const competitor = document.getElementById('instore-competitor-select')?.value || '';
      const data = await API.compareInstore(competitor || undefined);
      this.state.instore = data;
      this.renderComparison('instore', data);
    } catch (e) {
      Utils.showError(contentId, 'Failed to load in-store comparison');
    }
  },

  async loadPlatform(platform) {
    const contentId = `${platform}-content`;
    Utils.showLoading(contentId, `Comparing ${Utils.getPlatformLabel(platform)} prices...`);
    try {
      const competitor = document.getElementById(`${platform}-competitor-select`)?.value || '';
      const data = await API.comparePlatform(platform, competitor || undefined);
      this.state[platform] = data;
      this.renderComparison(platform, data);
    } catch (e) {
      Utils.showError(contentId, `Failed to load ${Utils.getPlatformLabel(platform)} comparison`);
    }
  },

  renderComparison(platform, data) {
    const contentId = `${platform}-content`;
    const el = document.getElementById(contentId);
    if (!el) return;

    // Handle array (multiple competitors) vs single comparison
    const comparisons = Array.isArray(data) ? data : [data];
    if (!comparisons.length || !comparisons[0].items) {
      Utils.showEmpty(contentId, 'No comparison data available');
      return;
    }

    let html = '';

    for (const comp of comparisons) {
      const items = comp.items || [];
      const clientName = comp.client_name || 'Bawarchi';
      const compName = comp.competitor_name || 'Competitor';
      const sortKey = document.getElementById(`${platform}-sort-select`)?.value || 'name';
      const searchTerm = (document.getElementById(`${platform}-search`)?.value || '').toLowerCase();

      let filtered = items;
      if (searchTerm) {
        filtered = items.filter(i =>
          (i.item_name || '').toLowerCase().includes(searchTerm) ||
          (i.category || '').toLowerCase().includes(searchTerm)
        );
      }
      const sorted = Utils.sortItems(filtered, sortKey);

      // Summary stats
      html += `<div class="comparison-summary">
        <div class="summary-card">
          <div class="summary-label">vs ${compName}</div>
          <div class="summary-stats">
            <span class="stat-pill success">${comp.client_cheaper_count || 0} items cheaper</span>
            <span class="stat-pill danger">${comp.competitor_cheaper_count || 0} items more expensive</span>
            <span class="stat-pill info">${comp.total_matched || 0} items compared</span>
          </div>
          <div class="summary-avgs">
            <span>Our Avg: ${Utils.formatCurrency(comp.client_avg_price)}</span>
            <span>Their Avg: ${Utils.formatCurrency(comp.competitor_avg_price)}</span>
          </div>
        </div>
      </div>`;

      // Chart
      html += `<div class="chart-container" style="height:300px;margin-bottom:20px;">
        <canvas id="${platform}-price-chart-${comparisons.indexOf(comp)}"></canvas>
      </div>`;

      // Table
      html += `<div class="comparison-table-wrapper">
        <table class="comp-table" id="${platform}-table">
          <thead><tr>
            <th>Item</th><th>Category</th>
            <th>${clientName}</th><th>${compName}</th>
            <th>Difference</th><th>% Diff</th>`;

      if (platform !== 'instore') {
        html += `<th>Markup</th>`;
      }
      html += `<th>Cheaper</th></tr></thead><tbody>`;

      for (const item of sorted) {
        const diff = item.price_difference;
        const diffColor = diff == null ? 'var(--text-muted)' : diff > 0 ? 'var(--danger)' : 'var(--success)';
        const pctColor = item.percentage_difference == null ? '' : item.percentage_difference > 0 ? 'var(--danger)' : 'var(--success)';

        html += `<tr>
          <td class="td-item">${item.item_name || 'N/A'}</td>
          <td><span class="category-pill">${item.category || 'N/A'}</span></td>
          <td>${Utils.safeVal(item.client_price, Utils.formatCurrency)}</td>
          <td>${Utils.safeVal(item.competitor_price, Utils.formatCurrency)}</td>
          <td style="color:${diffColor};font-weight:600;">${Utils.safeVal(diff, v => (v > 0 ? '+' : '') + Utils.formatCurrency(Math.abs(v)))}</td>
          <td style="color:${pctColor};">${Utils.safeVal(item.percentage_difference, Utils.formatPercent)}</td>`;

        if (platform !== 'instore') {
          html += `<td>${Utils.safeVal(item.client_markup_pct, Utils.formatPercent)}</td>`;
        }

        const cheaperName = item.cheaper_restaurant;
        html += `<td>${cheaperName ? Utils.cheapestBadge(cheaperName) : '<span class="na-text">N/A</span>'}</td>`;
        html += `</tr>`;
      }

      html += '</tbody></table></div>';

      // Pagination placeholder
      html += `<div id="${platform}-pagination"></div>`;
    }

    el.innerHTML = html;

    // Render charts
    setTimeout(() => {
      comparisons.forEach((comp, idx) => {
        const chartId = `${platform}-price-chart-${idx}`;
        const items = (comp.items || []).filter(i => i.client_price && i.competitor_price).slice(0, 12);
        if (items.length) {
          Charts.createPriceComparisonChart(chartId, {
            items: items.map(i => ({
              item: i.item_name,
              client_price: i.client_price,
              competitor_price: i.competitor_price,
            }))
          });
        }
      });
    }, 100);
  },

  populateCompetitorDropdowns(restaurants) {
    const platforms = ['instore', 'ubereats', 'doordash', 'grubhub'];
    for (const p of platforms) {
      const select = document.getElementById(`${p}-competitor-select`);
      if (!select) continue;
      select.innerHTML = '<option value="">All Competitors</option>';
      for (const r of restaurants) {
        select.innerHTML += `<option value="${r.name}">${r.name}</option>`;
      }
    }
  },

  bindControls() {
    const platforms = ['instore', 'ubereats', 'doordash', 'grubhub'];
    for (const p of platforms) {
      const sortSelect = document.getElementById(`${p}-sort-select`);
      const searchInput = document.getElementById(`${p}-search`);
      const compSelect = document.getElementById(`${p}-competitor-select`);

      if (sortSelect) {
        sortSelect.addEventListener('change', () => {
          if (this.state[p]) this.renderComparison(p, this.state[p]);
        });
      }
      if (searchInput) {
        searchInput.addEventListener('input', Utils.debounce(() => {
          if (this.state[p]) this.renderComparison(p, this.state[p]);
        }, 250));
      }
      if (compSelect) {
        compSelect.addEventListener('change', () => {
          if (p === 'instore') this.loadInstore();
          else this.loadPlatform(p);
        });
      }
    }
  },

  export(platform) {
    const url = API.exportUrl(platform);
    window.open(url, '_blank');
  },
};
