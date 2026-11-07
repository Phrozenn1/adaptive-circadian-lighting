/**
 * Adaptive Circadian Lighting - Custom Sidebar Panel
 * Displays an overview of all circadian zones, weather boosts, and room statuses in Home Assistant.
 */

class AdaptiveCircadianPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;

    const states = this._hass.states || {};
    // Find all master switches for our domain
    const instances = [];

    for (const [entityId, stateObj] of Object.entries(states)) {
      if (entityId.startsWith("switch.") && entityId.endsWith("_adaptation")) {
        const prefix = entityId.replace(/^switch\./, "").replace(/_adaptation$/, "");
        const friendlyName = stateObj.attributes.friendly_name?.replace(" Adaptation", "") || prefix;

        instances.push({
          prefix,
          name: friendlyName,
          masterSwitch: stateObj,
          targetBrightness: states[`sensor.${prefix}_target_brightness`]?.state || "100",
          targetKelvin: states[`sensor.${prefix}_target_color_temp`]?.state || "4000",
          phase: states[`sensor.${prefix}_phase`]?.state || "day",
          profile: states[`select.${prefix}_profile`]?.state || "normal",
          weatherBoost: states[`sensor.${prefix}_weather_boost`]?.state || "none",
          overrides: parseInt(states[`sensor.${prefix}_manual_overrides`]?.state || "0", 10),
          presence: states[`sensor.${prefix}_presence_state`]?.state || "N/A",
        });
      }
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 24px;
          background: var(--primary-background-color, #111116);
          color: var(--primary-text-color, #fff);
          min-height: 100vh;
          box-sizing: border-box;
          font-family: var(--paper-font-body1_-_font-family, system-ui, -apple-system, sans-serif);
        }
        .header-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          flex-wrap: wrap;
          gap: 16px;
        }
        .header-title h1 {
          font-size: 1.8rem;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-title p {
          margin: 4px 0 0 0;
          opacity: 0.7;
          font-size: 0.95rem;
        }
        .global-actions {
          display: flex;
          gap: 10px;
        }
        .btn-global {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: inherit;
          padding: 8px 16px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.85rem;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition: background 0.2s ease;
        }
        .btn-global:hover {
          background: rgba(255, 255, 255, 0.15);
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
          gap: 20px;
        }
        .zone-card {
          background: var(--ha-card-background, #1e1e24);
          border-radius: 14px;
          padding: 18px;
          border: 1px solid rgba(255, 255, 255, 0.06);
          box-shadow: 0 4px 14px rgba(0,0,0,0.2);
        }
        .zone-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .zone-name {
          font-size: 1.2rem;
          font-weight: 600;
        }
        .zone-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-bottom: 14px;
        }
        .stat-item {
          background: rgba(0, 0, 0, 0.2);
          padding: 8px 12px;
          border-radius: 8px;
        }
        .stat-item .label {
          font-size: 0.7rem;
          opacity: 0.6;
          text-transform: uppercase;
        }
        .stat-item .value {
          font-size: 1.1rem;
          font-weight: bold;
          color: #ffb74d;
        }
        .zone-badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          font-size: 0.75rem;
        }
        .z-badge {
          padding: 3px 8px;
          border-radius: 6px;
          background: rgba(255, 255, 255, 0.08);
        }
        .z-badge.boost {
          background: rgba(255, 179, 0, 0.18);
          color: #ffb300;
        }
        .z-badge.overridden {
          background: rgba(244, 67, 54, 0.18);
          color: #ff5252;
        }
        .empty-state {
          text-align: center;
          padding: 60px 20px;
          opacity: 0.7;
        }
      </style>

      <div>
        <div class="header-bar">
          <div class="header-title">
            <h1>
              <ha-icon icon="mdi:sun-clock"></ha-icon>
              Adaptive Circadian Lighting
            </h1>
            <p>Oversikt over døgnrytme, værkompensering og tilstedeværelse for alle rom.</p>
          </div>
          <div class="global-actions">
            <button class="btn-global" id="btn-all-sleep">
              <ha-icon icon="mdi:bed"></ha-icon>
              Nattmodus for alle
            </button>
            <button class="btn-global" id="btn-all-reset">
              <ha-icon icon="mdi:refresh"></ha-icon>
              Nullstill alle overstyringer
            </button>
          </div>
        </div>

        ${instances.length === 0 ? `
          <div class="empty-state">
            <h2>Ingen soner konfigurert ennå</h2>
            <p>Gå til Innstillinger -> Enheter og tjenester -> Legg til integrasjon for å opprette ditt første rom.</p>
          </div>
        ` : `
          <div class="grid">
            ${instances.map(inst => `
              <div class="zone-card">
                <div class="zone-header">
                  <div class="zone-name">${inst.name}</div>
                  <ha-switch class="zone-switch" data-entity="${inst.masterSwitch.entity_id}" ?checked="${inst.masterSwitch.state === 'on'}"></ha-switch>
                </div>
                <div class="zone-stats">
                  <div class="stat-item">
                    <div class="label">Mål-lysstyrke</div>
                    <div class="value">${inst.targetBrightness}%</div>
                  </div>
                  <div class="stat-item">
                    <div class="label">Fargetemperatur</div>
                    <div class="value">${inst.targetKelvin}K</div>
                  </div>
                </div>
                <div class="zone-badges">
                  <span class="z-badge">Profil: <b>${inst.profile}</b></span>
                  <span class="z-badge">Fase: <b>${inst.phase}</b></span>
                  <span class="z-badge boost">Vær: <b>${inst.weatherBoost.replace('_', ' ')}</b></span>
                  <span class="z-badge">Tilstedeværelse: <b>${inst.presence}</b></span>
                  ${inst.overrides > 0 ? `
                    <span class="z-badge overridden">${inst.overrides} pære overstyrt</span>
                  ` : ''}
                </div>
              </div>
            `).join("")}
          </div>
        `}
      </div>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    const root = this.shadowRoot;

    // Global buttons
    const btnSleep = root.getElementById("btn-all-sleep");
    if (btnSleep) {
      btnSleep.addEventListener("click", () => {
        this._hass.callService("adaptive_circadian_lighting", "toggle_sleep_mode", {});
      });
    }

    const btnReset = root.getElementById("btn-all-reset");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        this._hass.callService("adaptive_circadian_lighting", "reset_manual_override", {});
      });
    }

    // Individual switches
    const switches = root.querySelectorAll(".zone-switch");
    switches.forEach(sw => {
      sw.addEventListener("change", () => {
        const ent = sw.getAttribute("data-entity");
        this._hass.callService("switch", "toggle", { entity_id: ent });
      });
    });
  }
}

customElements.define("adaptive-circadian-panel", AdaptiveCircadianPanel);
