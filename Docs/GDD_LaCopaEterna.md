# LA COPA ETERNA: SANGRE Y POTRERO
## Game Design Document (GDD) & Arquitectura Técnica AAA

- **Plataformas:** PC (Windows / Steam / Epic), PlayStation 5, Xbox Series X/S.
- **Crossplay & Netcode:** Rollback GGPO determinista a 60 FPS fijos con Epic Online Services (EOS).
- **Aritmética Core:** Punto Fijo Q32.32 (`FFixedPoint` int64) libre de desincronización entre x86_64 y consolas.
- **Audio Reactivo:** Audiokinetic Wwise 2023.1+ (Buses de Ducking, cánticos por selección, comentaristas reactivos).
- **UI / UX:** Unreal Engine 5.4+ CommonUI con Invalidation Boxes y soporte de Háptica DualSense / Xbox Impulse Triggers.

---

### 1. Estructura de Controles (5 Botones)
- **LP (Light):** Toque corto / Jab rápido (Startup 4-5f).
- **MP (Medium):** Cabezazo / Cuerpo a cuerpo medio (Startup 7-9f).
- **HP (Heavy):** Entrada dura / Patada potente (Startup 11-16f).
- **SK (Special Kick / Balón):** Invoca o patea el balón como proyectil o trampa.
- **GB (Gambeta / Drive):** Finta universal, esquive o Parry táctico (Startup 2f).

---

### 2. Roster de 16 Leyendas (10 CONMEBOL + Invitados)
1. **O Fenômeno (Brasil):** Rushdown explosivo con *Pedalada Stance* y dashes con Super Armor.
2. **O Bruxo (Brasil):** Trickster / Mix-up master, *Elástica* y pases *No-Look*.
3. **El Cañón (Argentina):** Powerhouse Shoto, *Bati-Cañonazo* cargado y Wall Bounce.
4. **La Pulga (Argentina):** Pixie / Footsies, hurtbox diminuta, caminata supersónica y Ultimate de 4f.
5. **El Pibe (Colombia):** Setplay Zoner, balones trampa en suspensión y control de espacio.
6. **El Loco (Colombia):** Counter-Acrobat, parry *El Escorpión* y salidas aéreas de puños.
7. **El Pistolero (Uruguay):** Grappler híbrido / Brawler, agarre de comando *Mordisco Táctico* y *Garra Charrúa*.
8. **El Matador (Uruguay):** Long-Range Hybrid ambidiestro, *Efecto Jabulani* y cabezazo en picada.
9. **Bam-Bam (Chile):** Air-Dominance / Divekick, *El Helicóptero* con Hang-Time suspendido.
10. **El Rey (Chile):** Berserker Rekka Brawler, *Trancazo Real* de 3 impactos y consumo reducido de Gambeta.
11. **El Bulldog (Paraguay):** Big-Body Grappler / Zoner (11,500 HP), tiros libres teledirigidos y agarre del cuello.
12. **El Maestro (Perú):** Technical Footsies, *Tiro de Tres Dedos* con curva tardía y caño de cambio de lado.
13. **El Tren Amazónico (Ecuador):** Speedster / Run-Cancel, dash de 13f y cancelaciones con ventaja on-block.
14. **El Huracán Vinotinto (Venezuela):** Dead-Ball Sniper, *Zurda de Oro Folha Seca* sin daño reducido a distancia.
15. **El Diablo Andino (Bolivia):** Stamina Debuffer, aplica *Falta de Aire (3600m)* y merma velocidad rival.
16. **Le Général (Francia - Invitado):** Tactical Stance y contraataques corporales de media distancia.

---

### 3. Escenarios (10 Estadios Míticos con Wall Break)
- **Maracanã (Brasil):** Explanada de Samba y vestuarios históricos tras romper las redes.
- **La Bombonera (Argentina):** Escenario estrecho (2200u); ruptura hacia Calle Caminito.
- **Estadio Centenario (Uruguay):** Neblina del Plata y lluvia; ruptura hacia Museo de 1930.
- **Metropolitano de Barranquilla (Colombia):** 40°C a aguacero tropical; ruptura hacia comparsas del Carnaval.
- **Estadio Nacional de Santiago (Chile):** Cordillera nevada; ruptura hacia el Memorial y pista atlética.
- **Defensores del Chaco (Paraguay):** Muros pesados (4 hits), relámpagos subtropicales.
- **Nacional de Lima (Perú):** Fachada LED reactiva, disipación de niebla *Garúa* con ataques de fuego/viento.
- **Atahualpa / Casa Blanca (Ecuador):** Sin sombra a mediodía, ceniza de volcán activo y mirador del teleférico.
- **Olímpico de la UCV / Monumental del Ávila (Venezuela):** Cerro El Ávila al atardecer, terraza VIP con drones.
- **Hernando Siles (Bolivia - 3600m):** Cancha ancha (2600u), muros frágiles (2 hits) y efecto acústico de fatiga.

---

### 4. Boss Final: "El Juez Supremo" (V.A.R. - ZERO)
- **Fase 1:** Zoner opresivo con lásers de *Línea de Offside* (Micro-stun si atacas de frente) y teletransporte.
- **Fase 2:** *V.A.R. Rewind* (rebobina 90 frames del buffer GGPO anulando combos del jugador).
- **Condición de Victoria:** 3 *Gambetas Perfectas* causan *System Overload* y habilitan el Ultimate Cooperativo CONMEBOL.
