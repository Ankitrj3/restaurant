/**
 * Comparison UI module — renders one-to-one comparison panels.
 */
const Comparison = {
  charts: {},

  async open(restaurantIdx, restaurantName) {
    const overlay = document.getElementById("comparison-overlay");
    const panel = document.getElementById("comparison-content");
    if (!overlay || !panel) return;

    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
    panel.innerHTML = `<div class="loading-container"><div class="spinner"></div><div class="loading-text">Analyzing ${restaurantName}...</div></div>`;

    try {
      const data = await API.getComparison(restaurantIdx);
      this.render(panel, data, restaurantName);
    } catch (e) {
      panel.innerHTML = `<p style="color:var(--danger);text-align:center;padding:40px;">Failed to load comparison. Please try again.</p>`;
    }
  },

  close() {
    const overlay = document.getElementById("comparison-overlay");
    if (overlay) overlay.classList.remove("active");
    document.body.style.overflow = "";
    Charts.destroyAll(this.charts);
    this.charts = {};
  },

  render(panel, data, compName) {
    Charts.destroyAll(this.charts);
    const clientName = "Bawarchi Biryanis";
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
        <h2><i class="fa-solid fa-magnifying-glass icon-inline" aria-hidden="true"></i>One-to-One Comparison</h2>
        <div class="vs-badge">
          <strong>${clientName}</strong>
          <span class="vs">VS</span>
          <strong>${compName}</strong>
        </div>
      </div>`;

    // Price Comparison
    html += `<div class="comp-section">
      <h3><i class="fa-solid fa-tags icon-inline" aria-hidden="true"></i>Price Comparison</h3>
      <div class="chart-container" style="height:320px;margin-bottom:16px;">
        <canvas id="comp-price-chart"></canvas>
      </div>
      <table class="comp-table"><thead><tr>
        <th>Item</th><th>${clientName}</th><th>${compName}</th><th>Diff</th><th>Better Value</th>
      </tr></thead><tbody>`;
    for (const item of (pc.items || []).slice(0, 12)) {
      const clientPrice = item.client_price;
      const competitorPrice = item.competitor_price;
      const hasPrices = clientPrice != null && competitorPrice != null;
      const diffValue = hasPrices ? item.difference : null;
      const betterValue = hasPrices ? item.better_value : "no_data";
      html += `<tr>
        <td style="color:var(--text-primary);font-weight:500;">${item.item}</td>
        <td>${Utils.formatCurrency(clientPrice)}</td>
        <td>${Utils.formatCurrency(competitorPrice)}</td>
        <td style="color:${diffValue == null ? "var(--text-muted)" : diffValue > 0 ? "var(--danger)" : "var(--success)"};">${diffValue == null ? "N/A" : `${diffValue > 0 ? "+" : ""}${Utils.formatCurrency(Math.abs(diffValue))}`}</td>
        <td><span class="badge-better ${Utils.getBadgeClass(betterValue)}">${Utils.getBadgeLabel(betterValue)}</span></td>
      </tr>`;
    }
    html += `</tbody></table>
      <p style="margin-top:10px;font-size:0.82rem;color:var(--text-muted);">${pc.summary || ""}</p>
    </div>`;

    // Offer Comparison
    html += `<div class="comp-section">
      <h3><i class="fa-solid fa-bullseye icon-inline" aria-hidden="true"></i>Offer Comparison</h3>
      <div class="chart-row"><div class="chart-container" style="height:280px;">
        <canvas id="comp-offer-chart"></canvas>
      </div><div class="chart-container" style="height:280px;">
        <canvas id="comp-menu-chart"></canvas>
      </div></div>
      <table class="comp-table" style="margin-top:16px;"><thead><tr>
        <th>Area</th><th>${clientName}</th><th>${compName}</th><th>Winner</th>
      </tr></thead><tbody>`;
    for (const item of oc.comparison_items || []) {
      html += `<tr>
        <td style="color:var(--text-primary);">${item.area}</td>
        <td>${item.client}</td><td>${item.competitor}</td>
        <td><span class="badge-better ${Utils.getBadgeClass(item.winner)}">${Utils.getBadgeLabel(item.winner)}</span></td>
      </tr>`;
    }
    html += `</tbody></table></div>`;

    // Menu Variety
    html += `<div class="comp-section">
      <h3><i class="fa-solid fa-list icon-inline" aria-hidden="true"></i>Menu Variety Comparison</h3>
      <div class="scores-grid" style="margin-bottom:16px;">
        <div class="score-card"><div class="score-label">${clientName} Items</div><div class="score-value" style="color:var(--success);">${mc.client_total_items || 0}</div></div>
        <div class="score-card"><div class="score-label">${compName} Items</div><div class="score-value" style="color:var(--danger);">${mc.competitor_total_items || 0}</div></div>
        <div class="score-card"><div class="score-label">Client Veg / Non-Veg</div><div class="score-value" style="color:var(--accent-blue);font-size:1.3rem;">${mc.client_veg_items || 0} / ${mc.client_nonveg_items || 0}</div></div>
        <div class="score-card"><div class="score-label">Competitor Veg / Non-Veg</div><div class="score-value" style="color:var(--accent-gold);font-size:1.3rem;">${mc.competitor_veg_items || 0} / ${mc.competitor_nonveg_items || 0}</div></div>
      </div>`;
    if ((mc.unique_to_competitor || []).length > 0) {
      html += `<p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:6px;"><i class="fa-regular fa-circle-dot icon-inline" aria-hidden="true"></i>Unique to competitor: <strong>${mc.unique_to_competitor.join(", ")}</strong></p>`;
    }
    if ((mc.unique_to_client || []).length > 0) {
      html += `<p style="font-size:0.85rem;color:var(--text-secondary);"><i class="fa-regular fa-circle-dot icon-inline" aria-hidden="true"></i>Unique to client: <strong>${mc.unique_to_client.join(", ")}</strong></p>`;
    }
    html += `</div>`;

    // Performance Scores
    html += `<div class="comp-section">
      <h3><i class="fa-solid fa-chart-pie icon-inline" aria-hidden="true"></i>Performance Scores</h3>
      <div class="chart-container" style="height:340px;margin-bottom:16px;">
        <canvas id="comp-radar-chart"></canvas>
      </div>
      <div class="scores-grid">`;
    for (const [key, val] of Object.entries(scores)) {
      const color = Utils.getScoreColor(val);
      html += `<div class="score-card">
        <div class="score-label">${key.replace(/_/g, " ")}</div>
        <div class="score-value" style="color:${color};">${val}</div>
        <div class="score-bar"><div class="score-fill" style="width:${val}%;background:${color};"></div></div>
      </div>`;
    }
    html += `</div></div>`;

    // Areas Analysis
    if (compBetter.length || clientBetter.length) {
      html += `<div class="comp-section"><h3><i class="fa-solid fa-bolt icon-inline" aria-hidden="true"></i>Advantage Analysis</h3><div class="chart-row">`;
      if (clientBetter.length) {
        html += `<div><h4 style="color:var(--success);font-size:0.9rem;margin-bottom:8px;"><i class="fa-solid fa-circle-check icon-inline" aria-hidden="true"></i>Where We Excel</h4><ul class="rec-list">`;
        for (const a of clientBetter)
          html += `<li style="border-left:3px solid var(--success);">${a}</li>`;
        html += `</ul></div>`;
      }
      if (compBetter.length) {
        html += `<div><h4 style="color:var(--danger);font-size:0.9rem;margin-bottom:8px;"><i class="fa-solid fa-triangle-exclamation icon-inline" aria-hidden="true"></i>Where Competitor is Better</h4><ul class="rec-list">`;
        for (const a of compBetter)
          html += `<li style="border-left:3px solid var(--danger);">${a}</li>`;
        html += `</ul></div>`;
      }
      html += `</div></div>`;
    }

    // Recommendations
    if (recs.length) {
      html += `<div class="comp-section"><h3><i class="fa-solid fa-lightbulb icon-inline" aria-hidden="true"></i>AI Recommendations</h3><ul class="rec-list">`;
      for (const r of recs) html += `<li>${r}</li>`;
      html += `</ul></div>`;
    }

    // ── Data Sources panel ──────────────────────────────────
    const ds = data.data_sources || {};
    const clientDs = ds.client || {};
    const compDs = ds.competitor || {};

    const renderSourceCard = (info, label) => {
      if (!info || !info.name) return '';
      const srcBadge = info.is_live_data
        ? `<span style="background:#1f9d64;color:#fff;padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:700;">LIVE</span>`
        : `<span style="background:#7c746c;color:#fff;padding:2px 8px;border-radius:12px;font-size:0.72rem;font-weight:700;">ESTIMATED</span>`;

      const typeList = (info.source_types || []).join(', ') || 'unknown';

      let linksHtml = '';
      if (info.website_url) {
        linksHtml += `<div style="margin-top:6px;">
          <i class="fa-solid fa-globe" style="color:var(--accent-blue);margin-right:4px;font-size:0.8rem;" aria-hidden="true"></i>
          <a href="${info.website_url}" target="_blank" rel="noopener"
             style="color:var(--accent-blue);font-size:0.82rem;word-break:break-all;"
             title="Restaurant website used for menu scraping">${info.website_url}</a>
        </div>`;
      }

      if ((info.grounding_urls || []).length > 0) {
        linksHtml += `<div style="margin-top:8px;font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;">
          <i class="fa-brands fa-google" aria-hidden="true"></i> Gemini searched these pages:
        </div>`;
        for (const src of info.grounding_urls.slice(0, 5)) {
          const dispTitle = src.title || src.url;
          linksHtml += `<div style="margin:3px 0 3px 12px;display:flex;align-items:flex-start;gap:6px;">
            <i class="fa-solid fa-link" style="color:var(--accent-gold);font-size:0.72rem;margin-top:3px;flex-shrink:0;" aria-hidden="true"></i>
            <a href="${src.url}" target="_blank" rel="noopener"
               style="color:var(--accent-gold);font-size:0.78rem;word-break:break-all;"
               title="${src.url}">${dispTitle.length > 70 ? dispTitle.slice(0, 70) + '…' : dispTitle}</a>
          </div>`;
        }
      }

      if (!info.website_url && (info.grounding_urls || []).length === 0) {
        linksHtml = `<div style="margin-top:6px;font-size:0.8rem;color:var(--text-muted);">
          <i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i>
          No source URLs available — data generated from AI estimates.
          <a href="/api/data-sources" target="_blank" style="color:var(--accent-blue);margin-left:4px;">Check /api/data-sources</a>
        </div>`;
      }

      return `
        <div style="background:var(--card-bg,#1e1a16);border:1px solid rgba(255,255,255,0.08);
                    border-radius:10px;padding:14px 16px;flex:1;min-width:220px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:0.82rem;font-weight:700;color:var(--text-secondary);">${label}</span>
            ${srcBadge}
          </div>
          <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;">
            Source: <code style="font-size:0.75rem;">${typeList}</code>
          </div>
          <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:2px;">${info.note || ''}</div>
          ${linksHtml}
        </div>`;
    };

    const clientCard = renderSourceCard(clientDs, clientName);
    const compCard = renderSourceCard(compDs, compName);

    if (clientCard || compCard) {
      html += `
        <details class="comp-section" style="cursor:pointer;" id="data-sources-details">
          <summary style="list-style:none;display:flex;align-items:center;gap:8px;
                          padding:0 0 6px;font-size:0.95rem;font-weight:600;color:var(--text-secondary);">
            <i class="fa-solid fa-database icon-inline" aria-hidden="true"></i>
            Data Sources
            <span style="font-size:0.75rem;font-weight:400;color:var(--text-muted);margin-left:auto;">
              Click to verify prices ↗
            </span>
          </summary>
          <p style="font-size:0.78rem;color:var(--text-muted);margin:4px 0 12px;">
            These are the URLs Gemini searched to populate the comparison data.
            Click any link to verify the prices directly on the source page.
          </p>
          <div style="display:flex;flex-wrap:wrap;gap:14px;">
            ${clientCard}
            ${compCard}
          </div>
        </details>`;
    }

    panel.innerHTML = html;

    // Initialize charts after DOM update
    setTimeout(() => {
      if (pc.items && pc.items.length)
        this.charts.price = Charts.createPriceComparisonChart(
          "comp-price-chart",
          pc,
        );
      if (oc.comparison_items)
        this.charts.offer = Charts.createOfferComparisonChart(
          "comp-offer-chart",
          oc,
        );
      if (mc.client_total_items)
        this.charts.menu = Charts.createMenuVarietyChart("comp-menu-chart", mc);
      if (Object.keys(scores).length)
        this.charts.radar = Charts.createScoresRadarChart(
          "comp-radar-chart",
          scores,
        );
    }, 100);
  },
};
