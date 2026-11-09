# Adaptive Circadian Lighting for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced circadian rhythm lighting integration for Home Assistant that dynamically synchronizes brightness, color temperature (Kelvin), and RGB colors across your home.

Inspired by and building upon `basnijholt/adaptive-lighting`, this component redesigns the architecture to feature an interactive GUI, weather and cloud compensation, first-class RGB and Kelvin modes, and presence automation with state memory for manual adjustments.

---

## 🌍 Supported Languages / Støttede Språk

The integration, options flow, entities, and UI cards automatically adapt to your Home Assistant language setting:
- 🇬🇧 **English** (`en`)
- 🇳🇴 **Norsk (Bokmål)** (`nb`, `no`)
- 🇪🇸 **Español** (`es`)
- 🇩🇪 **Deutsch** (`de`)
- 🇫🇷 **Français** (`fr`)
- 🇵🇹 🇧🇷 **Português (Portugal & Brasil)** (`pt`, `pt-BR`)

---

## ✨ Key Features

### 1. Four Calculation Engines
- **Hybrid (Recommended):** Blends solar elevation with user-defined time anchors (e.g. wakeup never earlier than 06:30, evening wind-down guaranteed by 21:30 even during high-latitude midnight sun).
- **Pure Sun Position (Astral):** Classic astronomical calculation following sunrise, solar noon, sunset, and twilight.
- **Custom 24h Curve (Spline):** 24-hour piecewise cubic/cosine spline curve using custom control points `[(hour, brightness_pct, kelvin), ...]`.
- **Weather / Lux Compensated:** Real-time sensor-driven modulation.

### 2. Flexible Color Modes (Kelvin, RGB & Auto-Hybrid)
- **Color Temperature (Kelvin):** Native white-spectrum LED control (Tuneable White / CCT).
- **RGB Mode:** Direct RGB color control for LED strips and colored bulbs.
- **Auto / Hybrid (Recommended):** Employs native Kelvin white diodes during normal daylight hours (e.g. 2200K–6500K), and automatically shifts to deep amber/red RGB (1200K–1800K) at night to bypass hardware white diode limits and preserve melatonin production.

### 3. Weather & Cloud Boost (Sensor Fusion)
- Directly reads Home Assistant's built-in `weather.*` entity (cloud coverage and conditions like `cloudy`, `rainy`, `fog`).
- **Priority Hierarchy:**
  1. **Physical Lux Sensor (Highest Priority):** Measured outdoor or indoor lux.
  2. **Weather Entity:** Automatically applies a configurable "Cloud Boost" (e.g. +25% brightness and crisper Kelvin) on dark, overcast days.
  3. **Circadian Curve:** Base circadian schedule.

### 4. Presence Automation & State Memory
- Connects to room motion/presence sensors (`binary_sensor.*`).
- **Active Occupancy:** Keeps any manual bulb adjustment locked in without disruption while the room is in use (e.g. cooking in the kitchen or working at an office desk).
- **Staged 2-Step Vacancy:**
  - *Dimming Phase:* Dims lights down to minimum (e.g. 10%) after a configurable timeout (e.g. 3 minutes).
  - *Turn-Off Phase:* Completely powers off lights after an additional timeout (e.g. 2 minutes).
- **Grace Period (Short Departures):** If someone leaves temporarily (e.g. to fetch a coffee) and returns within the grace window (e.g. 15 minutes), **their manual lighting setting is immediately restored**! Beyond the grace period, lights cleanly turn back on with adaptive circadian lighting.

### 5. Automated Sleep Schedule & Weekend Support
- **Built-in Schedule:** Automatically activates Sleep Mode during your preferred bedtime window (e.g. 23:00 to 06:30) and seamlessly transitions back to normal circadian lighting in the morning, eliminating the need for extra Home Assistant automations.
- **Separate Weekend Schedule:** Configure different bedtimes and wake-up times for weekends (Friday/Saturday evening and Saturday/Sunday morning).
- **Room-Specific Sleep Settings:** Customize sleep brightness (e.g. 1% in the bedroom vs. 8% in the hallway/kitchen) and color temperature (e.g. 1800K or deep red RGB) individually for each room.
- **Sleep Motion Behavior:** Choose whether motion sensors turn on soft nightlights or remain in Do Not Disturb (DND) mode during sleep hours.
- **External Bedtime Sensor:** Link optional sleep tracking sensors (e.g. `input_boolean.sleep_mode`, phone charger, or smart mattress) to dynamically synchronize Sleep Mode.

### 6. Fine-Tuned Solar & Operational Controls
- **Sunrise & Sunset Offsets:** Shift morning ramp and evening wind-down (+/- 120 minutes) to account for terrain, surrounding buildings, or blinds.
- **Adapt Only on Turn-On:** Optional mode where lights adapt only when powered on, remaining completely static while on to prevent distracting gradual shifts during movie nights or focused work.
- **Evening Brightness Cap:** Hard ceiling on maximum allowable brightness in the evening/night regardless of daylight.
- **Configurable Interval:** Set update frequency anywhere from 10 to 300 seconds (default 60s) to balance responsiveness with Zigbee/Z-Wave mesh traffic.

