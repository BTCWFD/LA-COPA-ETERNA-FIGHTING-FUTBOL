# Plan Maestro de Arte 2D — Hojas de Frames de Combate (Multi-Frame Sprite Sheets)
**Proyecto:** LA COPA ETERNA: SANGRE Y POTRERO (*SouthAmericaFightersCore*)  
**Dirección de Arte Técnica:** Pipeline 2D Combat Sprites (`WebLab/app.js` Tab 6 Arena + Fallbacks / Pre-viz UE5 60.0 FPS)  
**Catálogo Determinista:** [`ActionFrames_PromptCatalog.json`](../Assets/Sprites2D/ActionFrames/ActionFrames_PromptCatalog.json) (generado por [`build_action_frames_plan.py`](../Scripts/build_action_frames_plan.py))

---

## 1. Especificación de Dirección de Arte y Reglas de Producción

Para reemplazar los recortes articulados estáticos por poses de combate auténticas de juego de pelea 2D AAA sin perder **ni un ápice de fidelidad** respecto a los *Turnarounds* fotorrealistas aprobados, todas las láminas generadas en Gemini deben cumplir estrictamente las siguientes reglas técnicas:

1. **Bloqueo de Identidad y Kit (100% Reference Lock):**
   - Cada generación en Gemini **debe adjuntar obligatoriamente** la lámina maestra [`Assets/Design3D_Turnarounds/Turnaround_<CODE>.png`](../Assets/Design3D_Turnarounds/) del luchador correspondiente.
   - Se exige coincidencia exacta en rostro, tono de piel, peinado/barba/bigote, complexión física, dorsal, patrón de camiseta, cuello, pantaloneta, medias, vendajes/guantes y botines.
2. **Fondo Chromakey / Studio Grey Uniforme (`#383B42`):**
   - Fondo plano continuo `#383B42` idéntico al estándar de `extract_turnaround_sprites_and_textures.py` para permitir extracción alfa limpia mediante *floodfill* y eliminación de bordes sin contaminar cabello negro, shorts o botines.
   - **Prohibido:** pasto de cancha, gradas, viñetas radiales en esquinas, gradientes bruscos o sombras proyectadas en el piso (la sombra elíptica y el césped los dibuja `drawFighterOnT6Canvas` en `WebLab/app.js`).
3. **Cero Ruido Gráfico en Grilla:**
   - **ZERO líneas de grilla**, marcos, cajas o divisores visuales.
   - **ZERO etiquetas de texto**, números de celda (`1..6`), nombres de pose o marcas de agua.
   - **ZERO VFX o balones dentro del sprite:** sin balones pintados, sin chispas, sin láseres ni estelas de impacto (los proyectiles `PROJ`/`PROJ_EX` y arcos de golpe en estado `ACTIVE` los renderiza el motor).
4. **Aislamiento Estricto por Celda (Zero Cell Overlap):**
   - Composición apaisada `16:9` dividida lógicamente en **3 columnas × 2 filas** (6 celdas de igual tamaño).
   - Cada figura completa (de cabeza/cabello a tapones de los botines) debe quedar contenida cómodamente dentro del **80%–85% interno** de su celda, manteniendo **escala corporal uniforme** entre las 6 poses y sin que extremidades, cabello o drones invadan celdas vecinas.
5. **Cámara Ortográfica Lateral Pura (`+X` Derecha):**
   - Todos los *keyframes* miran estrictamente hacia la **DERECHA (`+X`)** en perfil lateral de pelea 2D (`facingRight = true` en `WebLab/app.js`; el motor aplica `ctx.scale(-1, 1)` automáticamente para `P2` o cambios de lado).

---

## 2. Taxonomía Oficial: 2 Láminas × 6 Frames (`3×2`) por Luchador

Cada uno de los **17 luchadores** cuenta con **2 láminas** (**12 keyframes** únicos por personaje = **204 frames totales** en producción):

### 2.1 Lámina A — `SheetA_<CODE>.png`: *Locomotion & Core Combat* (`3 columnas × 2 filas`)

