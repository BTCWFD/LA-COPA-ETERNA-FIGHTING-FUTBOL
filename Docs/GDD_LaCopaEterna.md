# LA COPA ETERNA: SANGRE Y POTRERO
## Game Design Document (GDD) & Arquitectura Técnica AAA

- **Motor & Versión:** Unreal Engine 5.4+ / 5.8.4 (`EngineAssociation: "5.8"`, módulo C++20 `SouthAmericaFightersCore`).
- **Plataformas:** PC (Windows / Steam / Epic), PlayStation 5, Xbox Series X|S.
- **Crossplay & Netcode:** Rollback GGPO determinista a 60 FPS fijos (`16.66 ms/frame`) con Epic Online Services (EOS).
- **Aritmética Core:** Punto Fijo Q32.32 (`FFixedPoint` `int64_t`) libre de desincronización entre compiladores MSVC (x86_64/XSX) y Clang (PS5).
- **Audio Reactivo:** Audiokinetic Wwise 2023.1+ (`MasterMixerHierarchy.wwu` UUID `{19301950-CA4A-4B10-9F00-C0A4EB012026}`, Sidechain Auto-Ducking con `HoldMs: 40ms / 80ms`) y **19 stems `.wav` reales (48 kHz, 16-bit PCM mono)**: 10 cánticos percusivos nacionales CONMEBOL a su BPM exacto, 8 SFX de combate/arbitraje/coro `¡OOOO-LÉ!` y 1 sub-grave háptico DualSense.
- **UI / UX:** Unreal Engine 5.4+ / 5.8.4 CommonUI con Invalidation Boxes, cambio instantáneo de glifos (`<1 ms`) y soporte de Háptica DualSense / Xbox Impulse Triggers.

---

### 1. Estructura de Controles (5 Botones)
- **LP (Light):** Toque corto / Jab rápido (Startup 4-5f).
- **MP (Medium):** Cabezazo / Cuerpo a cuerpo medio (Startup 7-9f).
- **HP (Heavy):** Entrada dura / Patada potente (Startup 11-16f).
- **SK (Special Kick / Balón):** Invoca o patea el balón como proyectil físico o trampa en cancha.
- **GB (Gambeta / Drive):** Finta universal, esquive o Parry táctico (Startup 2f).

---

### 2. Roster Oficial: 16 Leyendas + Jefe Final (`DT_SouthAmericaRoster.json` — 17 Personajes)
1. **O Fenômeno (Brasil — `FENOMENO_BR`, 10,000 HP, Dash 15f):** Rushdown explosivo con *Pedalada Mortal* (`236+LP`) y dashes con Super Armor.
2. **O Bruxo (Brasil — `BRUXO_BR`, 9,500 HP, Dash 17f):** Trickster / Mix-up master, *Elástica* (`41236+MP`) y pases *No-Look* (`236+SK`).
3. **El Cañón (Argentina — `CANON_AR`, 10,500 HP, Dash 19f):** Powerhouse Shoto, *Bati-Cañonazo* (`236+SK` / `236+[SK]`) y Wall Bounce.
4. **La Pulga (Argentina — `PULGA_AR`, 9,000 HP, Dash 14f):** Pixie / Footsies, hurtbox reducida, *Slalom Imposible* (`236+MP`) y Ultimate *Coronación* de 4f (`214214+HP+SK`).
5. **El Pibe (Colombia — `PIBE_CO`, 10,000 HP, Dash 21f):** Setplay Zoner, *Pase Filtrado* (`236+SK`) y balones trampa en suspensión (`214+SK` / `22+SK`).
6. **El Loco (Colombia — `LOCO_CO`, 10,200 HP, Dash 18f):** Counter-Acrobat, contraataque aéreo *El Escorpión* (`214+SK`) y despejes de puños (`623+HP`).
7. **El Pistolero (Uruguay — `PISTOLERO_UY`, 10,800 HP, Dash 20f):** Grappler híbrido / Brawler, agarre de comando *Presión Asfixiante* (`41236+LP`) y *La Mano Salvadora* (`22+GB`).
8. **El Matador (Uruguay — `MATADOR_UY`, 10,000 HP, Dash 18f):** Long-Range Hybrid ambidiestro, *Efecto Jabulani* (`236+SK`) y cabezazo en plancha (`[4]6+HP`).
9. **Bam-Bam (Chile — `BAMBAM_CL`, 10,000 HP, Dash 17f):** Air-Dominance / Divekick, *Cabezazo Suspendido* (`j.236+MP`) y Hang-Time en el aire (`8+GB`).
10. **El Rey (Chile — `REY_CL`, 10,400 HP, Dash 16f):** Berserker Rekka Brawler, *Trancazo Real* de 3 impactos (`236+LP`) y menor costo de Gambeta.
11. **El Bulldog (Paraguay — `BULLDOG_PY`, 11,500 HP, Dash 23f):** Big-Body Grappler / Zoner, *Tiro Libre con Barrera* (`236+SK`) y *Agarre del Cuello* (`41236+HP`).
12. **El Maestro (Perú — `MAESTRO_PE`, 9,800 HP, Dash 17f):** Technical Footsies, *Tiro de Tres Dedos* (`236+SK~8` / `236+SK~2`) y huacha de cambio de lado (`214+LP`).
13. **El Tren Amazónico (Ecuador — `TREN_EC`, 9,600 HP, Dash 13f):** Speedster / Run-Cancel, *Expreso por la Banda* (`236+GB`) con ventaja `+3` on-block.
14. **El Huracán Vinotinto (Venezuela — `HURACAN_VE`, 10,200 HP, Dash 19f):** Dead-Ball Sniper, *Zurda de Oro Folha Seca* (`236+SK`) sin escalado de daño por distancia.
15. **El Diablo Andino (Bolivia — `DIABLO_BO`, 9,800 HP, Dash 18f):** Stamina Debuffer, *Balón Pesado* (`214+SK`) que aplica *Falta de Aire (3,600m)*.
16. **Le Général (Francia Invitado — `GENERAL_FR`, 10,000 HP, Dash 17f):** Tactical Stance, *Roulette de Marseille* (`236+MP`) y *Coup de Tête* (`41236+HP`).
17. **El Juez Supremo (V.A.R. - ZERO — `VAR_ZERO_BOSS`, 13,000 HP, Dash 12f):** Jefe Final del Sindicato Arbitral con *Láser de Offside* (`236+SK`), *Tarjeta Roja* (`623+HP`) y *V.A.R. Rewind* (`22+GB`).

