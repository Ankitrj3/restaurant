/**
 * Admin Config module — platform toggle, cache settings, and config management.
 */
const AdminConfig = {
  async open() {
    const overlay = document.getElementById('settings-overlay');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    await this.loadConfig();
  },

  close() {
    const overlay = document.getElementById('settings-overlay');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
  },

  async loadConfig() {
    const el = document.getElementById('admin-config-form');
    if (!el) return;
    try {
      const config = await API.getConfig();
      this.renderForm(el, config);
    } catch (e) {
      el.innerHTML = '<p style="color:var(--danger);">Failed to load configuration</p>';
    }
  },

  renderForm(el, config) {
    const platforms = config.platforms || {};
    let html = `
      <div class="config-section">
        <h3><i class="fa-solid fa-toggle-on icon-inline"></i>Platform Toggles</h3>
        <div class="config-grid">`;

    for (const [key, info] of Object.entries(platforms)) {
      html += `<label class="config-toggle">
        <input type="checkbox" id="cfg-${key}" ${info.enabled ? 'checked' : ''}>
        <span class="toggle-label">${info.label}</span>
        <span class="toggle-status ${info.enabled ? 'on' : 'off'}">${info.enabled ? 'Enabled' : 'Disabled'}</span>
      </label>`;
    }
    html += `</div></div>`;

    html += `
      <div class="config-section">
        <h3><i class="fa-solid fa-clock icon-inline"></i>Cache & Performance</h3>
        <div class="config-grid">
          <label class="config-field">
            <span>Cache TTL (seconds)</span>
            <input type="number" id="cfg-cache-ttl" value="${config.cache_ttl || 3600}" min="60" max="86400">
          </label>
          <label class="config-field">
            <span>Fuzzy Match Threshold</span>
            <input type="number" id="cfg-fuzzy" value="${config.fuzzy_threshold || 0.65}" min="0.1" max="1.0" step="0.05">
          </label>
          <label class="config-toggle">
            <input type="checkbox" id="cfg-fallback" ${config.scraping_fallback ? 'checked' : ''}>
            <span class="toggle-label">AI Fallback Data</span>
            <span class="toggle-status ${config.scraping_fallback ? 'on' : 'off'}">${config.scraping_fallback ? 'Enabled' : 'Disabled'}</span>
          </label>
        </div>
      </div>`;

    html += `
      <div class="config-section">
        <h3><i class="fa-solid fa-info-circle icon-inline"></i>Restaurant Info</h3>
        <div class="config-info">
          <p><strong>Client:</strong> ${config.client_restaurant || 'N/A'}</p>
          <p><strong>Address:</strong> ${config.client_address || 'N/A'}</p>
        </div>
      </div>`;

    html += `<div class="config-actions">
      <button class="btn-save" onclick="AdminConfig.save()"><i class="fa-solid fa-check icon-inline"></i>Save Changes</button>
      <button class="btn-cancel" onclick="AdminConfig.close()">Cancel</button>
    </div>`;

    el.innerHTML = html;
  },

  async save() {
    const data = {
      ubereats_enabled: document.getElementById('cfg-ubereats')?.checked,
      doordash_enabled: document.getElementById('cfg-doordash')?.checked,
      grubhub_enabled: document.getElementById('cfg-grubhub')?.checked,
      cache_ttl: parseInt(document.getElementById('cfg-cache-ttl')?.value || '3600'),
      fuzzy_threshold: parseFloat(document.getElementById('cfg-fuzzy')?.value || '0.65'),
      scraping_fallback: document.getElementById('cfg-fallback')?.checked,
    };
    try {
      await API.updateConfig(data);
      Utils.showToast('Configuration saved successfully', 'success');
      this.close();
    } catch (e) {
      Utils.showToast('Failed to save configuration', 'error');
    }
  },
};