| Celda (`Fila, Col`) | ID de Frame | Pose y Coreografía Exacta (Mirando `+X`) |
|---|---|---|
| **R1, C1** | `IDLE_GUARD` | Guardia de combate lateral 3/4 mirando `+X`, rodillas flexionadas, peso equilibrado, puños arriba en guardia cerrada. |
| **R1, C2** | `RUN_1` | Zancada de sprint A: rodilla cercana alta hacia adelante (`+X`), pierna trasera impulsándose atrás, torso inclinado ~26° al frente, brazos bombeando en oposición. |
| **R1, C3** | `RUN_2` | Zancada de sprint B opuesta: pierna trasera avanzando con fuerza, pierna delantera extendida hacia atrás, torso girado rítmicamente con braceo contrario. |
| **R2, C1** | `CROUCH` | Sentadilla baja de guardia (*crouch*) mirando `+X`, rodillas profundamente flexionadas, pecho inclinado ~30° al frente, mentón cubierto tras manos en guardia compacta. |
| **R2, C2** | `PUNCH_LP` | Jab recto veloz mirando `+X`, cadera y torso rotados dentro del golpe, brazo y puño delantero totalmente extendidos horizontalmente, puño trasero protegiendo el mentón. |
| **R2, C3** | `KICK_HP` | Patada alta frontal/circular de artes marciales mirando `+X`, pie de apoyo firme, pierna ejecutora y botín lanzados al frente a altura de pecho/cabeza, torso inclinado atrás en contrapeso. |

### 2.2 Lámina B — `SheetB_<CODE>.png`: *Aerial, Defense & Signature Specials* (`3 columnas × 2 filas`)

| Celda (`Fila, Col`) | ID de Frame | Pose y Coreografía Exacta (Mirando `+X`) |
|---|---|---|
| **R1, C1** | `JUMP` | Salto atlético en el aire mirando `+X`, rodillas recogidas hacia arriba, cuerpo compacto en suspensión, brazos equilibrados listos para ataque aéreo. |
| **R1, C2** | `BLOCK_GUARD` | Guardia cerrada reforzada de brazos cruzados absorbiendo impacto pesado mirando `+X`, rodillas flexionadas bajas, botines anclados contra el *pushback*, mentón oculto. |
| **R1, C3** | `HITSTUN` | Retroceso dramático (*whip-back recoil*) al recibir un golpe limpio desde `+X`, torso quebrado hacia atrás, cabeza echada atrás por el impacto, brazos abiertos. |
| **R2, C1** | `SHOT_SK` | Remate explosivo / pose especial insignia adaptada al arquetipo de `ROSTER_DATA` (ej. *El Escorpión* invertido para `LOCO_CO`, *Presión Asfixiante* clinch/rodillazo para `PISTOLERO_UY`, *Tiro de Tres Dedos* para `MAESTRO_PE`, *Zurda de Oro Folha Seca* para `HURACAN_VE`). |
| **R2, C2** | `CHILENA_SP` | Patada acrobática aérea invertida (*Chilena* / *Tijera* / *Volea* / *Purga*) con pierna ejecutora extendida hacia arriba/adelante rumbo a `+X`. |
| **R2, C3** | `KO` | Derribo completo (*Knockdown*) tendido horizontalmente cerca de la base de la celda, boca arriba/de lado (cabeza hacia `-X`, botines descansando hacia `+X`), inconsciente. |

---

## 3. Mapeo Completo de Estados del Motor (`WebLab/app.js`) a Keyframes 2D

Basado exactamente en la máquina de estados `createMatchFighter` (`WebLab/app.js` L2139), `startFighterMove` (L2544–2596) y el catálogo de combate `T6_MOVES` (L2111–2122):

### 3.1 Estados de Locomoción, Defensa y Reacción

| Estado en `WebLab/app.js` | Keyframe(s) Asignado(s) | Regla de Reproducción / Cadencia en Motor |
|---|---|---|
| `IDLE` | `IDLE_GUARD` | Pose base con micro-respiración vertical (`sin(t * 0.14) * 1.5px`) y ligero balanceo de guardia. |
| `WALK_F` | `RUN_1` → `IDLE_GUARD` → `RUN_2` | Ciclo alternado cada `7 frames` (`60 FPS`) avanzando hacia `+X` con zancada controlada. |
| `WALK_B` | `RUN_2` → `IDLE_GUARD` → `RUN_1` | Ciclo inverso cada `8 frames` retrocediendo en guardia mirando al rival. |
| `DASH_F` | `RUN_1` ↔ `RUN_2` | Alternancia rápida cada `4 frames` con inclinación adicional `+4°` y estela de velocidad verde (`#00e676`). |
| `DASH_B` | `JUMP` → `RUN_2` | Salto rasante hacia atrás (`-X`) en los primeros `6f` seguido de aterrizaje en `RUN_2`. |
| `CROUCH` | `CROUCH` | Fijo en `CROUCH` reduciendo la hurtbox visual (`baseH * 0.66`, L3662). |
| `JUMP` | `JUMP` | Fijo en `JUMP` con ligera rotación según velocidad vertical `f.vy` (inclinación al subir/caer). |
| `BLOCKSTUN` | `BLOCK_GUARD` | Fijo en `BLOCK_GUARD` + escudo cian translúcido frontal y retroceso por *pushback*. |
| `PARRY` *(botón `GB` / `5GB`, S:2f A:14f R:14f)* | `BLOCK_GUARD` *(S/R)* / `IDLE_GUARD` + *flash* *(A)* | Startup (`F1–F2`): `BLOCK_GUARD`; Active (`F3–F16`): pose de esquive adelantado (`IDLE_GUARD` desplazado `+12px` + aura `#00e5ff`); Recovery (`F17–F30`): `IDLE_GUARD`. |
| `HITSTUN` | `HITSTUN` | Fijo en `HITSTUN` con vibración de *hitstop* (`±3px`) y destello rojo `#ff2a54`. |
| `KO` | `HITSTUN` *(F1–F8)* → `KO` *(F9+)* | Transición breve de impacto en `HITSTUN` al caer y reposo definitivo en `KO` en el suelo. |