### 7. Interactive GUI & Lovelace Card
- **Lovelace Custom Card (`adaptive-circadian-card`):**
  - Interactive SVG 24h curve with day/night zones and live "NOW" indicator.
  - One-click profile chips: `Normal`, `Sleep`, `Morning`, `Evening`, `Focus`, `Relax`.
  - Live status badges for weather boost, presence, and manual overrides.
  - 1-click button to reset manual overrides and restore automatic control.
- **Custom Sidebar Panel (`/adaptive-circadian`):**
  - Dedicated full-screen dashboard in Home Assistant's sidebar displaying all house zones side-by-side with global toggles.

### 8. Immediate Turn-On Adaptation (Nighttime Protection)
- Reacts immediately to light state transitions from off to on so that when a light is switched on at night (via motion sensor or wall switch), it adapts directly to the calculated circadian target without delay.

---

## 📦 Installation

### Option 1: Manual Installation
1. Copy the `custom_components/adaptive_circadian_lighting` directory into your Home Assistant `<config_dir>/custom_components/` folder:
   ```bash
   cp -r custom_components/adaptive_circadian_lighting /path/to/homeassistant/config/custom_components/
   ```
2. Restart Home Assistant.
3. In Home Assistant, go to **Settings -> Devices & Services -> Add Integration**.
4. Search for **Adaptive Circadian Lighting** and follow the multi-step setup wizard.

### Option 2: HACS (Custom Repository)
1. In Home Assistant, open **HACS -> Integrations**.
2. Click the three dots in the top right corner and choose **Custom repositories**.
3. Add this repository URL, category: **Integration**.
4. Click **Download**, then restart Home Assistant.

---

## 🎨 Lovelace Card Setup

The custom Lovelace card is automatically registered when the integration is installed! Simply edit your dashboard and add:

```yaml
type: custom:adaptive-circadian-card
entity: switch.living_room_adaptation
title: Living Room
```

---

## 🛠️ Services

The integration exposes the following services under domain `adaptive_circadian_lighting`:
- `adaptive_circadian_lighting.apply_now`: Immediately calculates and pushes target values to lights.
- `adaptive_circadian_lighting.reset_manual_override`: Clears manual overrides and resumes automated adaptation.
- `adaptive_circadian_lighting.set_profile`: Activates a lighting profile (`normal`, `sleep`, `morning`, `evening`, `focus`, `relax`).
- `adaptive_circadian_lighting.toggle_sleep_mode`: Toggles sleep mode on/off.

---

## 🧪 Testing & Verification

Run the automated test suite locally:
```bash
python3 -m unittest discover tests
```

---

<details>
<summary><b>🇳🇴 Norsk Dokumentasjon (Klikk for å utvide)</b></summary>

### Norsk sammendrag
**Adaptive Circadian Lighting** tilpasser automatisk lysstyrke og fargetemperatur (Kelvin og RGB) i hjemmet basert på døgnrytme, solposisjon og værforhold.

**Hovedfordeler:**
- **Hybrid solmodell:** Aldri fullt dagslys før kl. 06:30, og garantert kveldslys senest 21:30 selv om sommeren.
- **Værkompensering (Cloud Boost):** Henter værdata fra `weather.*` og øker automatisk lysstyrken (+25 %) på mørke og overskyede dager.
- **Bevegelsessensor med minne:** Lyset dimmes i 2 trinn når rommet er tomt, og husker manuelle innstillinger dersom du forlater rommet en kort stund (f.eks. henter en kaffe).
- **Innebygd Tidsplan for Nattmodus:** Angi faste klokkeslett for nattmodus (f.eks. 23:00 til 06:30) med egen helgeplan, romspesifikk nattstyrke (f.eks. 1 % på soverom vs. 8 % på kjøkken) og «Ikke forstyrr»-valg for bevegelsessensorer.
- **Soloppgang- og solnedgangsforskyvning:** Juster kurven med +/- minutter tilpasset lokale lysforhold og nabobygg.
- **Kun tilpass ved tenning:** La lyset forbli statisk etter tenning for å unngå forstyrrende lysendringer under filmer eller måltider.
- **Kveldsgrense for lysstyrke:** Sett et automatisk tak på lysstyrke om kvelden og natten.
- **Umiddelbar tilpasning ved tenning:** Pærer tilpasses døgnrytmens målnivå med en gang de slås på, uten forsinkelse eller sjokkblits om natten.
- **Innebygd GUI:** Interaktivt Lovelace Dashboard-kort og dedikert sidepanel i Home Assistant.
</details>
