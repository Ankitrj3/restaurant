/**
 * REST API client for the Restaurant Competitor Intelligence Platform.
 * Includes request deduplication and error handling.
 */
const API = {
  BASE: '',
  _inflight: {},

  async get(endpoint) {
    // Request deduplication — prevent duplicate concurrent calls
    if (this._inflight[endpoint]) {
      return this._inflight[endpoint];
    }
    const promise = (async () => {
      try {
        const resp = await fetch(`${this.BASE}${endpoint}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
      } catch (e) {
        console.error(`[API] GET ${endpoint} failed:`, e);
        throw e;
      } finally {
        delete this._inflight[endpoint];
      }
    })();
    this._inflight[endpoint] = promise;
    return promise;
  },

  async post(endpoint, data) {
    try {
      const resp = await fetch(`${this.BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.error(`[API] POST ${endpoint} failed:`, e);
      throw e;
    }
  },

  // ── Existing endpoints ──────────────────────────
  async searchRestaurants(radius = 20) {
    return this.get(`/api/restaurants/search?radius=${radius}`);
  },
  async getClientMenu() {
    return this.get('/api/client/menu');
  },
  async getComparison(restaurantIdx) {
    return this.get(`/api/comparison/${restaurantIdx}`);
  },

  async getRecommendations() {
    return this.get('/api/analysis/recommendations');
  },
  async healthCheck() {
    return this.get('/api/health');
  },

  // ── New platform endpoints ──────────────────────
  async listRestaurants() {
    return this.get('/api/restaurants/list');
  },
  async listCategories(restaurant) {
    const qs = restaurant ? `?restaurant=${encodeURIComponent(restaurant)}` : '';
    return this.get(`/api/categories${qs}`);
  },
  async listPlatforms() {
    return this.get('/api/platforms');
  },
  async getPlatformMenu(restaurant, platform) {
    return this.get(`/api/platforms/menu?restaurant=${encodeURIComponent(restaurant)}&platform=${platform}`);
  },

  // ── Comparison endpoints ────────────────────────
  async compareInstore(competitor) {
    const qs = competitor ? `?competitor=${encodeURIComponent(competitor)}` : '';
    return this.get(`/api/comparison/instore${qs}`);
  },
  async comparePlatform(platform, competitor) {
    const qs = competitor ? `?competitor=${encodeURIComponent(competitor)}` : '';
    return this.get(`/api/comparison/platform/${platform}${qs}`);
  },
  async comparePlatformToPlatform(restaurant) {
    const qs = restaurant ? `?restaurant=${encodeURIComponent(restaurant)}` : '';
    return this.get(`/api/comparison/platform-vs-platform${qs}`);
  },
  async compareRestaurantToRestaurant(restaurants, platform) {
    const rParam = restaurants ? `&restaurants=${encodeURIComponent(restaurants.join(','))}` : '';
    return this.get(`/api/comparison/restaurant-vs-restaurant?platform=${platform}${rParam}`);
  },

  // ── Delivery endpoints ──────────────────────────
  async compareDelivery() {
    return this.get('/api/comparison/delivery');
  },
  async getDeliveryFees() {
    return this.get('/api/platforms/delivery-fees');
  },
  async getFreeDelivery() {
    return this.get('/api/platforms/free-delivery');
  },

  // ── Category endpoints ──────────────────────────
  async compareCategory(category, platform) {
    return this.get(`/api/comparison/category/${encodeURIComponent(category)}?platform=${platform}`);
  },

  // ── Admin config ────────────────────────────────
  async getConfig() {
    return this.get('/api/config');
  },
  async updateConfig(data) {
    return this.post('/api/config', data);
  },

  // ── Export ──────────────────────────────────────
  exportUrl(reportType, params) {
    let url = `${this.BASE}/api/export/${reportType}`;
    if (params) {
      const qs = new URLSearchParams(params).toString();
      url += `?${qs}`;
    }
    return url;
  },
};