---

### 3. Escenarios (10 Estadios Míticos CONMEBOL con Wall Break y BPM Exacto)
- **Maracanã (Brasil — `115 BPM`):** Batucada de Samba; ruptura hacia Explanada de Samba y vestuarios históricos.
- **La Bombonera (Argentina — `128 BPM`):** Bombo con platillo de murga, cancha estrecha (`2,200u`); ruptura hacia Calle Caminito.
- **Estadio Centenario (Uruguay — `120 BPM`):** Cuerda de tambores Candombe, neblina del Plata; ruptura hacia Museo de 1930.
- **Metropolitano de Barranquilla (Colombia — `130 BPM`):** Tambora caribeña a `40°C`; ruptura hacia Carnaval Exterior.
- **Coliseo de Ñuñoa (Chile — `125 BPM`):** Cueca brava y bombo cordillerano; ruptura hacia el Memorial y pista atlética.
- **Defensores del Chaco (Paraguay — `120 BPM`):** Polka Guaraní de bronces, muros pesados (4 impactos) y tormenta eléctrica.
- **Estadio Nacional de Lima (Perú — `118 BPM`):** Cajón peruano afro-costeño y quijada, fachada LED reactiva bajo la *Garúa*.
- **Atahualpa / Casa Blanca (Ecuador — `135 BPM`):** San Juanito andino en la línea ecuatorial, lluvia con ceniza volcánica y teleférico.
- **Monumental del Ávila (Venezuela — `170 BPM`):** Joropo y tambor urbano frente al Cerro El Ávila, terraza VIP con helipuerto.
- **Hernando Siles de La Paz (Bolivia — `3,600m`, `110 BPM`):** Bombo legüero y sikus sobre las nubes (`RTPC_Stage_Altitude_Meters = 3600m`), cancha ancha (`2,600u`) y muros frágiles (2 impactos).

---

### 4. Boss Final: "El Juez Supremo" (V.A.R. - ZERO — `VAR_ZERO_BOSS`)
- **Atributos Oficiales:** `13,000 HP` (`MaxHealth: 13000`), `StunThreshold: 1,500`, `ForwardDashFrames: 12f`, `BackDashFrames: 14f`.
- **Fase 1 (La Ley de Hierro):** Zoner opresivo con *Láser de Línea de Offside* (`VAR_OFFSIDE_TRAP`, `236+SK`) y *Sentencia de Tarjeta Roja* (`VAR_RED_CARD`, `623+HP`).
- **Fase 2 (Tiempo de Descuento Infinito):** Activa su movimiento insignia *V.A.R. Rewind* (`VAR_REWIND_90F`, `22+GB`), rebobinando `90 frames` (`1.5 s` a `60 Hz`) del Ring Buffer determinista GGPO para anular combos recibidos.
- **Condición de Victoria:** Encadenar **3 Gambetas Perfectas** (`PARRY_GAMBETA` de `2f`) provoca `System Overload` durante `240 frames` y habilita el Ultimate Cooperativo CONMEBOL (*Grito Sagrado*).
