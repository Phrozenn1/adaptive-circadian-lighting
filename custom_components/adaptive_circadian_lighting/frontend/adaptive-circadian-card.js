/**
 * Adaptive Circadian Lighting - Lovelace Custom Card
 * Provides an interactive 24h circadian curve visualization, profile switcher,
 * weather boost monitor, and manual override manager.
 * Supports English, Norwegian, Spanish, German, French, and Portuguese.
 */

const I18N = {
  en: {
    brightness: "Brightness",
    colorTemp: "Color Temp",
    phase: "Phase",
    now: "NOW",
    automatic: "Automatic",
    overridden: "overridden (Reset)",
    resetAuto: "Restore adaptive control",
    mode: "Mode",
    color: "Color",
    profiles: { normal: "Normal", sleep: "Sleep", morning: "Morning", evening: "Evening", focus: "Focus", relax: "Relax" }
  },
  nb: {
    brightness: "Lysstyrke",
    colorTemp: "Fargetemperatur",
    phase: "Fase",
    now: "NÅ",
    automatic: "Automatisk",
    overridden: "overstyrt (Nullstill)",
    resetAuto: "Gjenopprett automatikk",
    mode: "Modus",
    color: "Farge",
    profiles: { normal: "Normal", sleep: "Søvn", morning: "Morgen", evening: "Kveld", focus: "Fokus", relax: "Avslapping" }
  },
  no: {
    brightness: "Lysstyrke",
    colorTemp: "Fargetemperatur",
    phase: "Fase",
    now: "NÅ",
    automatic: "Automatisk",
    overridden: "overstyrt (Nullstill)",
    resetAuto: "Gjenopprett automatikk",
    mode: "Modus",
    color: "Farge",
    profiles: { normal: "Normal", sleep: "Søvn", morning: "Morgen", evening: "Kveld", focus: "Fokus", relax: "Avslapping" }
  },
  es: {
    brightness: "Brillo",
    colorTemp: "Temperatura color",
    phase: "Fase",
    now: "AHORA",
    automatic: "Automático",
    overridden: "anulado (Restablecer)",
    resetAuto: "Restablecer control adaptativo",
    mode: "Modo",
    color: "Color",
    profiles: { normal: "Normal", sleep: "Noche", morning: "Mañana", evening: "Tarde", focus: "Foco", relax: "Relajación" }
  },
  de: {
    brightness: "Helligkeit",
    colorTemp: "Farbtemperatur",
    phase: "Phase",
    now: "JETZT",
    automatic: "Automatisch",
    overridden: "übersteuert (Zurücksetzen)",
    resetAuto: "Automatische Steuerung wiederherstellen",
    mode: "Modus",
    color: "Farbe",
    profiles: { normal: "Normal", sleep: "Schlafen", morning: "Morgen", evening: "Abend", focus: "Fokus", relax: "Entspannen" }
  },
  fr: {
    brightness: "Luminosité",
    colorTemp: "Temp. de couleur",
    phase: "Phase",
    now: "MAINTENANT",
    automatic: "Automatique",
    overridden: "dérogé (Réinitialiser)",
    resetAuto: "Restaurer le contrôle adaptatif",
    mode: "Mode",
    color: "Couleur",
    profiles: { normal: "Normal", sleep: "Sommeil", morning: "Matin", evening: "Soir", focus: "Focus", relax: "Détente" }
  },
  pt: {
    brightness: "Brilho",
    colorTemp: "Temp. de cor",
    phase: "Fase",
    now: "AGORA",
    automatic: "Automático",
    overridden: "sobreposto (Repor)",
    resetAuto: "Restaurar controlo adaptativo",
    mode: "Modo",
    color: "Cor",
    profiles: { normal: "Normal", sleep: "Dormir", morning: "Manhã", evening: "Noite", focus: "Foco", relax: "Relaxar" }
  }
};

class AdaptiveCircadianCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getLang() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").substring(0, 2).toLowerCase();
    return I18N[lang] || I18N.en;
  }

  _escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  _kelvinToRgb(k) {
    const temp = Math.max(1000, Math.min(40000, k || 4000)) / 100.0;
    let r, g, b;
    if (temp <= 66) {
      r = 255;
      g = Math.max(0, Math.min(255, 99.4708025861 * Math.log(temp) - 161.1195681661));
      b = temp <= 19 ? 0 : Math.max(0, Math.min(255, 138.5177312231 * Math.log(temp - 10) - 305.0447927307));
    } else {
      r = Math.max(0, Math.min(255, 329.698727446 * Math.pow(temp - 60, -0.1332047592)));
      g = Math.max(0, Math.min(255, 288.1221695283 * Math.pow(temp - 60, -0.0755148492)));
      b = 255;
    }
    return [Math.round(r), Math.round(g), Math.round(b)];
  }

  _findRelatedEntities() {
    const states = this._hass?.states || {};
    const baseEntity = this._config?.entity || "";

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
      targetRgb: null,
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
      if (entityId.startsWith("sensor.") && entityId.endsWith("_target_rgb")) result.targetRgb = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_phase")) result.phaseSensor = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_weather_boost")) result.weatherBoost = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_manual_overrides")) result.overridesSensor = stateObj;
      if (entityId.startsWith("sensor.") && entityId.endsWith("_presence_state")) result.presenceSensor = stateObj;
    }

    return result;
  }

  _render() {
    if (!this._hass) return;

    const t = this._getLang();
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

    // Live target RGB color
    let rgbColor = [255, 180, 100];
    if (entities.targetRgb?.attributes?.rgb_color && Array.isArray(entities.targetRgb.attributes.rgb_color)) {
      rgbColor = entities.targetRgb.attributes.rgb_color;
    } else if (entities.targetRgb?.state && entities.targetRgb.state.includes(",")) {
      rgbColor = entities.targetRgb.state.split(",").map(v => parseInt(v.trim(), 10));
    } else if (entities.targetKelvin?.attributes?.target_rgb) {
      rgbColor = entities.targetKelvin.attributes.target_rgb;
    } else {
      rgbColor = this._kelvinToRgb(parseInt(currentKelvin, 10));
    }

    // 24h Curve calculation
    const now = new Date();
    const currentHourFloat = now.getHours() + now.getMinutes() / 60.0;
    const currentX = (currentHourFloat / 24.0) * 360 + 20;

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
        .color-val-box {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
        }
        .color-rgb-box {
          display: inline-block;
          width: 14px;
          height: 14px;
          border-radius: 4px;
          border: 1px solid rgba(255, 255, 255, 0.4);
          box-shadow: 0 0 6px rgba(0, 0, 0, 0.3);
          flex-shrink: 0;
        }
        .rgb-subtext {
          font-size: 0.68rem;
          font-weight: 500;
          opacity: 0.65;
          margin-top: 2px;
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
            <span>${this._escapeHtml(title)}</span>
          </div>
          <ha-switch id="master-toggle" ?checked="${isMasterOn}"></ha-switch>
        </div>

        <div class="badge-bar">
          <span class="badge highlight">
            <ha-icon icon="mdi:weather-partly-cloudy" style="--mdc-icon-size: 14px;"></ha-icon>
            ${this._escapeHtml(weatherBoost.replace('_', ' '))}
          </span>
          <span class="badge">
            <ha-icon icon="mdi:motion-sensor" style="--mdc-icon-size: 14px;"></ha-icon>
            ${this._escapeHtml(presenceState)}
          </span>
          ${overrideCount > 0 ? `
            <span class="badge alert" id="btn-override-badge">
              <ha-icon icon="mdi:hand-back-right-off" style="--mdc-icon-size: 14px;"></ha-icon>
              ${this._escapeHtml(overrideCount)} ${this._escapeHtml(t.overridden)}
            </span>
          ` : `
            <span class="badge">
              <ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 14px;"></ha-icon>
              ${this._escapeHtml(t.automatic)}
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

            <line x1="20" y1="120" x2="380" y2="120" stroke="rgba(255,255,255,0.1)" stroke-width="1" />
            <line x1="20" y1="35" x2="380" y2="35" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,4" />

            <path d="${curvePath}" fill="none" stroke="url(#curveGradient)" stroke-width="4" stroke-linecap="round" />

            <line x1="${currentX}" y1="15" x2="${currentX}" y2="125" class="now-indicator" />
            <circle cx="${currentX}" cy="30" r="4" fill="#ff9800" />
            <text x="${currentX}" y="12" fill="#ff9800" font-size="9" font-weight="bold" text-anchor="middle">${this._escapeHtml(t.now)}</text>
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
            <div class="stat-label">${this._escapeHtml(t.brightness)}</div>
            <div class="stat-value">${this._escapeHtml(currentBrightness)}%</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">${this._escapeHtml(t.colorTemp)}</div>
            <div class="stat-value color-val-box">
              <span class="color-rgb-box" style="background: rgb(${rgbColor.map(v => parseInt(v, 10) || 0).join(',')});" title="RGB: ${rgbColor.map(v => parseInt(v, 10) || 0).join(', ')}"></span>
              <span>${this._escapeHtml(currentKelvin)}K</span>
            </div>
            <div class="rgb-subtext">RGB(${rgbColor.map(v => parseInt(v, 10) || 0).join(', ')})</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">${this._escapeHtml(t.phase)}</div>
            <div class="stat-value" style="font-size:0.95rem; text-transform:capitalize;">${this._escapeHtml(currentPhase)}</div>
          </div>
        </div>

        <div class="profiles">
          ${["normal", "sleep", "morning", "evening", "focus", "relax"].map(p => `
            <button class="profile-btn ${currentProfile === p ? 'active' : ''}" data-profile="${this._escapeHtml(p)}">
              ${this._escapeHtml(t.profiles[p] || (p.charAt(0).toUpperCase() + p.slice(1)))}
            </button>
          `).join("")}
        </div>

        <div class="actions-row">
          <div style="font-size: 0.75rem; opacity: 0.7;">
            ${this._escapeHtml(t.mode)}: <b>${this._escapeHtml(entities.calcModeSelect?.state || 'Hybrid')}</b> | ${this._escapeHtml(t.color)}: <b>${this._escapeHtml(entities.colorModeSelect?.state || 'Auto')}</b>
          </div>
          ${overrideCount > 0 ? `
            <button class="btn-reset" id="btn-reset-overrides">
              <ha-icon icon="mdi:refresh" style="--mdc-icon-size: 14px;"></ha-icon>
              ${this._escapeHtml(t.resetAuto)}
            </button>
          ` : ''}
        </div>
      </ha-card>
    `;

    this._bindEvents(entities);
  }

  _bindEvents(entities) {
    const root = this.shadowRoot;

    const toggle = root.getElementById("master-toggle");
    if (toggle && entities.masterSwitch) {
      toggle.addEventListener("change", () => {
        this._hass.callService("switch", "toggle", { entity_id: entities.masterSwitch.entity_id });
      });
    }

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

window.customCards = window.customCards || [];
window.customCards.push({
  type: "adaptive-circadian-card",
  name: "Adaptive Circadian Card",
  description: "Interaktiv 24t døgnrytmekurve / Interactive 24h circadian curve for Adaptive Circadian Lighting.",
  preview: true,
});
