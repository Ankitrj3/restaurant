/**
 * Chart.js visualization module for comparison charts.
 */
const Charts = {
  colors: {
    client: 'rgba(34, 214, 122, 0.85)',
    clientBg: 'rgba(34, 214, 122, 0.15)',
    competitor: 'rgba(245, 71, 91, 0.85)',
    competitorBg: 'rgba(245, 71, 91, 0.15)',
    purple: 'rgba(124, 92, 252, 0.85)',
    gold: 'rgba(245, 166, 35, 0.85)',
    blue: 'rgba(78, 168, 246, 0.85)',
    gridColor: 'rgba(255,255,255,0.05)',
    textColor: '#9d9dba',
  },

  defaultOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: this.colors.textColor, font: { family: 'Inter', size: 12 } } },
        tooltip: {
          backgroundColor: 'rgba(13,13,26,0.95)',
          titleFont: { family: 'Inter', weight: '600' },
          bodyFont: { family: 'Inter' },
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 12,
        },
      },
      scales: {
        x: { ticks: { color: this.colors.textColor, font: { size: 11 } }, grid: { color: this.colors.gridColor } },
        y: { ticks: { color: this.colors.textColor, font: { size: 11 } }, grid: { color: this.colors.gridColor } },
      },
    };
  },

  createPriceComparisonChart(canvasId, priceData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = priceData.items.map(i => i.item).slice(0, 10);
    const clientPrices = priceData.items.map(i => i.client_price).slice(0, 10);
    const compPrices = priceData.items.map(i => i.competitor_price).slice(0, 10);

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Bawarchi Biryanis', data: clientPrices, backgroundColor: this.colors.client, borderRadius: 6, barPercentage: 0.4 },
          { label: 'Competitor', data: compPrices, backgroundColor: this.colors.competitor, borderRadius: 6, barPercentage: 0.4 },
        ],
      },
      options: { ...this.defaultOptions(), plugins: { ...this.defaultOptions().plugins, title: { display: true, text: 'Price Comparison ($)', color: '#f0f0f5', font: { family: 'Outfit', size: 15, weight: '600' } } } },
    });
  },

  createScoresRadarChart(canvasId, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = Object.keys(scores).map(k => k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const values = Object.values(scores);

    return new Chart(ctx, {
      type: 'radar',
      data: {
        labels,
        datasets: [{
          label: 'Client Score',
          data: values,
          borderColor: this.colors.client,
          backgroundColor: this.colors.clientBg,
          pointBackgroundColor: this.colors.client,
          pointBorderColor: '#fff',
          pointRadius: 4,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { r: { beginAtZero: true, max: 100, ticks: { color: this.colors.textColor, backdropColor: 'transparent', font: { size: 10 } }, grid: { color: this.colors.gridColor }, pointLabels: { color: this.colors.textColor, font: { size: 11, family: 'Inter' } } } },
        plugins: { legend: { labels: { color: this.colors.textColor } }, title: { display: true, text: 'Performance Scores', color: '#f0f0f5', font: { family: 'Outfit', size: 15, weight: '600' } } },
      },
    });
  },

  createMenuVarietyChart(canvasId, menuComp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Client Veg', 'Client Non-Veg', 'Competitor Veg', 'Competitor Non-Veg'],
        datasets: [{
          data: [menuComp.client_veg_items, menuComp.client_nonveg_items, menuComp.competitor_veg_items, menuComp.competitor_nonveg_items],
          backgroundColor: [this.colors.client, this.colors.blue, this.colors.competitor, this.colors.gold],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { color: this.colors.textColor, padding: 16, font: { size: 11 } } }, title: { display: true, text: 'Menu Variety', color: '#f0f0f5', font: { family: 'Outfit', size: 15, weight: '600' } } },
      },
    });
  },

  createOfferComparisonChart(canvasId, offerComp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = offerComp.comparison_items.map(i => i.area);
    const clientData = offerComp.comparison_items.map(i => i.client === 'Yes' ? 1 : 0);
    const compData = offerComp.comparison_items.map(i => i.competitor === 'Yes' ? 1 : 0);

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Bawarchi Biryanis', data: clientData, backgroundColor: this.colors.client, borderRadius: 4 },
          { label: 'Competitor', data: compData, backgroundColor: this.colors.competitor, borderRadius: 4 },
        ],
      },
      options: {
        ...this.defaultOptions(), indexAxis: 'y',
        scales: { x: { display: false }, y: { ticks: { color: this.colors.textColor }, grid: { display: false } } },
        plugins: { ...this.defaultOptions().plugins, title: { display: true, text: 'Offer Coverage', color: '#f0f0f5', font: { family: 'Outfit', size: 15, weight: '600' } } },
      },
    });
  },

  createMarketPriceChart(canvasId, restaurants) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const names = restaurants.map(r => r.name.length > 15 ? r.name.slice(0,15)+'…' : r.name).slice(0,8);
    const ratings = restaurants.map(r => r.rating || 0).slice(0,8);
    const bgColors = restaurants.map((r, i) => {
      const hue = 250 + i * 25;
      return `hsla(${hue}, 70%, 60%, 0.75)`;
    }).slice(0,8);

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: names,
        datasets: [{ label: 'Rating', data: ratings, backgroundColor: bgColors, borderRadius: 8, barPercentage: 0.6 }],
      },
      options: { ...this.defaultOptions(), plugins: { ...this.defaultOptions().plugins, title: { display: true, text: 'Competitor Ratings', color: '#f0f0f5', font: { family: 'Outfit', size: 15, weight: '600' } } } },
    });
  },

  destroyAll(chartInstances) {
    if (!chartInstances) return;
    Object.values(chartInstances).forEach(c => { if (c && typeof c.destroy === 'function') c.destroy(); });
  }
};
