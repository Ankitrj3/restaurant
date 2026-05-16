/**
 * Comparison UI module — renders one-to-one comparison panels.
 */
const Comparison = {
  charts: {},

  async open(restaurantIdx, restaurantName) {
    const overlay = document.getElementById('comparison-overlay');
    const panel = document.getElementById('comparison-content');
    if (!overlay || !panel) return;

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    panel.innerHTML = `<div class="loading-container"><div class="spinner"></div><div class="loading-text">Analyzing ${restaurantName}...</div></div>`;

    try {
      const data = await API.getComparison(restaurantIdx);
      this.render(panel, data, restaurantName);
    } catch (e) {
      panel.innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px;">Failed to load comparison. Please try again.</p>`;
    }
  },

  close() {
    const overlay = document.getElementById('comparison-overlay');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
    Charts.destroyAll(this.charts);
    this.charts = {};
  },

  render(panel, data, compName) {
    Charts.destroyAll(this.charts);
    const clientName = 'Bawarchi Biryanis';
    const pc = data.price_comparison || {};
    const oc = data.offer_comparison || {};
    const mc = data.menu_comparison || {};
    const ca = data.customer_attraction || {};
    const scores = data.scores || {};
    const recs = data.recommendations || [];
    const compBetter = data.competitor_better_areas || [];
    const clientBetter = data.client_better_areas || [];

    let html = `
      <button class="close-btn" onclick="Comparison.close()" title="Close">✕</button>
      <div class="comparison-header">
        <h2>🔍 One-to-One Comparison</h2>
        <div class="vs-badge">
          <strong>${clientName}</strong>
          <span class="vs">VS</span>
          <strong>${compName}</strong>
        </div>
      </div>`;

    // Price Comparison
    html += `<div class="comp-section">
      <h3>💰 Price Comparison</h3>
      <div class="chart-container" style="height:320px;margin-bottom:16px;">
        <canvas id="comp-price-chart"></canvas>
      </div>
      <table class="comp-table"><thead><tr>
        <th>Item</th><th>${clientName}</th><th>${compName}</th><th>Diff</th><th>Better Value</th>
      </tr></thead><tbody>`;
    for (const item of (pc.items || []).slice(0, 12)) {
      html += `<tr>
        <td style="color:var(--text-primary);font-weight:500;">${item.item}</td>
        <td>${Utils.formatCurrency(item.client_price)}</td>
        <td>${Utils.formatCurrency(item.competitor_price)}</td>
        <td style="color:${item.difference > 0 ? 'var(--danger)' : 'var(--success)'};">${item.difference > 0 ? '+' : ''}${Utils.formatCurrency(Math.abs(item.difference))}</td>
        <td><span class="badge-better ${Utils.getBadgeClass(item.better_value)}">${Utils.getBadgeLabel(item.better_value)}</span></td>
      </tr>`;
    }
    html += `</tbody></table>
      <p style="margin-top:10px;font-size:0.82rem;color:var(--text-muted);">${pc.summary || ''}</p>
    </div>`;

    // Offer Comparison
    html += `<div class="comp-section">
      <h3>🎯 Offer Comparison</h3>
      <div class="chart-row"><div class="chart-container" style="height:280px;">
        <canvas id="comp-offer-chart"></canvas>
      </div><div class="chart-container" style="height:280px;">
        <canvas id="comp-menu-chart"></canvas>
      </div></div>
      <table class="comp-table" style="margin-top:16px;"><thead><tr>
        <th>Area</th><th>${clientName}</th><th>${compName}</th><th>Winner</th>
      </tr></thead><tbody>`;
    for (const item of (oc.comparison_items || [])) {
      html += `<tr>
        <td style="color:var(--text-primary);">${item.area}</td>
        <td>${item.client}</td><td>${item.competitor}</td>
        <td><span class="badge-better ${Utils.getBadgeClass(item.winner)}">${Utils.getBadgeLabel(item.winner)}</span></td>
      </tr>`;
    }
    html += `</tbody></table></div>`;

    // Menu Variety
    html += `<div class="comp-section">
      <h3>📋 Menu Variety Comparison</h3>
      <div class="scores-grid" style="margin-bottom:16px;">
        <div class="score-card"><div class="score-label">${clientName} Items</div><div class="score-value" style="color:var(--success);">${mc.client_total_items || 0}</div></div>
        <div class="score-card"><div class="score-label">${compName} Items</div><div class="score-value" style="color:var(--danger);">${mc.competitor_total_items || 0}</div></div>
        <div class="score-card"><div class="score-label">Client Veg / Non-Veg</div><div class="score-value" style="color:var(--accent-blue);font-size:1.3rem;">${mc.client_veg_items || 0} / ${mc.client_nonveg_items || 0}</div></div>
        <div class="score-card"><div class="score-label">Competitor Veg / Non-Veg</div><div class="score-value" style="color:var(--accent-gold);font-size:1.3rem;">${mc.competitor_veg_items || 0} / ${mc.competitor_nonveg_items || 0}</div></div>
      </div>`;
    if ((mc.unique_to_competitor || []).length > 0) {
      html += `<p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:6px;">🔸 Unique to competitor: <strong>${mc.unique_to_competitor.join(', ')}</strong></p>`;
    }
    if ((mc.unique_to_client || []).length > 0) {
      html += `<p style="font-size:0.85rem;color:var(--text-secondary);">🔹 Unique to client: <strong>${mc.unique_to_client.join(', ')}</strong></p>`;
    }
    html += `</div>`;

    // Performance Scores
    html += `<div class="comp-section">
      <h3>📊 Performance Scores</h3>
      <div class="chart-container" style="height:340px;margin-bottom:16px;">
        <canvas id="comp-radar-chart"></canvas>
      </div>
      <div class="scores-grid">`;
    for (const [key, val] of Object.entries(scores)) {
      const color = Utils.getScoreColor(val);
      html += `<div class="score-card">
        <div class="score-label">${key.replace(/_/g, ' ')}</div>
        <div class="score-value" style="color:${color};">${val}</div>
        <div class="score-bar"><div class="score-fill" style="width:${val}%;background:${color};"></div></div>
      </div>`;
    }
    html += `</div></div>`;

    // Areas Analysis
    if (compBetter.length || clientBetter.length) {
      html += `<div class="comp-section"><h3>⚡ Advantage Analysis</h3><div class="chart-row">`;
      if (clientBetter.length) {
        html += `<div><h4 style="color:var(--success);font-size:0.9rem;margin-bottom:8px;">✅ Where We Excel</h4><ul class="rec-list">`;
        for (const a of clientBetter) html += `<li style="border-left:3px solid var(--success);">${a}</li>`;
        html += `</ul></div>`;
      }
      if (compBetter.length) {
        html += `<div><h4 style="color:var(--danger);font-size:0.9rem;margin-bottom:8px;">🚨 Where Competitor is Better</h4><ul class="rec-list">`;
        for (const a of compBetter) html += `<li style="border-left:3px solid var(--danger);">${a}</li>`;
        html += `</ul></div>`;
      }
      html += `</div></div>`;
    }

    // Recommendations
    if (recs.length) {
      html += `<div class="comp-section"><h3>💡 AI Recommendations</h3><ul class="rec-list">`;
      for (const r of recs) html += `<li>${r}</li>`;
      html += `</ul></div>`;
    }

    panel.innerHTML = html;

    // Initialize charts after DOM update
    setTimeout(() => {
      if (pc.items && pc.items.length) this.charts.price = Charts.createPriceComparisonChart('comp-price-chart', pc);
      if (oc.comparison_items) this.charts.offer = Charts.createOfferComparisonChart('comp-offer-chart', oc);
      if (mc.client_total_items) this.charts.menu = Charts.createMenuVarietyChart('comp-menu-chart', mc);
      if (Object.keys(scores).length) this.charts.radar = Charts.createScoresRadarChart('comp-radar-chart', scores);
    }, 100);
  }
};
