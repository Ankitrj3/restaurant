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

      // Build source URL row
      const dsi = comp.data_source_info || {};
      const isLive = dsi.is_live_grounded_data;
      const srcBadge = isLive
        ? `<span class="stat-pill success" style="font-size:0.7rem;">LIVE</span>`
        : `<span class="stat-pill" style="background:rgba(124,116,108,0.25);color:var(--text-muted);font-size:0.7rem;">ESTIMATED</span>`;

      // Collect all clickable source URLs
      const allUrls = [
        ...(dsi.client_sources?.grounding_urls || []),
        ...(dsi.competitor_sources?.grounding_urls || []),
        ...(dsi.all_platform_urls || []),
      ].filter((u, i, arr) => u.url && arr.findIndex(x => x.url === u.url) === i).slice(0, 3);

      let sourceLinksHtml = '';
      if (allUrls.length > 0) {
        sourceLinksHtml = allUrls.map(u => {
          const label = u.title
            ? (u.title.length > 40 ? u.title.slice(0, 40) + '…' : u.title)
            : u.url.replace(/https?:\/\//, '').split('/')[0];
          return `<a href="${u.url}" target="_blank" rel="noopener"
                     style="color:var(--accent-blue);font-size:0.75rem;margin-right:8px;white-space:nowrap;"
                     title="${u.url}">↗ ${label}</a>`;
        }).join('');
      } else {
        const regUrl = dsi.registry_url || '/api/data-sources';
        sourceLinksHtml = `<a href="${regUrl}" target="_blank" rel="noopener"
           style="color:var(--text-muted);font-size:0.75rem;" title="No grounding URLs yet — check after Gemini fetches live data">
           No source URLs yet ↗</a>`;
      }

      const srcType = Array.isArray(dsi.data_source)
        ? dsi.data_source.join(', ')
        : (dsi.data_source || 'unknown');

      // Build platform link buttons
      let platformLinksHtml = '';
      let compLabel = `vs ${compName}`;
      let clientHeader = clientName;
      let compHeader = compName;

      if (platform === 'instore') {
        // For in-store, show Google Maps verification links
        const clientMapsUrl = `https://www.google.com/maps/search/${encodeURIComponent(clientName)}`;
        const compMapsUrl = `https://www.google.com/maps/search/${encodeURIComponent(compName)}`;
        platformLinksHtml = `
          <div class="platform-links-row" style="margin-bottom: 12px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
            <span style="font-size:0.75rem;color:var(--text-muted);font-weight:600;">📍 Verify in-store prices:</span>
            <a href="${clientMapsUrl}" target="_blank" rel="noopener" class="platform-link-btn instore-link" style="text-decoration: none;">
              <i class="fa-solid fa-store"></i> ${clientName} on Maps
            </a>
            <a href="${compMapsUrl}" target="_blank" rel="noopener" class="platform-link-btn instore-link" style="text-decoration: none; opacity: 0.85;">
              <i class="fa-solid fa-store"></i> ${compName} on Maps
            </a>
          </div>
        `;
      } else {
        const platformLabel = Utils.getPlatformLabel(platform);
        const clientUrl = dsi.client_platform_url;
        const competitorUrl = dsi.competitor_platform_url;

        if (clientUrl) {
          clientHeader = `<a href="${clientUrl}" target="_blank" rel="noopener" class="restaurant-platform-link" title="Open ${clientName} on ${platformLabel}">
            ${clientName} <i class="fa-solid fa-up-right-from-square" style="font-size:0.8em; margin-left:2px;"></i>
          </a>`;
        }
        if (competitorUrl) {
          compHeader = `<a href="${competitorUrl}" target="_blank" rel="noopener" class="restaurant-platform-link" title="Open ${compName} on ${platformLabel}">
            ${compName} <i class="fa-solid fa-up-right-from-square" style="font-size:0.8em; margin-left:2px;"></i>
          </a>`;
          compLabel = `<a href="${competitorUrl}" target="_blank" rel="noopener" class="restaurant-platform-link" title="Open ${compName} on ${platformLabel}">
            vs ${compName} <i class="fa-solid fa-up-right-from-square" style="font-size:0.8em; margin-left:2px;"></i>
          </a>`;
        }

        // Render prominent View on [Platform] buttons
        platformLinksHtml = `
          <div class="platform-links-row" style="margin-bottom: 12px; display: flex; gap: 10px; flex-wrap: wrap;">
            ${clientUrl ? `
              <a href="${clientUrl}" target="_blank" rel="noopener" class="platform-link-btn ${platform}-link" style="text-decoration: none;">
                <i class="fa-solid fa-up-right-from-square"></i> View ${clientName} on ${platformLabel}
              </a>
            ` : ''}
            ${competitorUrl ? `
              <a href="${competitorUrl}" target="_blank" rel="noopener" class="platform-link-btn ${platform}-link" style="text-decoration: none;">
                <i class="fa-solid fa-up-right-from-square"></i> View ${compName} on ${platformLabel}
              </a>
            ` : ''}
          </div>
        `;
      }

      html += `<div class="comparison-summary">
        ${platformLinksHtml}
        <div class="summary-card">
          <div class="summary-label">${compLabel}</div>
          <div class="summary-stats">
            <span class="stat-pill success">${comp.client_cheaper_count || 0} items cheaper</span>
            <span class="stat-pill danger">${comp.competitor_cheaper_count || 0} items more expensive</span>
            <span class="stat-pill info">${comp.total_matched || 0} items compared</span>
          </div>
          <div class="summary-avgs">
            <span>Our Avg: ${Utils.formatCurrency(comp.client_avg_price)}</span>
            <span>Their Avg: ${Utils.formatCurrency(comp.competitor_avg_price)}</span>
          </div>
          <div style="margin-top:8px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;
                      padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);">
            ${srcBadge}
            <span style="font-size:0.72rem;color:var(--text-muted);">${srcType}</span>
            <span style="margin-left:auto;display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
              ${sourceLinksHtml}
            </span>
          </div>
          ${dsi.note ? `<div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px;">${dsi.note}</div>` : ''}
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
            <th>${clientHeader}</th><th>${compHeader}</th>
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