### 3.2 Estados de Ataque (`T6_MOVES` — `STARTUP` / `ACTIVE` / `RECOVERY`)

| MoveKey (`T6_MOVES`) | Ventana (`S / A / R`) | `STARTUP` (Preparación) | `ACTIVE` (Caja Roja Activa) | `RECOVERY` (Recuperación) |
|---|---|---|---|---|
| `LP` *(5LP Jab)* | `4f / 4f / 7f` | `IDLE_GUARD` *(torsión atrás)* | `PUNCH_LP` | `IDLE_GUARD` |
| `MP` *(5MP Cabezazo Medio)* | `7f / 5f / 12f` | `CROUCH` *(carga)* | `PUNCH_LP` / `RUN_1` *(embestida adelante)* | `IDLE_GUARD` |
| `HP` *(5HP Entrada Potente)* | `11f / 6f / 18f` | `RUN_2` *(retroceso de pierna)* | `KICK_HP` | `RUN_1` → `IDLE_GUARD` |
| `SK` *(5SK Disparo de Balón)* | `12f / 4f / 18f` | `RUN_2` *(armado de pierna)* | `SHOT_SK` | `IDLE_GUARD` |
| `SP_236` *(236+SK Cañonazo Esp.)* | `13f / 6f / 17f` | `CROUCH` → `RUN_2` | `SHOT_SK` *(+ lunge `+18px`)* | `RUN_1` → `IDLE_GUARD` |
| `SP_623` *(623+HP Despeje DP)* | `5f / 9f / 22f` | `CROUCH` *(F1–F5 invuln)* | `CHILENA_SP` *(ascenso `vy: -11`)* | `JUMP` *(caída)* → `CROUCH` |
| `SP_41236` *(41236+LP Agarre/Elástica)* | `6f / 5f / 20f` | `RUN_1` *(avance)* | `SHOT_SK` o `PUNCH_LP` *(según arquetipo)* | `IDLE_GUARD` |
| `SUPER_1` *(236236+SK Super Nv.1)* | `6f / 14f / 24f` | `CROUCH` *(super-flash)* | `SHOT_SK` *(F1–F7)* → `KICK_HP` *(F8–F14)* | `IDLE_GUARD` |
| `ULT_3` *(214214+HP+SK Grito Sagrado Nv.3)* | `4f / 22f / 30f` | `CROUCH` *(ink-flash)* | `SHOT_SK` *(F1–F8)* → `CHILENA_SP` *(F9–F22)* | `JUMP` → `IDLE_GUARD` |

> **Nota sobre `GB` (Gambeta / Parry):** En `startFighterMove` (`WebLab/app.js` L2568), `moveKey === 'GB'` transiciona directamente al estado `PARRY` en lugar de `STARTUP`, por lo que su mapeo visual corresponde a la fila `PARRY` de la tabla 3.1.

---

## 4. Inventario de los 17 Luchadores y Rutas de Archivos Destino

Cada luchador tiene un total de **15 archivos** asociados en este pipeline:
- **1 Referencia Turnaround:** `Assets/Design3D_Turnarounds/Turnaround_<CODE>.png`
- **2 Hojas Maestras 3×2:** `Assets/Sprites2D/ActionFrames/Sheets/SheetA_<CODE>.png` y `SheetB_<CODE>.png`
- **12 Frames Recortados (Alpha RGBA):** `Assets/Sprites2D/ActionFrames/<CODE>/<FRAME>.png` donde `<FRAME>` ∈ `{IDLE_GUARD, RUN_1, RUN_2, CROUCH, PUNCH_LP, KICK_HP, JUMP, BLOCK_GUARD, HITSTUN, SHOT_SK, CHILENA_SP, KO}`

