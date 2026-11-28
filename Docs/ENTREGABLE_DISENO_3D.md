# Entregable Técnico y Visual para Diseño y Esculpido 3D AAA
**Proyecto:** LA COPA ETERNA: SANGRE Y POTRERO (*SouthAmericaFightersCore*)  
**Motor Destino:** Unreal Engine 5.8.4 (60.0 FPS Determinista + GGPO Rollback + Chaos Cloth)  
**Pipeline 3D Activo:** Blender 5.2.1 LTS → `.glb` (WebGL2) & `.fbx` (UE 5.8)

---

## 1. Referencias Visuales *Turnaround* Fotorrealistas (Generadas en Gemini — 17/17 Completas)
Todas las láminas generadas en la sesión autenticada de Gemini (`https://gemini.google.com/app/85e2064825947d13`) siguen el estándar de producción **A-Pose (brazos a 35°, Frente / Perfil Lateral / Espalda + Close-up Facial 3/4)** sobre fondo gris neutro `#383B42`:

| Código Personaje | Nombre | Altura / Complexión | Estado de Hoja Turnaround | Archivo / Ubicación |
|---|---|---|---|---|
| `FENOMENO_BR` | **O Fenômeno** (Brasil) | `1.83 m` / Bulk `1.06x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_FENOMENO_BR.png` |
| `BRUXO_BR` | **O Bruxo** (Brasil) | `1.82 m` / Bulk `0.98x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_BRUXO_BR.png` |
| `CANON_AR` | **El Cañón** (Argentina) | `1.85 m` / Bulk `1.10x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_CANON_AR.png` |
| `PULGA_AR` | **La Pulga** (Argentina) | `1.70 m` / Bulk `0.92x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_PULGA_AR.png` |
| `PIBE_CO` | **El Pibe** (Colombia) | `1.76 m` / Bulk `1.00x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_PIBE_CO.png` |
| `LOCO_CO` | **El Loco** (Colombia) | `1.76 m` / Bulk `1.04x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_LOCO_CO.png` |
| `PISTOLERO_UY` | **El Pistolero** (Uruguay) | `1.82 m` / Bulk `1.08x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_PISTOLERO_UY.png` |
| `MATADOR_UY` | **El Matador** (Uruguay) | `1.80 m` / Bulk `1.02x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_MATADOR_UY.png` |
| `BAMBAM_CL` | **Bam-Bam** (Chile) | `1.78 m` / Bulk `1.03x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_BAMBAM_CL.png` |
| `REY_CL` | **El Rey** (Chile) | `1.80 m` / Bulk `1.07x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_REY_CL.png` |
| `BULLDOG_PY` | **El Bulldog** (Paraguay) | `1.92 m` / Bulk `1.24x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_BULLDOG_PY.png` |
| `MAESTRO_PE` | **El Maestro** (Perú) | `1.77 m` / Bulk `0.96x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_MAESTRO_PE.png` |
| `TREN_EC` | **El Tren Amazónico** (Ecuador) | `1.79 m` / Bulk `1.08x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_TREN_EC.png` |
| `HURACAN_VE` | **El Huracán Vinotinto** (Venezuela) | `1.80 m` / Bulk `1.01x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_HURACAN_VE.png` |
| `DIABLO_BO` | **El Diablo Andino** (Bolivia) | `1.76 m` / Bulk `0.99x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_DIABLO_BO.png` |
| `GENERAL_FR` | **Le Général** (Francia) | `1.85 m` / Bulk `1.04x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_GENERAL_FR.png` |
| `VAR_ZERO_BOSS` | **El Juez Supremo (V.A.R.-ZERO)** | `2.15 m` / Bulk `1.28x` | ✅ Generada y guardada | `Assets/Design3D_Turnarounds/Turnaround_VAR_ZERO_BOSS.png` |

---

## 2. Mallas Base, Escultura High-Poly y Presupuesto Geométrico UE 5.8
El diseñador 3D debe trabajar **sobre la jerarquía y topología ya configuradas** en el repositorio para garantizar compatibilidad directa con el motor de combate Q32.32 y los shaders HLSL:

- **Escena Maestra Blender 5.2.1 LTS:** `Assets/BlenderProduction/Fighters/Master_17Fighters_Showcase.blend`
- **FBX listos para Unreal Engine 5.8 (40 huesos + 4 Morph Targets + 16 animaciones @ 60 FPS):** `Assets/BlenderProduction/Fighters/SK_*.fbx`
- **glTF 2.0 Binarios para WebGL2 / Interchange (38 huesos + 16 clips @ 60 FPS):** `Assets/Models3D/Fighters/SK_*.glb`
- **Bakes Cycles de Referencia (Normal & AO Tangente):** `Assets/TexturesPBR/HighPolyBakes/T_SK_*_Sculpt_Normal.png` y `T_SK_*_Sculpt_AO.png`
- **51 Mapas PBR 1024×1024 por Luchador (Skin, Kit y Hair fidelidad Turnaround):** `Assets/TexturesPBR/Fighters/T_<ID>_{Skin,Kit,Hair}_Albedo.png`

