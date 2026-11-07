# Adaptive Circadian Lighting for Home Assistant

En avansert døgnrytmebelysnings-integrasjon for Home Assistant som automatisk tilpasser lysstyrke, fargetemperatur (Kelvin) og RGB-farger gjennom døgnet.

Basert på og inspirert av `basnijholt/adaptive-lighting`, men utvidet med:
- **4 Døgnrytmemodeller:** Ren solposisjon, Hybrid (sol + faste tidsankere), Egendefinert 24t kurve, og Vær-/Lux-kompensert.
- **Valgbar Fargetilpasning:** Kelvin, ren RGB, eller Auto-hybrid (Kelvin om dagen, dyp oransje/rød RGB om natten).
- **Vær- og Skydekke-prioritering:** Kobling mot `weather.*` og/eller fysisk lux-sensor, med prioritert "Cloud Boost" for mørke dager.
- **Tilstedeværelsesstyring med Minne:** Automatisk 2-trinns dimming og avskruing ved tomt rom, og intelligent minne som gjenoppretter manuelle innstillinger ved kort fravær (f.eks. hente en kaffe).
- **Innebygd GUI:** Interaktivt Lovelace Dashboard-kort og dedikert sidepanel i Home Assistant.
- **Anti-blending (Night turn-on):** Avskjærer `light.turn_on` slik at nattlamper tennes direkte på dempet nivå uten blitsing.
