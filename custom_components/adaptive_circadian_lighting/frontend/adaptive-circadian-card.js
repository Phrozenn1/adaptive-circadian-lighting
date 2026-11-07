/**
 * Adaptive Circadian Lighting - Lovelace Custom Card
 * Provides an interactive 24h circadian curve visualization, profile switcher,
 * weather boost monitor, and manual override manager.
 */

class AdaptiveCircadianCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config.entity && !config.device_id && !config.name) {
      // Default to finding first adaptive lighting switch if not specified
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _findRelatedEntities() {
    const states = this._hass?.states || {};
    const baseEntity = this._config?.entity || "";

    // Extract prefix if e.g. switch.adaptive_living_room_adaptation or select.living_room_profile
    let prefix = "";
    if (baseEntity) {
      prefix = baseEntity
        .replace(/^(switch|sensor|select)\./, "")
        .replace(/_(adaptation|profile|target_brightness|target_color_temp)$/, "");
    }

    const result = {
      masterSwitch: null,
      brightnessSwitch: null,
      colorSwitch: null,
      sleepSwitch: null,
      profileSelect: null,
      calcModeSelect: null,
      colorModeSelect: null,
      targetBrightness: null,
      targetKelvin: null,
      phaseSensor: null,
      weatherBoost: null,
      overridesSensor: null,
      presenceSensor: null,
    };

    for (const [entityId, stateObj] of Object.entries(states)) {
      if (prefix && !entityId.includes(prefix)) continue;

      if (entityId.startsWith("switch.") && entityId.endsWith("_adaptation")) result.masterSwitch = stateObj;
      if (entityId.startsWith("switch.") && entityId.endsWith("_adapt_brightness")) result.brightnessSwitch = stateObj;
      if (entityId.startsWith("switch.") && entityId.endsWith("_adapt_color")) result.colorSwitch = stateObj;
      if (entityId.startsWith("switch.") && entityId.endsWith("_sleep_mode")) result.sleepSwitch = stateObj;

      if (entityId.startsWith("select.") && entityId.endsWith("_profile")) result.profileSelect = stateObj;
      if (entityId.startsWith("select.") && entityId.endsWith("_calc_mode")) result.calcModeSelect = stateObj;
      if (entityId.startsWith("select.") && entityId.endsWith("_color_mode")) result.colorModeSelect = stateObj;

      if (entityId.startsWith("sensor.") && entityId.endsWith("_target_brightness")) result.targetBrightness = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_target_color_temp")) result.targetKelvin = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_phase")) result.phaseSensor = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_weather_boost")) result.weatherBoost = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_manual_overrides")) result.overridesSensor = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_presence_state")) result.presenceSensor = stateObj;
    }

    return result;
  }

  _render() {
    if (!this._hass) return;

    const entities = this._findRelatedEntities();
    const title = this._config?.title || entities.masterSwitch?.attributes?.friendly_name?.replace(" Adaptation", "") || "Adaptive Circadian Lighting";

    const isMasterOn = entities.masterSwitch ? entities.masterSwitch.state === "on" : true;
    const currentProfile = entities.profileSelect?.state || "normal";
    const currentBrightness = entities.targetBrightness?.state || "100";
    const currentKelvin = entities.targetKelvin?.state || "4000";
    const currentPhase = entities.phaseSensor?.state || "day";
    const weatherBoost = entities.weatherBoost?.state || "none";
    const overrideCount = parseInt(entities.overridesSensor?.state || "0", 10);
    const presenceState = entities.presenceSensor?.state || "unknown";

    // 24h Curve coordinates
    const now = new Date();
    const currentHourFloat = now.getHours() + now.getMinutes() / 60.0;
    const currentX = (currentHourFloat / 24.0) * 360 + 20;

    // Build SVG curve points for a standard day
    const svgWidth = 400;
    const svgHeight = 140;

    // Approximate Kelvin and Brightness path points
    let points = [];
    for (let h = 0; h <= 24; h += 0.5) {
      let x = (h / 24.0) * 360 + 20;
      let factor = 0.05;
      if (h >= 6.5 && h <= 22) {
        let fraction = (h - 6.5) / 15.5;
        factor = Math.sin(fraction * Math.PI);
      }
      let y = 120 - factor * 85;
      points.push(`${x},${y}`);
    }
    const curvePath = "M " + points.join(" L ");

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          padding: 18px;
          border-radius: 16px;
          background: var(--ha-card-background, var(--card-background-color, #1e1e24));
          color: var(--primary-text-color, #ffffff);
          box-shadow: var(--ha-card-box-shadow, 0 4px 12px rgba(0,0,0,0.15));
          font-family: var(--paper-font-body1_-_font-family, system-ui, -apple-system, sans-serif);
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .title {
          font-size: 1.25rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .badge-bar {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 14px;
        }
        .badge {
          font-size: 0.75rem;
          padding: 4px 10px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.08);
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .badge.highlight {
          background: rgba(255, 179, 0, 0.2);
          color: #ffb300;
          font-weight: 500;
        }
        .badge.alert {
          background: rgba(244, 67, 54, 0.2);
          color: #ff5252;
          cursor: pointer;
        }
        .curve-container {
          position: relative;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 12px;
          padding: 10px 0 4px 0;
          margin-bottom: 16px;
        }
        .curve-svg {
          width: 100%;
          height: 120px;
          overflow: visible;
        }
        .timeline-label {
          display: flex;
          justify-content: space-between;
          padding: 0 16px;
          font-size: 0.7rem;
          opacity: 0.6;
          margin-top: -6px;
        }
        .now-indicator {
          stroke: #ff9800;
          stroke-width: 2;
          stroke-dasharray: 3, 3;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-bottom: 16px;
          text-align: center;
        }
        .stat-box {
          background: rgba(255, 255, 255, 0.04);
          padding: 10px;
          border-radius: 10px;
        }
        .stat-value {
          font-size: 1.15rem;
          font-weight: 700;
          margin-top: 2px;
          color: #ffb74d;
        }
        .stat-label {
          font-size: 0.72rem;
          opacity: 0.7;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .profiles {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          padding-bottom: 4px;
          margin-bottom: 14px;
        }
        .profile-btn {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 20px;
          color: inherit;
          padding: 6px 14px;
          font-size: 0.8rem;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.2s ease;
        }
        .profile-btn:hover {
          background: rgba(255, 255, 255, 0.16);
        }
        .profile-btn.active {
          background: #ff9800;
          color: #000;
          font-weight: 600;
          border-color: #ff9800;
        }
        .actions-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 8px;
        }
        .btn-reset {
          background: rgba(244, 67, 54, 0.15);
          color: #ff5252;
          border: 1px solid rgba(244, 67, 54, 0.3);
          border-radius: 8px;
          padding: 6px 12px;
          font-size: 0.75rem;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .btn-reset:hover {
          background: rgba(244, 67, 54, 0.25);
        }
      </style>

      <ha-card>
        <div class="header">
          <div class="title">
            <ha-icon icon="mdi:theme-light-dark"></ha-icon>
            <span>${title}</span>
          </div>
          <ha-switch id="master-toggle" ?checked="${isMasterOn}"></ha-switch>
        </div>

        <div class="badge-bar">
          <span class="badge highlight">
            <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size: 14px;"></ha-icon>
            ${weatherBoost.replace('_', ' ')}
          </span>
          <span class="badge">
            <ha-icon icon="mdi:motion-sensor" style="--mdc-icon-size: 14px;"></ha-icon>
            ${presenceState}
          </span>
          ${overrideCount > 0 ? `
            <span class="badge alert" id="btn-override-badge" title="Klikk for å nullstille">
              <ha-icon icon="mdi:hand-back-right-off" style="--mdc-icon-size: 14px;"></ha-icon>
              ${overrideCount} overstyrt (Nullstill)
            </span>
          ` : `
            <span class="badge">
              <ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 14px;"></ha-icon>
              Automatisk
            </span>
          `}
        </div>

        <div class="curve-container">
          <svg class="curve-svg" viewBox="0 0 400 130">
            <defs>
              <linearGradient id="curveGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#ff7043" />
                <stop offset="30%" stop-color="#ffca28" />
                <stop offset="50%" stop-color="#81d4fa" />
                <stop offset="70%" stop-color="#ffca28" />
                <stop offset="100%" stop-color="#ff7043" />
              </linearGradient>
            </defs>

            <!-- Base horizontal guidelines -->
            <line x1="20" y1="120" x2="380" y2="120" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
            <line x1="20" y1="35" x2="380" y2="35" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,4" />

            <!-- Circadian Curve -->
            <path d="${curvePath}" fill="none" stroke="url(#curveGradient)" stroke-width="4" stroke-linecap="round" />

            <!-- NOW vertical marker -->
            <line x1="${currentX}" y1="15" x2="${currentX}" y2="125" class="now-indicator" />
            <circle cx="${currentX}" cy="30" r="4" fill="#ff9800" />
            <text x="${currentX}" y="12" fill="#ff9800" font-size="9" font-weight="bold" text-anchor="middle">NÅ</text>
          </svg>
          <div class="timeline-label">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>24:00</span>
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-label">Lysstyrke</div>
            <div class="stat-value">${currentBrightness}%</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Fargetemperatur</div>
            <div class="stat-value">${currentKelvin}K</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Fase</div>
            <div class="stat-value" style="font-size:0.95rem; text-transform:capitalize;">${currentPhase}</div>
          </div>
        </div>

        <div class="profiles">
          ${["normal", "sleep", "morning", "evening", "focus", "relax"].map(p => `
            <button class="profile-btn ${currentProfile === p ? 'active' : ''}" data-profile="${p}">
              ${p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          `).join("")}
        </div>

        <div class="actions-row">
          <div style="font-size: 0.75rem; opacity: 0.7;">
            Modus: <b>${entities.calcModeSelect?.state || 'Hybrid'}</b> | Farge: <b>${entities.colorModeSelect?.state || 'Auto'}</b>
          </div>
          ${overrideCount > 0 ? `
            <button class="btn-reset" id="btn-reset-overrides">
              <ha-icon icon="mdi:refresh" style="--mdc-icon-size: 14px;"></ha-icon>
              Gjenopprett automatikk
            </button>
          ` : ''}
        </div>
      </ha-card>
    `;

    this._bindEvents(entities);
  }

  _bindEvents(entities) {
    const root = this.shadowRoot;

    // Master toggle
    const toggle = root.getElementById("master-toggle");
    if (toggle && entities.masterSwitch) {
      toggle.addEventListener("change", () => {
        this._hass.callService("switch", "toggle", { entity_id: entities.masterSwitch.entity_id });
      });
    }

    // Profile buttons
    const buttons = root.querySelectorAll(".profile-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        const profile = btn.getAttribute("data-profile");
        if (entities.profileSelect) {
          this._hass.callService("select", "select_option", {
            entity_id: entities.profileSelect.entity_id,
            option: profile,
          });
        } else {
          this._hass.callService("adaptive_circadian_lighting", "set_profile", { profile });
        }
      });
    });

    // Reset override buttons
    const resetBtn = root.getElementById("btn-reset-overrides");
    const badgeReset = root.getElementById("btn-override-badge");
    const doReset = () => {
      this._hass.callService("adaptive_circadian_lighting", "reset_manual_override", {});
    };
    if (resetBtn) resetBtn.addEventListener("click", doReset);
    if (badgeReset) badgeReset.addEventListener("click", doReset);
  }

  getCardSize() {
    return 4;
  }
}

customElements.define("adaptive-circadian-card", AdaptiveCircadianCard);

// Register with Home Assistant Card Picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "adaptive-circadian-card",
  name: "Adaptive Circadian Card",
  description: "Interaktiv 24t døgnrytmekurve, profilvelger og overstyringskontroll for Adaptive Circadian Lighting.",
  preview: true,
});
