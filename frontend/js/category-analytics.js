/**
 * Category Analytics module — category tabs, filtering, sorting,
 * and cross-restaurant category comparison.
 */
const CategoryAnalytics = {
  state: {
    categories: [],
    activeCategory: null,
    data: null,
  },

  async load() {
    Utils.showLoading('categories-content', 'Loading categories...');
    try {
      const catData = await API.listCategories();
      this.state.categories = catData.categories || [];
      this.renderCategoryTabs();
      if (this.state.categories.length) {
        this.state.activeCategory = this.state.categories[0];
        await this.loadCategory(this.state.activeCategory);
      }
    } catch (e) {
      Utils.showError('categories-content', 'Failed to load categories');
    }
  },

  renderCategoryTabs() {
    const el = document.getElementById('category-tabs');
    if (!el) return;
    let html = '';
    for (const cat of this.state.categories) {
      const active = cat === this.state.activeCategory ? 'active' : '';
      html += `<button class="category-tab ${active}" onclick="CategoryAnalytics.selectCategory('${cat.replace(/'/g, "\\'")}')">${cat}</button>`;
    }
    el.innerHTML = html;
  },

  async selectCategory(category) {
    this.state.activeCategory = category;
    this.renderCategoryTabs();
    await this.loadCategory(category);
  },

  async loadCategory(category) {
    Utils.showLoading('categories-content', `Loading ${category} data...`);
    try {
      const platform = document.getElementById('category-platform-select')?.value || 'instore';
      const data = await API.compareCategory(category, platform);
      this.state.data = data;
      this.render(data);
    } catch (e) {
      Utils.showError('categories-content', `Failed to load ${category} data`);
    }
  },

  render(data) {
    const el = document.getElementById('categories-content');
    if (!el) return;

    const restaurants = data.restaurants || [];
    const category = data.category || 'Unknown';
    const platformLabel = data.platform_label || data.platform;
    const sortKey = document.getElementById('category-sort-select')?.value || 'name';

    if (!restaurants.length) {
      Utils.showEmpty('categories-content', `No ${category} items found`);
      return;
    }

    // Chart
    let html = `<div class="chart-container" style="height:300px;margin-bottom:24px;">
      <canvas id="category-chart"></canvas>
    </div>`;

    // Summary cards
    html += `<div class="stats-bar" style="margin-bottom:20px;">`;
    for (const r of restaurants) {
      const items = r.items || [];
      const avgPrice = items.length
        ? items.reduce((s, i) => s + (i.price || 0), 0) / items.length
        : 0;
      html += `<div class="stat-card">
        <div class="stat-label">${Utils.truncate(r.restaurant_name, 25)}</div>
        <div class="stat-value">${r.item_count || 0}</div>
        <div class="stat-sub">${category} items · Avg ${Utils.formatCurrency(avgPrice)}</div>
      </div>`;
    }
    html += `</div>`;

    // Comparison table — restaurants as columns
    const allItems = {};
    for (const r of restaurants) {
      for (const item of (r.items || [])) {
        const key = (item.item_name || '').toLowerCase();
        if (!allItems[key]) {
          allItems[key] = { item_name: item.item_name, category: item.category, is_veg: item.is_veg, restaurants: {} };
        }
        allItems[key].restaurants[r.restaurant_name] = item.price;
      }
    }

    let itemList = Object.values(allItems);
    if (sortKey === 'cheapest') {
      itemList.sort((a, b) => {
        const minA = Math.min(...Object.values(a.restaurants).filter(v => v != null));
        const minB = Math.min(...Object.values(b.restaurants).filter(v => v != null));
        return minA - minB;
      });
    } else {
      itemList.sort((a, b) => (a.item_name || '').localeCompare(b.item_name || ''));
    }

    html += `<div class="market-section">
      <h3><i class="fa-solid fa-table icon-inline"></i>${category} — ${platformLabel} Pricing</h3>
      <div class="comparison-table-wrapper">
        <table class="comp-table">
          <thead><tr><th>Item</th><th>Type</th>`;
    for (const r of restaurants) {
      html += `<th>${Utils.truncate(r.restaurant_name, 18)}</th>`;
    }
    html += `<th>Cheapest</th></tr></thead><tbody>`;

    for (const item of itemList) {
      const prices = {};
      for (const r of restaurants) {
        prices[r.restaurant_name] = item.restaurants[r.restaurant_name];
      }
      const validPrices = Object.entries(prices).filter(([_, v]) => v != null);
      const cheapest = validPrices.length
        ? validPrices.reduce((a, b) => a[1] < b[1] ? a : b)
        : null;

      html += `<tr><td class="td-item">${item.item_name || 'N/A'}</td>`;
      html += `<td>${item.is_veg ? '<span class="veg-badge">Veg</span>' : '<span class="nonveg-badge">Non-Veg</span>'}</td>`;
      for (const r of restaurants) {
        const price = prices[r.restaurant_name];
        const isCheapest = cheapest && cheapest[0] === r.restaurant_name && price != null;
        html += `<td style="${isCheapest ? 'color:var(--success);font-weight:700;' : ''}">${Utils.safeVal(price, Utils.formatCurrency)}</td>`;
      }
      html += `<td>${cheapest ? Utils.cheapestBadge(cheapest[0]) : '<span class="na-text">N/A</span>'}</td>`;
      html += `</tr>`;
    }
    html += `</tbody></table></div></div>`;

    el.innerHTML = html;

    // Chart
    setTimeout(() => {
      this._renderChart(restaurants, category);
    }, 100);
  },

  _renderChart(restaurants, category) {
    const ctx = document.getElementById('category-chart');
    if (!ctx) return;

    const labels = restaurants.map(r => Utils.truncate(r.restaurant_name, 18));
    const avgPrices = restaurants.map(r => {
      const items = r.items || [];
      return items.length ? items.reduce((s, i) => s + (i.price || 0), 0) / items.length : 0;
    });
    const counts = restaurants.map(r => r.item_count || 0);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: `Avg ${category} Price`,
            data: avgPrices,
            backgroundColor: 'rgba(242, 105, 34, 0.75)',
            borderRadius: 6,
            barPercentage: 0.5,
            yAxisID: 'y',
          },
          {
            label: 'Item Count',
            data: counts,
            type: 'line',
            borderColor: 'rgba(59, 130, 246, 0.85)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            pointRadius: 5,
            fill: true,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        ...Charts.defaultOptions(),
        scales: {
          ...Charts.defaultOptions().scales,
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: Charts.colors.textColor },
          },
        },
        plugins: {
          ...Charts.defaultOptions().plugins,
          title: { display: true, text: `${category} — Average Price & Item Count`, color: '#1f1b16', font: { family: 'Sora', size: 15, weight: '600' } },
        },
      },
    });
  },

  bindControls() {
    const platformSelect = document.getElementById('category-platform-select');
    const sortSelect = document.getElementById('category-sort-select');
    if (platformSelect) {
      platformSelect.addEventListener('change', () => {
        if (this.state.activeCategory) this.loadCategory(this.state.activeCategory);
      });
    }
    if (sortSelect) {
      sortSelect.addEventListener('change', () => {
        if (this.state.data) this.render(this.state.data);
      });
    }
  },
};
