/**
 * REST API client for the Restaurant Competitor Intelligence Platform.
 */
const API = {
  BASE: '',

  async get(endpoint) {
    try {
      const resp = await fetch(`${this.BASE}${endpoint}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.error(`[API] GET ${endpoint} failed:`, e);
      throw e;
    }
  },

  async searchRestaurants(radius = 20) {
    return this.get(`/api/restaurants/search?radius=${radius}`);
  },

  async getClientMenu() {
    return this.get('/api/client/menu');
  },

  async getComparison(restaurantIdx) {
    return this.get(`/api/comparison/${restaurantIdx}`);
  },

  async getMarketAnalysis() {
    return this.get('/api/analysis/market');
  },

  async getPricingAnalysis() {
    return this.get('/api/analysis/pricing');
  },

  async getRecommendations() {
    return this.get('/api/analysis/recommendations');
  },

  async healthCheck() {
    return this.get('/api/health');
  }
};
