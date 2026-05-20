/**
 * Delivery Comparison module — handles delivery fee comparison,
 * free delivery thresholds, and total order estimation.
 */
const DeliveryComparison = {
  state: {},
  charts: {},

  async load() {
    Utils.showLoading('delivery-content', 'Comparing delivery fees across platforms...');
    try {
      const data = await API.compareDelivery();
      this.state.delivery = data;
      this.render(data);
    } catch (e) {
      Utils.showError('delivery-content', 'Failed to load delivery comparison');
    }
  },

  render(data) {
    const el = document.getElementById('delivery-content');
    if (!el) return;
    const comparisons = data.comparisons || [];
    const platforms = ['ubereats', 'doordash', 'grubhub'];

    if (!comparisons.length) {
      Utils.showEmpty('delivery-content', 'No delivery data available');
      return;
    }

    let html = '';

    // Chart
    html += `<div class="chart-container" style="height:340px;margin-bottom:24px;">
      <canvas id="delivery-fees-chart"></canvas>
    </div>`;

    // Delivery Fee Table
    html += `<div class="market-section">
      <h3><i class="fa-solid fa-receipt icon-inline"></i>Delivery Fee Breakdown</h3>
      <div class="comparison-table-wrapper">
        <table class="comp-table">
          <thead><tr>
            <th>Restaurant</th>`;
    for (const p of platforms) {
      html += `<th colspan="2" style="text-align:center;border-left:2px solid var(--border);">
        <span style="color:${Utils.getPlatformColor(p)}">${Utils.getPlatformLabel(p)}</span>
      </th>`;
    }
    html += `</tr><tr><th></th>`;
    for (const p of platforms) {
      html += `<th style="border-left:2px solid var(--border);">Del. Fee</th><th>Service</th>`;
    }
    html += `</tr></thead><tbody>`;

    for (const comp of comparisons) {
      html += `<tr><td class="td-item">${comp.restaurant_name}</td>`;
      for (const p of platforms) {
        const fees = (comp.platforms || {})[p] || {};
        html += `<td style="border-left:2px solid var(--border);">${Utils.safeVal(fees.delivery_fee, Utils.formatCurrency)}</td>`;
        html += `<td>${Utils.safeVal(fees.service_fee, Utils.formatCurrency)}</td>`;
      }
      html += `</tr>`;
    }
    html += `</tbody></table></div></div>`;

    // Surge / Tax / Delivery Time Table
    html += `<div class="market-section">
      <h3><i class="fa-solid fa-clock icon-inline"></i>Delivery Details</h3>
      <div class="comparison-table-wrapper">
        <table class="comp-table">
          <thead><tr>
            <th>Restaurant</th><th>Platform</th><th>Surge Fee</th>
            <th>Tax Est.</th><th>Min Order</th><th>Delivery Time</th>
            <th>Total Fees</th>
          </tr></thead><tbody>`;

    for (const comp of comparisons) {
      for (const p of platforms) {
        const fees = (comp.platforms || {})[p] || {};
        const totalFees = this._calcTotalFees(fees);
        html += `<tr>
          <td class="td-item">${comp.restaurant_name}</td>
          <td><span class="platform-badge" style="background:${Utils.getPlatformColor(p)}20;color:${Utils.getPlatformColor(p)};">${Utils.getPlatformLabel(p)}</span></td>
          <td>${Utils.safeVal(fees.surge_fee, Utils.formatCurrency)}</td>
          <td>${Utils.safeVal(fees.tax_estimate, Utils.formatCurrency)}</td>
          <td>${Utils.safeVal(fees.min_order_amount, Utils.formatCurrency)}</td>
          <td>${fees.estimated_delivery_time || 'N/A'}</td>
          <td style="font-weight:700;color:var(--accent-purple);">${Utils.safeVal(totalFees, Utils.formatCurrency)}</td>
        </tr>`;
      }
    }
    html += `</tbody></table></div></div>`;

    el.innerHTML = html;

    // Chart
    setTimeout(() => {
      this._renderDeliveryChart(comparisons, platforms);
    }, 100);
  },

  async loadFreeDelivery() {
    Utils.showLoading('free-delivery-content', 'Loading free delivery thresholds...');
    try {
      const data = await API.getFreeDelivery();
      this.state.freeDelivery = data;
      this.renderFreeDelivery(data);
    } catch (e) {
      Utils.showError('free-delivery-content', 'Failed to load free delivery data');
    }
  },

  renderFreeDelivery(data) {
    const el = document.getElementById('free-delivery-content');
    if (!el) return;
    const thresholds = data.thresholds || [];
    const platforms = ['ubereats', 'doordash', 'grubhub'];

    if (!thresholds.length) {
      Utils.showEmpty('free-delivery-content', 'No free delivery data available');
      return;
    }

    let html = `<div class="chart-container" style="height:300px;margin-bottom:24px;">
      <canvas id="free-delivery-chart"></canvas>
    </div>`;

    html += `<div class="market-section">
      <h3><i class="fa-solid fa-gift icon-inline"></i>Minimum Order for Free Delivery</h3>
      <div class="comparison-table-wrapper">
        <table class="comp-table">
          <thead><tr>
            <th>Restaurant</th>`;
    for (const p of platforms) {
      html += `<th style="color:${Utils.getPlatformColor(p)};">${Utils.getPlatformLabel(p)}</th>`;
    }
    html += `<th>Best Platform</th></tr></thead><tbody>`;

    for (const t of thresholds) {
      const vals = {};
      for (const p of platforms) {
        vals[p] = (t.thresholds || {})[p];
      }
      const validPlatforms = Object.entries(vals).filter(([_, v]) => v != null);
      const best = validPlatforms.length
        ? validPlatforms.reduce((a, b) => a[1] < b[1] ? a : b)
        : null;

      html += `<tr><td class="td-item">${t.restaurant_name}</td>`;
      for (const p of platforms) {
        const val = vals[p];
        const isBest = best && best[0] === p;
        html += `<td style="${isBest ? 'color:var(--success);font-weight:700;' : ''}">${Utils.safeVal(val, Utils.formatCurrency)}</td>`;
      }
      html += `<td>${best ? `<span class="platform-badge" style="background:${Utils.getPlatformColor(best[0])}20;color:${Utils.getPlatformColor(best[0])};">${Utils.getPlatformLabel(best[0])}</span>` : 'N/A'}</td>`;
      html += `</tr>`;
    }
    html += `</tbody></table></div></div>`;

    el.innerHTML = html;

    // Chart
    setTimeout(() => {
      this._renderFreeDeliveryChart(thresholds, platforms);
    }, 100);
  },

  _calcTotalFees(fees) {
    if (!fees) return null;
    const vals = [fees.delivery_fee, fees.service_fee, fees.surge_fee, fees.tax_estimate];
    const valid = vals.filter(v => v != null);
    return valid.length ? valid.reduce((a, b) => a + b, 0) : null;
  },

  _renderDeliveryChart(comparisons, platforms) {
    const ctx = document.getElementById('delivery-fees-chart');
    if (!ctx) return;
    const labels = comparisons.map(c => Utils.truncate(c.restaurant_name, 18));
    const datasets = platforms.map(p => ({
      label: Utils.getPlatformLabel(p),
      data: comparisons.map(c => {
        const fees = (c.platforms || {})[p] || {};
        return this._calcTotalFees(fees) || 0;
      }),
      backgroundColor: Utils.getPlatformColor(p) + '99',
      borderRadius: 6,
      barPercentage: 0.7,
    }));

    new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets },
      options: {
        ...Charts.defaultOptions(),
        plugins: {
          ...Charts.defaultOptions().plugins,
          title: { display: true, text: 'Total Delivery Fees by Platform ($)', color: '#1f1b16', font: { family: 'Sora', size: 15, weight: '600' } },
        },
      },
    });
  },

  _renderFreeDeliveryChart(thresholds, platforms) {
    const ctx = document.getElementById('free-delivery-chart');
    if (!ctx) return;
    const labels = thresholds.map(t => Utils.truncate(t.restaurant_name, 18));
    const datasets = platforms.map(p => ({
      label: Utils.getPlatformLabel(p),
      data: thresholds.map(t => (t.thresholds || {})[p] || 0),
      backgroundColor: Utils.getPlatformColor(p) + '99',
      borderRadius: 6,
      barPercentage: 0.7,
    }));

    new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets },
      options: {
        ...Charts.defaultOptions(),
        plugins: {
          ...Charts.defaultOptions().plugins,
          title: { display: true, text: 'Free Delivery Minimum Order ($)', color: '#1f1b16', font: { family: 'Sora', size: 15, weight: '600' } },
        },
      },
    });
  },

  export() {
    window.open(API.exportUrl('delivery'), '_blank');
  },

  exportFreeDelivery() {
    window.open(API.exportUrl('free-delivery'), '_blank');
  },
};
