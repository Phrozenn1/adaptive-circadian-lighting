/**
 * Adaptive Circadian Lighting - Custom Sidebar Panel
 * Displays an overview and interactive controls for all circadian zones,
 * weather boost, profiles, and presence states in Home Assistant.
 * Supports English, Norwegian, Spanish, German, French, and Portuguese.
 */

const PANEL_I18N = {
  en: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Real-time overview and manual control across all configured rooms and zones.",
    allSleep: "Sleep mode (all)",
    resetAll: "Reset all overrides",
    applyAll: "Apply to all",
    noZones: "No circadian zones found",
    noZonesDesc: "Go to Settings -> Devices & services -> Add integration to configure your first room.",
    targetBright: "Target Brightness",
    targetColor: "Color Temp",
    profile: "Profile",
    phase: "Phase",
    weather: "Weather Boost",
    presence: "Presence",
    active: "Active",
    paused: "Paused",
    overriddenWarning: "manual override(s) active",
    resetOverride: "Reset override",
    toggleSleep: "Toggle Sleep",
    applyNow: "Apply Now",
    profiles: {
      normal: "Normal",
      sleep: "Sleep",
      morning: "Morning",
      evening: "Evening",
      focus: "Focus",
      relax: "Relax"
    }
  },
  nb: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Døgnrytmestyring, værkompensering og tilstedeværelse for hele hjemmet.",
    allSleep: "Nattmodus (alle)",
    resetAll: "Nullstill alle",
    applyAll: "Tilpass alle",
    noZones: "Ingen soner konfigurert ennå",
    noZonesDesc: "Gå til Innstillinger -> Enheter og tjenester -> Legg til integrasjon for å opprette ditt første rom.",
    targetBright: "Mål-lysstyrke",
    targetColor: "Fargetemperatur",
    profile: "Profil",
    phase: "Fase",
    weather: "Værkompensering",
    presence: "Tilstedeværelse",
    active: "Aktiv",
    paused: "Pauset",
    overriddenWarning: "overstyring(er) aktive",
    resetOverride: "Nullstill overstyring",
    toggleSleep: "Søvnmodus",
    applyNow: "Tilpass nå",
    profiles: {
      normal: "Normal",
      sleep: "Søvn",
      morning: "Morgen",
      evening: "Kveld",
      focus: "Fokus",
      relax: "Avslapping"
    }
  },
  no: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Døgnrytmestyring, værkompensering og tilstedeværelse for hele hjemmet.",
    allSleep: "Nattmodus (alle)",
    resetAll: "Nullstill alle",
    applyAll: "Tilpass alle",
    noZones: "Ingen soner konfigurert ennå",
    noZonesDesc: "Gå til Innstillinger -> Enheter og tjenester -> Legg til integrasjon for å opprette ditt første rom.",
    targetBright: "Mål-lysstyrke",
    targetColor: "Fargetemperatur",
    profile: "Profil",
    phase: "Fase",
    weather: "Værkompensering",
    presence: "Tilstedeværelse",
    active: "Aktiv",
    paused: "Pauset",
    overriddenWarning: "overstyring(er) aktive",
    resetOverride: "Nullstill overstyring",
    toggleSleep: "Søvnmodus",
    applyNow: "Tilpass nå",
    profiles: {
      normal: "Normal",
      sleep: "Søvn",
      morning: "Morgen",
      evening: "Kveld",
      focus: "Fokus",
      relax: "Avslapping"
    }
  },
  es: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Resumen en tiempo real y control manual en todas las habitaciones y zonas.",
    allSleep: "Modo noche (todos)",
    resetAll: "Restablecer todo",
    applyAll: "Aplicar a todos",
    noZones: "No se encontraron zonas circadianas",
    noZonesDesc: "Vaya a Configuración -> Dispositivos y servicios para añadir su primera habitación.",
    targetBright: "Brillo objetivo",
    targetColor: "Temp. color",
    profile: "Perfil",
    phase: "Fase",
    weather: "Compensación clima",
    presence: "Presencia",
    active: "Activo",
    paused: "Pausado",
    overriddenWarning: "anulación(es) manual(es) activa(s)",
    resetOverride: "Restablecer",
    toggleSleep: "Modo noche",
    applyNow: "Aplicar ahora",
    profiles: {
      normal: "Normal",
      sleep: "Noche",
      morning: "Mañana",
      evening: "Tarde",
      focus: "Foco",
      relax: "Relax"
    }
  },
  de: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Echtzeit-Übersicht und manuelle Steuerung für alle Räume und Zonen.",
    allSleep: "Nachtmodus (alle)",
    resetAll: "Alle zurücksetzen",
    applyAll: "Auf alle anwenden",
    noZones: "Keine zirkadianen Zonen gefunden",
    noZonesDesc: "Gehen Sie zu Einstellungen -> Geräte & Dienste, um Ihren ersten Raum einzurichten.",
    targetBright: "Ziel-Helligkeit",
    targetColor: "Farbtemperatur",
    profile: "Profil",
    phase: "Phase",
    weather: "Wetter-Boost",
    presence: "Präsenz",
    active: "Aktiv",
    paused: "Pausiert",
    overriddenWarning: "manuelle Übersteuerung(en) aktiv",
    resetOverride: "Zurücksetzen",
    toggleSleep: "Nachtmodus",
    applyNow: "Jetzt anwenden",
    profiles: {
      normal: "Normal",
      sleep: "Schlafen",
      morning: "Morgen",
      evening: "Abend",
      focus: "Fokus",
      relax: "Entspannen"
    }
  },
  fr: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Aperçu en temps réel et contrôle manuel dans toutes les pièces et zones.",
    allSleep: "Mode nuit (tous)",
    resetAll: "Tout réinitialiser",
    applyAll: "Appliquer à tous",
    noZones: "Aucune zone circadienne trouvée",
    noZonesDesc: "Allez dans Paramètres -> Appareils et services pour configurer votre première pièce.",
    targetBright: "Luminosité cible",
    targetColor: "Temp. de couleur",
    profile: "Profil",
    phase: "Phase",
    weather: "Boost météo",
    presence: "Présence",
    active: "Actif",
    paused: "En pause",
    overriddenWarning: "dérogation(s) manuelle(s) active(s)",
    resetOverride: "Réinitialiser",
    toggleSleep: "Mode nuit",
    applyNow: "Appliquer maintenant",
    profiles: {
      normal: "Normal",
      sleep: "Sommeil",
      morning: "Matin",
      evening: "Soir",
      focus: "Focus",
      relax: "Détente"
    }
  },
  pt: {
    title: "Adaptive Circadian Lighting",
    subtitle: "Visão geral em tempo real e controlo manual em todas as divisões e zonas.",
    allSleep: "Modo noturno (todos)",
    resetAll: "Repor todas",
    applyAll: "Aplicar a todas",
    noZones: "Nenhuma zona circadiana encontrada",
    noZonesDesc: "Vá a Definições -> Dispositivos e serviços para configurar a sua primeira divisão.",
    targetBright: "Brilho alvo",
    targetColor: "Temp. de cor",
    profile: "Perfil",
    phase: "Fase",
    weather: "Compensação clima",
    presence: "Presença",
    active: "Ativo",
    paused: "Pausado",
    overriddenWarning: "sobreposição(ões) ativa(s)",
    resetOverride: "Repor",
    toggleSleep: "Modo noturno",
    applyNow: "Aplicar agora",
    profiles: {
      normal: "Normal",
      sleep: "Dormir",
      morning: "Manhã",
      evening: "Noite",
      focus: "Foco",
      relax: "Relaxar"
    }
  }
};

class AdaptiveCircadianPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._lastFingerprint = "";

    // Event delegation on shadow root ensures listeners are never detached
    this.shadowRoot.addEventListener("click", (e) => this._handleClick(e));
    this.shadowRoot.addEventListener("change", (e) => this._handleChange(e));
  }

  set hass(hass) {
    this._hass = hass;
    this._checkAndRender();
  }

  set panel(panel) {
    this._panel = panel;
  }

  set narrow(narrow) {
    this._narrow = narrow;
  }

  _getLang() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").substring(0, 2).toLowerCase();
    return PANEL_I18N[lang] || PANEL_I18N.en;
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

  _handleClick(e) {
    if (!this._hass) return;
    const path = e.composedPath ? e.composedPath() : [e.target];
    const btn = path.find(el => el.dataset && el.dataset.action);
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const action = btn.dataset.action;
    const prefix = btn.dataset.prefix;
    const profile = btn.dataset.profile;

    if (action === "all-sleep") {
      this._hass.callService("adaptive_circadian_lighting", "toggle_sleep_mode", {});
    } else if (action === "all-reset") {
      this._hass.callService("adaptive_circadian_lighting", "reset_manual_override", {});
    } else if (action === "all-apply") {
      this._hass.callService("adaptive_circadian_lighting", "apply_now", {});
    } else if (action === "zone-sleep") {
      this._hass.callService("adaptive_circadian_lighting", "toggle_sleep_mode", { entity_id: `switch.${prefix}_adaptation` });
    } else if (action === "zone-reset") {
      this._hass.callService("adaptive_circadian_lighting", "reset_manual_override", { entity_id: `switch.${prefix}_adaptation` });
    } else if (action === "zone-apply") {
      this._hass.callService("adaptive_circadian_lighting", "apply_now", { entity_id: `switch.${prefix}_adaptation` });
    } else if (action === "select-profile") {
      const selectEntity = `select.${prefix}_profile`;
      if (this._hass.states[selectEntity]) {
        this._hass.callService("select", "select_option", {
          entity_id: selectEntity,
          option: profile,
        });
      } else {
        this._hass.callService("adaptive_circadian_lighting", "set_profile", {
          entity_id: `switch.${prefix}_adaptation`,
          profile: profile,
        });
      }
    }
  }

  _handleChange(e) {
    if (!this._hass) return;
    const path = e.composedPath ? e.composedPath() : [e.target];
    const toggle = path.find(el => el.classList && el.classList.contains("zone-toggle"));
    if (toggle && toggle.dataset.entity) {
      this._hass.callService("switch", "toggle", { entity_id: toggle.dataset.entity });
    }
  }

  _computeFingerprint(instances) {
    return instances.map(i => `${i.prefix}:${i.enabled}:${i.targetBrightness}:${i.targetKelvin}:${i.rgb ? i.rgb.join(',') : ''}:${i.profile}:${i.phase}:${i.weatherBoost}:${i.overrides}:${i.presence}`).join("|");
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

  _getInstances() {
    const states = this._hass?.states || {};
    const instances = [];

    for (const [entityId, stateObj] of Object.entries(states)) {
      if (entityId.startsWith("switch.") && entityId.endsWith("_adaptation")) {
        const prefix = entityId.replace(/^switch\./, "").replace(/_adaptation$/, "");
        const friendlyName = stateObj.attributes.friendly_name?.replace(/ Adaptation$/i, "") || prefix;

        const rgbSensor = states[`sensor.${prefix}_target_rgb`];
        let rgbArray = [255, 180, 100];
        if (rgbSensor?.attributes?.rgb_color && Array.isArray(rgbSensor.attributes.rgb_color)) {
          rgbArray = rgbSensor.attributes.rgb_color;
        } else if (rgbSensor?.state && rgbSensor.state.includes(",")) {
          rgbArray = rgbSensor.state.split(",").map(v => parseInt(v.trim(), 10));
        } else if (states[`sensor.${prefix}_target_color_temp`]?.attributes?.target_rgb) {
          rgbArray = states[`sensor.${prefix}_target_color_temp`].attributes.target_rgb;
        } else {
          rgbArray = this._kelvinToRgb(parseInt(states[`sensor.${prefix}_target_color_temp`]?.state || "4000", 10));
        }

        instances.push({
          prefix,
          name: friendlyName,
          masterSwitch: stateObj,
          enabled: stateObj.state === "on",
          targetBrightness: states[`sensor.${prefix}_target_brightness`]?.state || "100",
          targetKelvin: states[`sensor.${prefix}_target_color_temp`]?.state || "4000",
          rgb: rgbArray,
          phase: states[`sensor.${prefix}_phase`]?.state || "day",
          profile: states[`select.${prefix}_profile`]?.state || "normal",
          weatherBoost: states[`sensor.${prefix}_weather_boost`]?.state || "none",
          overrides: parseInt(states[`sensor.${prefix}_manual_overrides`]?.state || "0", 10),
          presence: states[`sensor.${prefix}_presence_state`]?.state || "N/A",
        });
      }
    }

    return instances;
  }

  _checkAndRender() {
    if (!this._hass) return;

    const instances = this._getInstances();
    const fp = this._computeFingerprint(instances);

    if (fp === this._lastFingerprint && this.shadowRoot.innerHTML !== "") {
      return;
    }
    this._lastFingerprint = fp;
    this._render(instances);
  }

  _render(instances) {
    const t = this._getLang();
    const allProfiles = ["normal", "sleep", "morning", "evening", "focus", "relax"];

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
          font-weight: 700;
          letter-spacing: -0.02em;
        }
        .header-title p {
          margin: 4px 0 0 0;
          opacity: 0.7;
          font-size: 0.95rem;
        }
        .global-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        .btn-global {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.16);
          color: inherit;
          padding: 9px 16px;
          border-radius: 9px;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          transition: background 0.18s ease, transform 0.1s ease;
          user-select: none;
        }
        .btn-global:hover {
          background: rgba(255, 255, 255, 0.16);
        }
        .btn-global:active {
          transform: scale(0.97);
        }
        .btn-global > * {
          pointer-events: none;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
          gap: 20px;
        }
        .zone-card {
          background: var(--ha-card-background, #1d1d24);
          border-radius: 16px;
          padding: 20px;
          border: 1px solid rgba(255, 255, 255, 0.07);
          box-shadow: 0 4px 20px rgba(0,0,0,0.25);
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .zone-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .zone-title-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .zone-name {
          font-size: 1.25rem;
          font-weight: 600;
        }
        .zone-status-badge {
          font-size: 0.7rem;
          padding: 2px 7px;
          border-radius: 10px;
          text-transform: uppercase;
          font-weight: 600;
        }
        .zone-status-badge.on {
          background: rgba(76, 175, 80, 0.2);
          color: #81c784;
        }
        .zone-status-badge.off {
          background: rgba(255, 255, 255, 0.08);
          color: rgba(255, 255, 255, 0.5);
        }
        /* Custom pure HTML Switch */
        .switch {
          position: relative;
          display: inline-block;
          width: 44px;
          height: 24px;
          flex-shrink: 0;
        }
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0; left: 0; right: 0; bottom: 0;
          background-color: rgba(255, 255, 255, 0.18);
          transition: 0.25s;
          border-radius: 24px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 3px;
          background-color: #fff;
          transition: 0.25s;
          border-radius: 50%;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        input:checked + .slider {
          background-color: var(--primary-color, #03a9f4);
        }
        input:checked + .slider:before {
          transform: translateX(20px);
        }
        .zone-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .stat-item {
          background: rgba(0, 0, 0, 0.25);
          padding: 10px 14px;
          border-radius: 10px;
        }
        .stat-item .label {
          font-size: 0.72rem;
          opacity: 0.6;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .stat-item .value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #ffb74d;
          margin-top: 2px;
        }
        .value-color-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .color-rgb-box {
          display: inline-block;
          width: 18px;
          height: 18px;
          border-radius: 4px;
          border: 1px solid rgba(255, 255, 255, 0.4);
          box-shadow: 0 0 8px rgba(0, 0, 0, 0.4);
          flex-shrink: 0;
        }
        .rgb-subtext {
          font-size: 0.72rem;
          font-weight: 500;
          opacity: 0.65;
          margin-top: 2px;
        }
        .kelvin-bar-wrap {
          margin-top: 2px;
        }
        .kelvin-bar {
          height: 6px;
          border-radius: 3px;
          background: linear-gradient(90deg, #ff8c00 0%, #ffd180 35%, #ffffff 60%, #b3e5fc 85%, #81d4fa 100%);
          position: relative;
        }
        .kelvin-pointer {
          position: absolute;
          top: -3px;
          width: 4px;
          height: 12px;
          background: #fff;
          border-radius: 2px;
          box-shadow: 0 0 6px rgba(0,0,0,0.8);
          transform: translateX(-50%);
        }
        .zone-badges {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          font-size: 0.78rem;
        }
        .z-badge {
          padding: 4px 10px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.07);
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .z-badge.boost {
          background: rgba(255, 179, 0, 0.16);
          color: #ffb300;
        }
        .z-badge.presence {
          background: rgba(66, 165, 245, 0.16);
          color: #90caf9;
        }
        .override-alert {
          background: rgba(244, 67, 54, 0.14);
          border: 1px solid rgba(244, 67, 54, 0.3);
          border-radius: 10px;
          padding: 8px 12px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.82rem;
          color: #ff8a80;
        }
        .btn-reset-single {
          background: rgba(244, 67, 54, 0.25);
          border: 1px solid rgba(244, 67, 54, 0.5);
          color: #fff;
          padding: 4px 10px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.75rem;
          font-weight: 600;
          transition: background 0.15s;
        }
        .btn-reset-single:hover {
          background: rgba(244, 67, 54, 0.4);
        }
        .btn-reset-single > * {
          pointer-events: none;
        }
        .profile-chips {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-top: 2px;
        }
        .chip {
          background: rgba(255, 255, 255, 0.07);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: inherit;
          padding: 5px 11px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.78rem;
          transition: all 0.15s ease;
          user-select: none;
        }
        .chip:hover {
          background: rgba(255, 255, 255, 0.14);
        }
        .chip.active {
          background: var(--primary-color, #03a9f4);
          color: #fff;
          border-color: var(--primary-color, #03a9f4);
          font-weight: 600;
          box-shadow: 0 0 10px rgba(3, 169, 244, 0.4);
        }
        .chip > * {
          pointer-events: none;
        }
        .card-actions {
          display: flex;
          gap: 8px;
          margin-top: 6px;
          border-top: 1px solid rgba(255, 255, 255, 0.07);
          padding-top: 12px;
        }
        .btn-card-action {
          flex: 1;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: inherit;
          padding: 7px 10px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.8rem;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          transition: background 0.15s;
        }
        .btn-card-action:hover {
          background: rgba(255, 255, 255, 0.12);
        }
        .btn-card-action > * {
          pointer-events: none;
        }
        .empty-state {
          text-align: center;
          padding: 80px 20px;
          opacity: 0.75;
        }
        .empty-state ha-icon {
          --mdc-icon-size: 56px;
          opacity: 0.4;
          margin-bottom: 12px;
        }
      </style>

      <div>
        <div class="header-bar">
          <div class="header-title">
            <h1>
              <ha-icon icon="mdi:sun-clock"></ha-icon>
              ${t.title}
            </h1>
            <p>${t.subtitle}</p>
          </div>
          <div class="global-actions">
            <button class="btn-global" data-action="all-sleep">
              <ha-icon icon="mdi:bed"></ha-icon>
              <span>${t.allSleep}</span>
            </button>
            <button class="btn-global" data-action="all-apply">
              <ha-icon icon="mdi:lightning-bolt"></ha-icon>
              <span>${t.applyAll}</span>
            </button>
            <button class="btn-global" data-action="all-reset">
              <ha-icon icon="mdi:restore"></ha-icon>
              <span>${t.resetAll}</span>
            </button>
          </div>
        </div>

        ${instances.length === 0 ? `
          <div class="empty-state">
            <ha-icon icon="mdi:lightbulb-alert"></ha-icon>
            <h2>${t.noZones}</h2>
            <p>${t.noZonesDesc}</p>
          </div>
        ` : `
          <div class="grid">
            ${instances.map(inst => {
              const kelvinVal = parseInt(inst.targetKelvin, 10) || 4000;
              const kelvinPct = Math.max(0, Math.min(100, ((kelvinVal - 1800) / (6500 - 1800)) * 100));

              return `
                <div class="zone-card">
                  <div class="zone-header">
                    <div class="zone-title-wrap">
                      <div class="zone-name">${this._escapeHtml(inst.name)}</div>
                      <span class="zone-status-badge ${inst.enabled ? 'on' : 'off'}">
                        ${inst.enabled ? this._escapeHtml(t.active) : this._escapeHtml(t.paused)}
                      </span>
                    </div>
                    <label class="switch" title="Toggle adaptation">
                      <input type="checkbox" class="zone-toggle" data-entity="${this._escapeHtml(inst.masterSwitch.entity_id)}" ${inst.enabled ? 'checked' : ''}>
                      <span class="slider"></span>
                    </label>
                  </div>

                  <div class="zone-stats">
                    <div class="stat-item">
                      <div class="label">${this._escapeHtml(t.targetBright)}</div>
                      <div class="value">${this._escapeHtml(inst.targetBrightness)}%</div>
                    </div>
                    <div class="stat-item">
                      <div class="label">${this._escapeHtml(t.targetColor)}</div>
                      <div class="value value-color-row">
                        <span class="color-rgb-box" style="background: rgb(${inst.rgb.map(v => parseInt(v, 10) || 0).join(',')});" title="RGB: ${inst.rgb.map(v => parseInt(v, 10) || 0).join(', ')}"></span>
                        <span>${this._escapeHtml(inst.targetKelvin)}K</span>
                      </div>
                      <div class="rgb-subtext">RGB(${inst.rgb.map(v => parseInt(v, 10) || 0).join(', ')})</div>
                    </div>
                  </div>

                  <div class="kelvin-bar-wrap">
                    <div class="kelvin-bar">
                      <div class="kelvin-pointer" style="left: ${kelvinPct}%;"></div>
                    </div>
                  </div>

                  <div class="zone-badges">
                    <span class="z-badge"><b>${this._escapeHtml(t.phase)}:</b> ${this._escapeHtml(inst.phase)}</span>
                    <span class="z-badge boost"><b>${this._escapeHtml(t.weather)}:</b> ${this._escapeHtml(inst.weatherBoost.replace('_', ' '))}</span>
                    <span class="z-badge presence"><b>${this._escapeHtml(t.presence)}:</b> ${this._escapeHtml(inst.presence)}</span>
                  </div>

                  ${inst.overrides > 0 ? `
                    <div class="override-alert">
                      <span>⚠️ ${this._escapeHtml(inst.overrides)} ${this._escapeHtml(t.overriddenWarning)}</span>
                      <button class="btn-reset-single" data-action="zone-reset" data-prefix="${this._escapeHtml(inst.prefix)}">
                        ${this._escapeHtml(t.resetOverride)}
                      </button>
                    </div>
                  ` : ''}

                  <div class="profile-chips">
                    ${allProfiles.map(p => `
                      <button
                        class="chip ${inst.profile === p ? 'active' : ''}"
                        data-action="select-profile"
                        data-prefix="${this._escapeHtml(inst.prefix)}"
                        data-profile="${this._escapeHtml(p)}">
                        ${this._escapeHtml(t.profiles[p] || p)}
                      </button>
                    `).join("")}
                  </div>

                  <div class="card-actions">
                    <button class="btn-card-action" data-action="zone-sleep" data-prefix="${inst.prefix}">
                      <ha-icon icon="mdi:bed"></ha-icon>
                      <span>${t.toggleSleep}</span>
                    </button>
                    <button class="btn-card-action" data-action="zone-apply" data-prefix="${inst.prefix}">
                      <ha-icon icon="mdi:lightning-bolt"></ha-icon>
                      <span>${t.applyNow}</span>
                    </button>
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        `}
      </div>
    `;
  }
}

customElements.define("adaptive-circadian-panel", AdaptiveCircadianPanel);