| # | Código (`CODE`) | Luchador (`DisplayName`) | Arquetipo (`ROSTER_DATA`) | Especial Insignia (`SHOT_SK` / `CHILENA_SP`) | Referencia Turnaround | Hojas 3×2 Destino | Carpeta de 12 Frames Recortados |
|---|---|---|---|---|---|---|---|
| 1 | `FENOMENO_BR` | **O Fenômeno** | Rushdown Explosivo | Definición Cruzada / Pentacampeón | `Assets/Design3D_Turnarounds/Turnaround_FENOMENO_BR.png` | `SheetA_FENOMENO_BR.png` / `SheetB_FENOMENO_BR.png` | `Assets/Sprites2D/ActionFrames/FENOMENO_BR/<FRAME>.png` |
| 2 | `BRUXO_BR` | **O Bruxo** | Trickster / Mix-up | Pase No-Look / Joga Bonito | `Assets/Design3D_Turnarounds/Turnaround_BRUXO_BR.png` | `SheetA_BRUXO_BR.png` / `SheetB_BRUXO_BR.png` | `Assets/Sprites2D/ActionFrames/BRUXO_BR/<FRAME>.png` |
| 3 | `CANON_AR` | **El Cañón** | Power Shoto | Bati-Cañonazo / Volea del 98 | `Assets/Design3D_Turnarounds/Turnaround_CANON_AR.png` | `SheetA_CANON_AR.png` / `SheetB_CANON_AR.png` | `Assets/Sprites2D/ActionFrames/CANON_AR/<FRAME>.png` |
| 4 | `PULGA_AR` | **La Pulga** | Pixie / Footsies | Rosca al Ángulo / Coronación Eterna | `Assets/Design3D_Turnarounds/Turnaround_PULGA_AR.png` | `SheetA_PULGA_AR.png` / `SheetB_PULGA_AR.png` | `Assets/Sprites2D/ActionFrames/PULGA_AR/<FRAME>.png` |
| 5 | `PIBE_CO` | **El Pibe** | Setplay Zoner | Pase Filtrado / Cinco a Cero | `Assets/Design3D_Turnarounds/Turnaround_PIBE_CO.png` | `SheetA_PIBE_CO.png` / `SheetB_PIBE_CO.png` | `Assets/Sprites2D/ActionFrames/PIBE_CO/<FRAME>.png` |
| 6 | `LOCO_CO` | **El Loco** | Counter-Acrobat | El Escorpión / Wembley 95 | `Assets/Design3D_Turnarounds/Turnaround_LOCO_CO.png` | `SheetA_LOCO_CO.png` / `SheetB_LOCO_CO.png` | `Assets/Sprites2D/ActionFrames/LOCO_CO/<FRAME>.png` |
| 7 | `PISTOLERO_UY` | **El Pistolero** | Hybrid Grappler | Presión Asfixiante / Garra Charrúa | `Assets/Design3D_Turnarounds/Turnaround_PISTOLERO_UY.png` | `SheetA_PISTOLERO_UY.png` / `SheetB_PISTOLERO_UY.png` | `Assets/Sprites2D/ActionFrames/PISTOLERO_UY/<FRAME>.png` |
| 8 | `MATADOR_UY` | **El Matador** | Long-Range Hybrid | Efecto Jabulani / Cabezazo en Plancha | `Assets/Design3D_Turnarounds/Turnaround_MATADOR_UY.png` | `SheetA_MATADOR_UY.png` / `SheetB_MATADOR_UY.png` | `Assets/Sprites2D/ActionFrames/MATADOR_UY/<FRAME>.png` |
| 9 | `BAMBAM_CL` | **Bam-Bam** | Air-Dominance | El Helicóptero / Tijera Chilena | `Assets/Design3D_Turnarounds/Turnaround_BAMBAM_CL.png` | `SheetA_BAMBAM_CL.png` / `SheetB_BAMBAM_CL.png` | `Assets/Sprites2D/ActionFrames/BAMBAM_CL/<FRAME>.png` |
| 10 | `REY_CL` | **El Rey** | Berserker Rekka | Trancazo Real / Tijera Berserker | `Assets/Design3D_Turnarounds/Turnaround_REY_CL.png` | `SheetA_REY_CL.png` / `SheetB_REY_CL.png` | `Assets/Sprites2D/ActionFrames/REY_CL/<FRAME>.png` |
| 11 | `BULLDOG_PY` | **El Bulldog** | Big-Body Grappler / Zoner | Tiro Libre con Barrera / Smash Aéreo | `Assets/Design3D_Turnarounds/Turnaround_BULLDOG_PY.png` | `SheetA_BULLDOG_PY.png` / `SheetB_BULLDOG_PY.png` | `Assets/Sprites2D/ActionFrames/BULLDOG_PY/<FRAME>.png` |
| 12 | `MAESTRO_PE` | **El Maestro** | Technical Footsies | Tiro de Tres Dedos / Chilena Peruana | `Assets/Design3D_Turnarounds/Turnaround_MAESTRO_PE.png` | `SheetA_MAESTRO_PE.png` / `SheetB_MAESTRO_PE.png` | `Assets/Sprites2D/ActionFrames/MAESTRO_PE/<FRAME>.png` |
| 13 | `TREN_EC` | **El Tren Amazónico** | Speedster / Run-Cancel | Expreso por la Banda / Chilena Veloz | `Assets/Design3D_Turnarounds/Turnaround_TREN_EC.png` | `SheetA_TREN_EC.png` / `SheetB_TREN_EC.png` | `Assets/Sprites2D/ActionFrames/TREN_EC/<FRAME>.png` |
| 14 | `HURACAN_VE` | **El Huracán Vinotinto** | Dead-Ball Sniper | Zurda de Oro (Folha Seca) / Volea | `Assets/Design3D_Turnarounds/Turnaround_HURACAN_VE.png` | `SheetA_HURACAN_VE.png` / `SheetB_HURACAN_VE.png` | `Assets/Sprites2D/ActionFrames/HURACAN_VE/<FRAME>.png` |
| 15 | `DIABLO_BO` | **El Diablo Andino** | Stamina Debuffer | Balón Pesado 3,600m / Chilena Andina | `Assets/Design3D_Turnarounds/Turnaround_DIABLO_BO.png` | `SheetA_DIABLO_BO.png` / `SheetB_DIABLO_BO.png` | `Assets/Sprites2D/ActionFrames/DIABLO_BO/<FRAME>.png` |
| 16 | `GENERAL_FR` | **Le Général** | Tactical Stance | Roulette de Marseille / Volea Real | `Assets/Design3D_Turnarounds/Turnaround_GENERAL_FR.png` | `SheetA_GENERAL_FR.png` / `SheetB_GENERAL_FR.png` | `Assets/Sprites2D/ActionFrames/GENERAL_FR/<FRAME>.png` |
| 17 | `VAR_ZERO_BOSS` | **El Juez Supremo (V.A.R. - ZERO)** | Boss Zoner / Time Rewinder | Sentencia Roja / Purga Reglamentaria | `Assets/Design3D_Turnarounds/Turnaround_VAR_ZERO_BOSS.png` | `SheetA_VAR_ZERO_BOSS.png` / `SheetB_VAR_ZERO_BOSS.png` | `Assets/Sprites2D/ActionFrames/VAR_ZERO_BOSS/<FRAME>.png` |

