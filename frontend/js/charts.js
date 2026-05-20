/**
 * Chart.js visualization module for comparison charts.
 */
const Charts = {
  colors: {
    client: "rgba(31, 157, 100, 0.85)",
    clientBg: "rgba(31, 157, 100, 0.15)",
    competitor: "rgba(224, 82, 82, 0.85)",
    competitorBg: "rgba(224, 82, 82, 0.15)",
    purple: "rgba(242, 105, 34, 0.85)",
    gold: "rgba(244, 154, 61, 0.85)",
    blue: "rgba(59, 130, 246, 0.85)",
    green: "rgba(29, 185, 84, 0.85)",
    red: "rgba(255, 48, 8, 0.85)",
    orange: "rgba(249, 115, 22, 0.85)",
    gridColor: "rgba(31, 27, 22, 0.06)",
    textColor: "#7c746c",
  },

  defaultOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: this.colors.textColor,
            font: { family: "Manrope", size: 12 },
          },
        },
        tooltip: {
          backgroundColor: "rgba(255,255,255,0.97)",
          titleColor: "#1f1b16",
          bodyColor: "#4b4540",
          titleFont: { family: "Manrope", weight: "600" },
          bodyFont: { family: "Manrope" },
          borderColor: "rgba(31,27,22,0.12)",
          borderWidth: 1,
          cornerRadius: 10,
          padding: 14,
        },
      },
      scales: {
        x: {
          ticks: { color: this.colors.textColor, font: { size: 11 } },
          grid: { color: this.colors.gridColor },
        },
        y: {
          ticks: { color: this.colors.textColor, font: { size: 11 } },
          grid: { color: this.colors.gridColor },
        },
      },
    };
  },

  createPriceComparisonChart(canvasId, priceData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const filtered = (priceData.items || [])
      .filter((i) => i.client_price != null && i.competitor_price != null)
      .slice(0, 10);
    if (!filtered.length) return null;
    const labels = filtered.map((i) => i.item);
    const clientPrices = filtered.map((i) => i.client_price);
    const compPrices = filtered.map((i) => i.competitor_price);

    return new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Bawarchi",
            data: clientPrices,
            backgroundColor: this.colors.client,
            borderRadius: 6,
            barPercentage: 0.4,
          },
          {
            label: "Competitor",
            data: compPrices,
            backgroundColor: this.colors.competitor,
            borderRadius: 6,
            barPercentage: 0.4,
          },
        ],
      },
      options: {
        ...this.defaultOptions(),
        plugins: {
          ...this.defaultOptions().plugins,
          title: {
            display: true,
            text: "Price Comparison ($)",
            color: "#1f1b16",
            font: { family: "Sora", size: 15, weight: "600" },
          },
        },
      },
    });
  },

  createScoresRadarChart(canvasId, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = Object.keys(scores).map((k) =>
      k.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
    );
    const values = Object.values(scores);

    return new Chart(ctx, {
      type: "radar",
      data: {
        labels,
        datasets: [
          {
            label: "Client Score",
            data: values,
            borderColor: this.colors.client,
            backgroundColor: this.colors.clientBg,
            pointBackgroundColor: this.colors.client,
            pointBorderColor: "#fff",
            pointRadius: 4,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              color: this.colors.textColor,
              backdropColor: "transparent",
              font: { size: 10 },
            },
            grid: { color: this.colors.gridColor },
            pointLabels: {
              color: this.colors.textColor,
              font: { size: 11, family: "Manrope" },
            },
          },
        },
        plugins: {
          legend: { labels: { color: this.colors.textColor } },
          title: {
            display: true,
            text: "Performance Scores",
            color: "#1f1b16",
            font: { family: "Sora", size: 15, weight: "600" },
          },
        },
      },
    });
  },

  createMenuVarietyChart(canvasId, menuComp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Client Veg", "Client Non-Veg", "Competitor Veg", "Competitor Non-Veg"],
        datasets: [
          {
            data: [
              menuComp.client_veg_items,
              menuComp.client_nonveg_items,
              menuComp.competitor_veg_items,
              menuComp.competitor_nonveg_items,
            ],
            backgroundColor: [this.colors.client, this.colors.blue, this.colors.competitor, this.colors.gold],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: this.colors.textColor, padding: 16, font: { size: 11 } },
          },
          title: {
            display: true,
            text: "Menu Variety",
            color: "#1f1b16",
            font: { family: "Sora", size: 15, weight: "600" },
          },
        },
      },
    });
  },

  createOfferComparisonChart(canvasId, offerComp) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = offerComp.comparison_items.map((i) => i.area);
    const clientData = offerComp.comparison_items.map((i) => (i.client === "Yes" ? 1 : 0));
    const compData = offerComp.comparison_items.map((i) => (i.competitor === "Yes" ? 1 : 0));

    return new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Bawarchi", data: clientData, backgroundColor: this.colors.client, borderRadius: 4 },
          { label: "Competitor", data: compData, backgroundColor: this.colors.competitor, borderRadius: 4 },
        ],
      },
      options: {
        ...this.defaultOptions(),
        indexAxis: "y",
        scales: {
          x: { display: false },
          y: { ticks: { color: this.colors.textColor }, grid: { display: false } },
        },
        plugins: {
          ...this.defaultOptions().plugins,
          title: {
            display: true,
            text: "Offer Coverage",
            color: "#1f1b16",
            font: { family: "Sora", size: 15, weight: "600" },
          },
        },
      },
    });
  },

  createMarketPriceChart(canvasId, restaurants) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const names = restaurants.map((r) => (r.name.length > 15 ? r.name.slice(0, 15) + "…" : r.name)).slice(0, 8);
    const ratings = restaurants.map((r) => r.rating || 0).slice(0, 8);
    const bgColors = restaurants
      .map((r, i) => {
        const hue = 20 + i * 30;
        return `hsla(${hue}, 70%, 55%, 0.75)`;
      })
      .slice(0, 8);

    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: names,
        datasets: [
          {
            label: "Rating",
            data: ratings,
            backgroundColor: bgColors,
            borderRadius: 8,
            barPercentage: 0.6,
          },
        ],
      },
      options: {
        ...this.defaultOptions(),
        plugins: {
          ...this.defaultOptions().plugins,
          title: {
            display: true,
            text: "Competitor Ratings",
            color: "#1f1b16",
            font: { family: "Sora", size: 15, weight: "600" },
          },
        },
      },
    });
  },

  destroyAll(chartInstances) {
    if (!chartInstances) return;
    Object.values(chartInstances).forEach((c) => {
      if (c && typeof c.destroy === "function") c.destroy();
    });
  },
};