### Presupuesto por LOD (Manifiesto `Models3D_TechnicalManifest.json`)
| Nivel LOD | Presupuesto Triángulos | Morph Targets | Chaos Cloth | Uso |
|---|---|---|---|---|
| **LOD0** | `65,000` (máx. proyecto) *(malla anatómica esculpida actual: `14,480–17,628` tris desde HP `80,304–99,120` tris)* | Hasta `32` (`4` faciales/combate base ya creados) | ✅ ON (60 Hz) | Gameplay cercano, Intros y Supers |
| **LOD1** | `32,000` | Hasta `16` | ✅ ON (60 Hz) | Distancia media |
| **LOD2** | `16,000` | `0` | ❌ OFF | Cámaras amplias / Zonas abiertas |
| **LOD3** | `8,000` | `0` | ❌ OFF | Fallback hardware ligero |

---

## 3. Estándar Obligatorio de Esqueleto, Materiales y Chaos Cloth
1. **Esqueleto Exacto (38 huesos glTF / 40 con helpers UE5 Chaos Cloth):**
   - Mantener sin renombrar `root` → `pelvis` → `pelvis_visual_offset` *(hueso crítico desacoplado para Hitstop Shake y rotaciones acrobáticas de chilena sin mover la cápsula lógica)*.
   - Cadena de torso/brazos/piernas con twist bones (`lowerarm_twist_01_l/r`, `calf_twist_01_l/r`) y escalado smear (`calf_r` / `foot_r` hasta `1.25x–1.30x`).
   - Huesos secundarios dinámicos: `hair_chain_01..06` (cabello largo / melena afro / drones astrolabio de V.A.R.-ZERO) y `kit_hem_01..04`.
   - ⚠️ **No activar Nanite** sobre `USkeletalMesh` de luchadores (`bEnableNanite = False`, `SkinCacheUsage = Enabled`, `LightingChannel = 1`).
2. **3 Slots de Material Maestro:**
   - **Slot 0:** `M_FighterSkin_SSS` (poros de piel, Subsurface Scattering, mapa base + `T_Skin_MicroPores_Normal.png` / Normal High-Poly).
   - **Slot 1:** `M_FighterKit_Retro90s_Cloth` (camiseta noventera con `T_Kit_<País>_Albedo.png`, `T_FighterKit_ORM.png`, `T_Retro90s_Jacquard_Normal.png`).
   - **Slot 2:** `M_FighterHairCards_And_Eyes` (ojos, tarjetas capilares anisotrópicas / visor holográfico).
3. **Peso Vertex `ChaosCloth_Jersey_Weight` (y canal `COLOR_0.R`):**
   - `0.0` (*Pinned*): Cuello, hombros y escudo (`0.5 cm` max distance).
   - Gradiente suave en torso holgado hasta `1.0` (*Free Hem*) en el faldón inferior y bordes de mangas (`12.0 cm` max distance, Drag `0.08`, Lift `0.04`).
4. **4 Morph Targets (`Shape Keys`) mínimos:** `Smile_Victory`, `Battle_Roar`, `Pain_Hitstun`, `Effort_Sprint`.
5. **16 Animaciones @ 60.0 FPS exactos (`dt = 1/60s`):**
   - 5 *Stepped FGC*: `Anim_Idle`, `Anim_5LP_Jab4f`, `Anim_236SK_Shot`, `Anim_623HP_BicycleKick`, `Anim_214SK_Scorpion`.
   - 11 *Full-Body 60 FPS Mocap*: `Idle_Breath`, `Dash_Forward`, `Kick_High`, `Special_Chilena`, `Victory_Pose`, `Mocap_Walk_Forward`, `Mocap_Backdash_Dodge`, `Mocap_Block_Guard`, `Mocap_Hitstun_Knockback`, `Mocap_Super_Potrero`, `Mocap_KO_Knockdown`.

---

## 4. Portal Interactivo Visual del Entregable
Abre [design-3d-brief.html](../WebLab/design-3d-brief.html) (en vivo en `http://localhost:8080/WebLab/design-3d-brief.html`) para revisar las hojas *Turnaround*, copiar las especificaciones del roster completo de 17 personajes y descargar cualquier binario `.glb` / `.fbx` de referencia.