> **Ruta base de hojas maestras:** todas las hojas `SheetA_<CODE>.png` y `SheetB_<CODE>.png` van dentro de `Assets/Sprites2D/ActionFrames/Sheets/`.

---

## 5. Flujo de Generación Determinista y Verificación

1. **Generar / actualizar catálogo de prompts:**
   ```bash
   python Scripts/build_action_frames_plan.py
   ```
   Produce `Assets/Sprites2D/ActionFrames/ActionFrames_PromptCatalog.json` con las **17 entradas**, **34 prompts de lámina** (`sheetA` + `sheetB`), especificaciones corregidas (incluido el ajuste `footba.` → `football boots.` en `FENOMENO_BR`) y rutas exactas de entrada/salida.
2. **Generación en Gemini:**
   - Para cada luchador `fighters[i]`, subir `fighters[i].sheetA.attachment` (`Assets/Design3D_Turnarounds/Turnaround_<CODE>.png`), pegar `fighters[i].sheetA.prompt` y guardar como `Assets/Sprites2D/ActionFrames/Sheets/SheetA_<CODE>.png`.
   - Repetir con `fighters[i].sheetB.attachment` + `fighters[i].sheetB.prompt` y guardar como `Assets/Sprites2D/ActionFrames/Sheets/SheetB_<CODE>.png`.
3. **Recorte y Alpha Matting (`#383B42` → RGBA):**
   - Cada hoja `3×2` se divide en 6 celdas regulares y se procesa con remoción de fondo `#383B42` y normalización de pie/pivote inferior hacia `Assets/Sprites2D/ActionFrames/<CODE>/<FRAME>.png` (total **204** sprites listos para `WebLab/app.js` y manifiesto 2D).
