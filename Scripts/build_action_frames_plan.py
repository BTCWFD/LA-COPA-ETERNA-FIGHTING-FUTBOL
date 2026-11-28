#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_action_frames_plan.py
Generates the deterministic Gemini multi-frame 2D combat sprite-sheet prompt catalog
(`Assets/Sprites2D/ActionFrames/ActionFrames_PromptCatalog.json`) for all 17 CONMEBOL
fighters in `LA COPA ETERNA: SANGRE Y POTRERO`.

Each fighter receives 2 sheets (`SheetA` & `SheetB`) in a 3x2 grid (6 keyframes each,
12 keyframes total per fighter = 204 total combat frames), strictly anchored to
`Assets/Design3D_Turnarounds/Turnaround_<CODE>.png` on seamless studio grey `#383B42`.
"""

from __future__ import annotations

import json
import os
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Assets", "Sprites2D", "ActionFrames")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "ActionFrames_PromptCatalog.json")

BACKGROUND_HEX = "#383B42"
SHEET_A_FRAMES = ["IDLE_GUARD", "RUN_1", "RUN_2", "CROUCH", "PUNCH_LP", "KICK_HP"]
SHEET_B_FRAMES = ["JUMP", "BLOCK_GUARD", "HITSTUN", "SHOT_SK", "CHILENA_SP", "KO"]

# Exact 17 Turnaround visual specifications (with FENOMENO_BR trailing typo fixed:
# "footba." -> "football boots.") paired with ROSTER_DATA combat archetypes & signature moves.
FIGHTERS_DATA: list[dict[str, Any]] = [
    {
        "code": "FENOMENO_BR",
        "displayName": "O Fenômeno",
        "country": "Brasil",
        "era": "1994-2006",
        "archetype": "Rushdown Explosivo",
        "signatureNotation": "236+LP",
        "characterSpec": (
            "Character Specification: Athletic Brazilian striker in his early 20s, 1.83m tall, "
            "powerful broad-shouldered muscular rushdown build, warm golden-brown skin, iconic 2002 "
            "shaved head with a neat triangular crescent hairline patch at the forehead, wearing an "
            "oversized retro 1998/2002 vibrant canary-yellow football jersey with green collar trim "
            "and chest number 9, royal-blue athletic shorts, white folded socks, and silver-and-volt "
            "leather football boots."
        ),
        "shotSkPose": (
            "explosive low-driven cross-shot follow-through (Definicion Cruzada / Corte Bajo) after "
            "a burst pedalada feint, planting left cleat firmly while snapping right boot forward at "
            "shin height with torso lunging aggressively toward +X"
        ),
        "chilenaSpPose": (
            "high-powered airborne inverted overhead bicycle kick (Pentacampeon Eterno), body "
            "horizontal-inverted mid-air, left knee tucked and right striking leg scissoring high "
            "upward toward upper-right +X"
        ),
    },
    {
        "code": "BRUXO_BR",
        "displayName": "O Bruxo",
        "country": "Brasil",
        "era": "2000-2010",
        "archetype": "Trickster / Mix-up",
        "signatureNotation": "41236+MP",
        "characterSpec": (
            "Character Specification: Agile charismatic Brazilian playmaker in his mid 20s, 1.82m tall, "
            "lean sinewy trickster build, warm bronze skin, joyful mischievous grin, long dark-brown "
            "curly shoulder-length hair tied back with an elastic white athletic headband, subtle goatee, "
            "wearing a retro 2000s canary-yellow and emerald-green football jersey number 10 with v-neck "
            "collar, royal-blue shorts, white crew socks, and white-and-gold stitched leather cleats."
        ),
        "shotSkPose": (
            "flamboyant no-look outside-boot whip strike follow-through (Pase No-Look / Elastica de "
            "Cano), head turned slightly while snapping right cleat across body toward +X with "
            "expressive outstretched balancing arms"
        ),
        "chilenaSpPose": (
            "acrobatic samba airborne inverted overhead bicycle kick (Joga Bonito Eterno), body "
            "arched mid-air with curly hair and headband streaming behind and scissor kick snapping "
            "toward upper-right +X"
        ),
    },
    {
        "code": "CANON_AR",
        "displayName": "El Cañón",
        "country": "Argentina",
        "era": "1990-2002",
        "archetype": "Power Shoto",
        "signatureNotation": "236+SK",
        "characterSpec": (
            "Character Specification: Imposing Argentine center-forward in his late 20s, 1.85m tall, "
            "heavy heroic power-striker physique, sun-tanned Mediterranean olive skin, fierce warrior "
            "gaze, strong jawline with light stubble, long flowing golden-chestnut wavy lion-like mane "
            "hair held back by a thin black sports headband, wearing an oversized 1990s sky-blue and "
            "white vertical-striped jacquard jersey number 9 with black fold-over collar, black shorts, "
            "white socks with sky-blue bands, and classic black leather cleats."
        ),
        "shotSkPose": (
            "massive planted cannonball power-shot follow-through (Bati-Canonazo Recto), heavy hip "
            "torque, chest puffed with warrior roar, right boot driving through at waist height toward +X"
        ),
        "chilenaSpPose": (
            "explosive airborne half-volley / inverted scissor strike (Volea de Media Vuelta / Angulo "
            "Eterno del 98), flowing mane whipping back while driving right cleat upward toward +X"
        ),
    },
    {
        "code": "PULGA_AR",
        "displayName": "La Pulga",
        "country": "Argentina",
        "era": "2005-Presente",
        "archetype": "Pixie / Footsies",
        "signatureNotation": "236+MP",
        "characterSpec": (
            "Character Specification: Compact nimble Argentine forward in his late 20s/early 30s, 1.70m "
            "tall, low center-of-gravity agile build, fair-olive complexion, focused calm eyes, neatly "
            "trimmed full reddish-brown beard and mustache, short textured dark-brown faded haircut, "
            "detailed geometric sleeve tattoo on right arm and left calf tattoo, wearing a sky-blue and "
            "white vertical-striped modern-retro football jersey number 10 with gold trim, crisp white "
            "shorts, sky-blue/white socks, and sleek gold-and-white speed cleats."
        ),
        "shotSkPose": (
            "low-center-of-gravity left-footed curling precision strike follow-through (Rosca al Angulo "
            "Imposible / Slalom Imposible), torso leaned sharply left for counterbalance as left gold "
            "cleat whips upward toward +X"
        ),
        "chilenaSpPose": (
            "compact nimble airborne inverted overhead bicycle kick (Coronacion Eterna), tight aerial "
            "rotation with left cleat snapped cleanly upward toward upper-right +X"
        ),
    },
    {
        "code": "PIBE_CO",
        "displayName": "El Pibe",
        "country": "Colombia",
        "era": "1990-2000",
        "archetype": "Setplay Zoner",
        "signatureNotation": "236+SK",
        "characterSpec": (
            "Character Specification: Iconic 1990s Colombian midfield maestro in his early 30s, 1.76m "
            "tall, balanced technical build, warm tan complexion, calm penetrating gaze, signature thick "
            "handlebar-style golden-brown mustache, massive volumetric fluffy bleached-blonde curly afro "
            "hair, braided woven friendship bracelets on left wrist, wearing an oversized 1990s "
            "golden-yellow football jersey number 10 with navy-blue and crimson shoulder stripes, "
            "royal-blue shorts, white socks with crimson trim, and classic black leather cleats."
        ),
        "shotSkPose": (
            "poised upright outside-foot surgical through-pass strike (Pase Filtrado al Vacio), head "
            "held high with commanding vision, braceleted left arm extended for balance while right boot "
            "whips toward +X"
        ),
        "chilenaSpPose": (
            "technical elevated airborne scissor volley (Cinco a Cero Monumental), volumetric blonde "
            "afro framing calm focused face while extending striking cleat upward toward +X"
        ),
    },
    {
        "code": "LOCO_CO",
        "displayName": "El Loco",
        "country": "Colombia",
        "era": "1990-2000",
        "archetype": "Counter-Acrobat",
        "signatureNotation": "214+SK",
        "characterSpec": (
            "Character Specification: Eccentric acrobatic 1990s Colombian goalkeeper, 1.76m tall, "
            "sturdy stocky athletic build, warm medium-tan complexion, intense eyes, prominent thick "
            "dark-brown mustache, voluminous dark curly shoulder-length hair cascading down his neck, "
            "wearing a vivid purple-violet and black 1990s geometric-patterned long-sleeve goalkeeper "
            "jersey number 1 with padded elbows, black shorts, black socks, classic padded leather "
            "goalkeeper gloves, and black retro cleats."
        ),
        "shotSkPose": (
            "signature arched acrobatic Scorpion Kick counter-clearance (El Escorpion), diving forward "
            "mid-air with chest angled down, padded goalkeeper gloves braced forward and both heels "
            "whipping overhead backward-to-forward to strike toward +X"
        ),
        "chilenaSpPose": (
            "daring flying goalkeeper overhead bicycle kick clearance (Wembley Eterno 95), fully "
            "inverted mid-air with curly hair cascading and studded cleats snapping upward toward +X"
        ),
    },
    {
        "code": "PISTOLERO_UY",
        "displayName": "El Pistolero",
        "country": "Uruguay",
        "era": "2007-Presente",
        "archetype": "Hybrid Grappler",
        "signatureNotation": "41236+LP",
        "characterSpec": (
            "Character Specification: Fierce relentless Uruguayan striker in his late 20s, 1.82m tall, "
            "thick chest-heavy muscular grappler build, fair-tan South American skin, determined "
            "competitive scowl, rugged cheekbones and jawline with 3-day stubble, short cropped "
            "dark-brown hair, black protective athletic wrist tape wrapped around both wrists/forearms, "
            "wearing a celeste sky-blue football jersey number 9 with white-and-gold collar detail, "
            "black shorts, black socks, and crimson-and-black high-traction cleats."
        ),
        "shotSkPose": (
            "ferocious forward-lunging grappler-strike / knee-drive charge (Presion Asfixiante), "
            "wrist-taped arms reaching forward to clinch while driving heavy front knee and cleat "
            "explosively toward +X"
        ),
        "chilenaSpPose": (
            "fierce full-power airborne inverted overhead scissor kick (Garra Charrua Inmortal), "
            "muscular torso coiled mid-air with crimson-and-black cleat snapping toward upper-right +X"
        ),
    },
    {
        "code": "MATADOR_UY",
        "displayName": "El Matador",
        "country": "Uruguay",
        "era": "2000-2018",
        "archetype": "Long-Range Hybrid",
        "signatureNotation": "236+SK",
        "characterSpec": (
            "Character Specification: Sharp stoic Uruguayan striker in his late 20s, 1.80m tall, lean "
            "sculpted long-range endurance athlete build, pale-olive skin, chiseled high cheekbones and "
            "piercing dark eyes, long sleek jet-black wavy hair past the shoulders secured with a thin "
            "dark headband, wearing a deep celeste sky-blue athletic jersey number 21 with subtle golden "
            "collar trim, black shorts, black socks, and crimson-trimmed speed cleats."
        ),
        "shotSkPose": (
            "long-range ambidextrous knuckle-shot follow-through (Efecto Jabulani), wide athletic "
            "stride, lean torso twisted sharply and sleek jet-black hair streaming back as striking "
            "boot snaps toward +X"
        ),
        "chilenaSpPose": (
            "diving horizontal air-pike overhead scissor / flying header-kick hybrid (Cabezazo en "
            "Plancha / Balon de Oro Sudafrica), soaring toward +X with sculpted athletic extension"
        ),
    },
    {
        "code": "BAMBAM_CL",
        "displayName": "Bam-Bam",
        "country": "Chile",
        "era": "1990-2002",
        "archetype": "Air-Dominance",
        "signatureNotation": "j.236+MP",
        "characterSpec": (
            "Character Specification: Heroic 1990s Chilean aerial striker, 1.78m tall, lean powerful "
            "jumping athlete with explosive calves, tanned Andean complexion, determined noble eyes, "
            "strong aquiline nose, crisp short 1990s dark-brown feathered hair, athletic knee brace "
            "strap below left knee, wearing a crimson-red retro 1998 jacquard football jersey number 9 "
            "with clean white shoulder yoke and navy-blue collar, royal-blue shorts, white socks, and "
            "black-and-red classic leather cleats."
        ),
        "shotSkPose": (
            "explosive rising anti-air knee-drive and instep launch (El Helicoptero Anti-Aereo), "
            "propelling upward from a coiled plant with left knee-brace strap prominent and right leg "
            "snapping toward +X"
        ),
        "chilenaSpPose": (
            "signature high-altitude Tijera Chilena inverted overhead bicycle kick, suspended at peak "
            "aerial hang-time with explosive calves extended upward toward +X"
        ),
    },
    {
        "code": "REY_CL",
        "displayName": "El Rey",
        "country": "Chile",
        "era": "2007-Presente",
        "archetype": "Berserker Rekka",
        "signatureNotation": "236+LP",
        "characterSpec": (
            "Character Specification: Aggressive box-to-box Chilean midfielder in his early 30s, 1.80m "
            "tall, sturdy muscular brawler build, olive complexion, fierce scowl, sculpted angular chin "
            "beard, iconic sharp central dark mohawk hair crest with clean shaved sides, realistic "
            "athletic sleeve tattoos covering both arms and neck, wearing a vivid crimson-red football "
            "jersey number 8 with royal-blue sleeves, navy shorts, crimson socks, and metallic "
            "chrome-and-red cleats."
        ),
        "shotSkPose": (
            "ferocious forward-charging box-to-box rekka power kick / low slide-drive (Trancazo Real / "
            "Barrida Real), tattooed shoulders pitched aggressively forward with chrome-and-red cleat "
            "slashing toward +X"
        ),
        "chilenaSpPose": (
            "brutal high-torque airborne inverted scissor kick overhead strike, mohawk crest sharp and "
            "tattooed arms braced mid-air as boot snaps toward +X"
        ),
    },
    {
        "code": "BULLDOG_PY",
        "displayName": "El Bulldog",
        "country": "Paraguay",
        "era": "1990-2003",
        "archetype": "Big-Body Grappler / Zoner",
        "signatureNotation": "236+SK",
        "characterSpec": (
            "Character Specification: Towering intimidating 1990s Paraguayan goalkeeper and captain, "
            "1.92m tall, massive heavyweight broad-shouldered torso, rugged weathered olive-tan skin, "
            "stern fearless glare, thick bull neck, close-cropped salt-and-pepper crew cut hair, wearing "
            "a dark charcoal-slate and emerald-green retro 1990s long-sleeve goalkeeper jersey number 1 "
            "featuring an embroidered stylized roaring bulldog chest patch, thick forearm bandages, "
            "heavy leather goalkeeper gloves, black shorts, and black heavy-duty cleats."
        ),
        "shotSkPose": (
            "heavyweight set-piece free-kick cannon blast follow-through (Tiro Libre con Barrera), "
            "massive shoulders squared, heavy goalkeeper gloves flared wide for torque, driving "
            "heavy-duty cleat forward toward +X"
        ),
        "chilenaSpPose": (
            "towering powerhouse mid-air overhead scissor smash, massive heavyweight frame suspended "
            "horizontally with bandaged forearms braced and heavy boot snapping upward toward +X"
        ),
    },
    {
        "code": "MAESTRO_PE",
        "displayName": "El Maestro",
        "country": "Perú",
        "era": "Clásico-Moderno",
        "archetype": "Technical Footsies",
        "signatureNotation": "236+SK~8",
        "characterSpec": (
            "Character Specification: Elegant technical Peruvian midfielder, 1.77m tall, balanced "
            "slender playmaker physique, warm Andean-mestizo complexion, composed intelligent gaze, "
            "neat short dark wavy hair, light mustache/stubble, wearing the iconic crisp white "
            "Peru-inspired football jersey number 10 with a bold diagonal crimson-red chest sash "
            "(la blanquirroja) and gold collar trim, white shorts with red trim, white socks with red "
            "hoop bands, and classic black-and-white leather cleats."
        ),
        "shotSkPose": (
            "silky three-toe outside-boot trivela whip strike follow-through (Tiro de Tres Dedos), "
            "graceful hip rotation and poised balance in crisp white-and-crimson sash jersey facing +X"
        ),
        "chilenaSpPose": (
            "classical Peruvian Chilena overhead bicycle kick executed mid-air with textbook form, "
            "diagonal crimson sash clear on torso and cleat snapping cleanly toward upper-right +X"
        ),
    },
    {
        "code": "TREN_EC",
        "displayName": "El Tren Amazónico",
        "country": "Ecuador",
        "era": "2002-2020",
        "archetype": "Speedster / Run-Cancel",
        "signatureNotation": "236+GB",
        "characterSpec": (
            "Character Specification: Explosive powerhouse Ecuadorian right-winger, 1.79m tall, "
            "ultra-ripped sprinter build with pronounced thigh and calf vascularity, deep Afro-Ecuadorian "
            "dark skin, focused relentless sprint stare, tightly cropped fade haircut, white captain "
            "armband on left bicep, wearing a bright golden-yellow Ecuador-inspired football jersey "
            "number 16 with navy-blue and crimson shoulder panels, navy-blue shorts, navy socks, and "
            "neon-volt sprint cleats."
        ),
        "shotSkPose": (
            "blistering full-throttle wing-sprint rasante drive follow-through (Expreso por la Banda / "
            "Centro Rasante Buscapies), ultra-lean sprinter lunge toward +X with neon-volt cleats and "
            "white captain armband clear"
        ),
        "chilenaSpPose": (
            "high-velocity airborne sprint-into-scissor bicycle kick streaking upward toward +X with "
            "explosive sprinter calves and neon-volt cleats fully extended"
        ),
    },
    {
        "code": "HURACAN_VE",
        "displayName": "El Huracán Vinotinto",
        "country": "Venezuela",
        "era": "2000-Presente",
        "archetype": "Dead-Ball Sniper",
        "signatureNotation": "236+SK",
        "characterSpec": (
            "Character Specification: Technical Venezuelan free-kick specialist, 1.80m tall, athletic "
            "lean sniper build, warm tan complexion, calm laser-focused eyes, sleek dark-brown "
            "swept-back medium haircut, subtle chin beard, wearing a rich deep burgundy-wine (vinotinto) "
            "football jersey number 18 with champagne-gold collar and sleeve cuffs, burgundy shorts, "
            "burgundy socks, and gold-detailed precision football cleats."
        ),
        "shotSkPose": (
            "pinpoint left-footed Folha Seca dead-ball sniper strike follow-through (Zurda de Oro), "
            "torso angled cleanly back, right arm extended for surgical precision, gold-detailed left "
            "cleat whipping upward toward +X"
        ),
        "chilenaSpPose": (
            "sharp acrobatic vinotinto airborne inverted overhead bicycle volley snapped cleanly toward "
            "upper-right +X"
        ),
    },
    {
        "code": "DIABLO_BO",
        "displayName": "El Diablo Andino",
        "country": "Bolivia",
        "era": "1990-2000",
        "archetype": "Stamina Debuffer",
        "signatureNotation": "214+SK",
        "characterSpec": (
            "Character Specification: Legendary 1990s Bolivian creative number 10 playmaker, 1.76m "
            "tall, compact stocky high-altitude build, warm indigenous-Andean bronze complexion, intense "
            "charismatic eyes, iconic thick dark mustache and windswept 1990s wavy dark mane hair "
            "reaching the collar, wearing a deep emerald-green 1994 Bolivia-inspired jacquard football "
            "jersey number 10 with red-yellow-green tricolor collar trim, white shorts, emerald-green "
            "socks, and classic black leather boots."
        ),
        "shotSkPose": (
            "punchy high-altitude power whip strike follow-through (Balon Pesado 3,600m / Remate "
            "Soroche), compact coiled stance snapping left leather boot forward toward +X with "
            "windswept dark mane flaring"
        ),
        "chilenaSpPose": (
            "fierce compact airborne inverted overhead bicycle kick, emerald-green tricolor collar "
            "jersey twisted mid-air and black leather boot driving upward toward +X"
        ),
    },
    {
        "code": "GENERAL_FR",
        "displayName": "Le Général",
        "country": "Francia (Invitado)",
        "era": "1996-2006",
        "archetype": "Tactical Stance",
        "signatureNotation": "236+MP",
        "characterSpec": (
            "Character Specification: Aristocratic composed French midfield general in his early 30s, "
            "1.85m tall, tall upright regal build, fair Mediterranean-Kabyle complexion, calm calculating "
            "gaze, cleanly shaved/receding crown head, crisp light stubble, wearing a classic 1998 deep "
            "royal-blue France-inspired football jersey number 10 with horizontal white-and-crimson "
            "chest band and crisp white polo collar, crisp white shorts, crimson socks, and classic "
            "white-gold-black leather cleats."
        ),
        "shotSkPose": (
            "aristocratic Roulette de Marseille pivot-and-strike stance (Roulette de Marseille / Coup "
            "de Tete Final), regal upright torso twisting with surgical balance and white-gold-black "
            "cleat sweeping toward +X"
        ),
        "chilenaSpPose": (
            "iconic commanding mid-air volley / inverted overhead scissor strike executed with surgical "
            "elegance and regal extension toward upper-right +X"
        ),
    },
    {
        "code": "VAR_ZERO_BOSS",
        "displayName": "El Juez Supremo (V.A.R. - ZERO)",
        "country": "BOSS FINAL",
        "era": "Atemporal",
        "archetype": "Boss Zoner / Time Rewinder",
        "signatureNotation": "22+GB",
        "characterSpec": (
            "Character Specification: Towering 2.15m tall cybernetic biomechanical supreme referee boss "
            "blending Renaissance bronze filigree, dark polished obsidian armor plates, and cold cyan "
            "holographic V.A.R. optics, sculpted metallic-bronze mask with glowing cyan cybernetic visor "
            "slit and sharp obsidian mandible plates, dark obsidian-and-gold biomechanical referee "
            "trench-tunic over dark armor greaves, cyan digital stopwatch chest core, crimson red-card "
            "gauntlets, armored bronze-studded cleats, and two floating brass-and-cyan rotating "
            "Renaissance astrolabe drones near shoulders."
        ),
        "shotSkPose": (
            "imperious cybernetic referee judgment kick and crimson red-card gauntlet thrust (Sentencia "
            "de Tarjeta Roja / Laser de Linea de Offside), obsidian trench-tunic flaring while driving "
            "armored bronze-studded cleat forward toward +X and astrolabe drones hovering behind shoulders"
        ),
        "chilenaSpPose": (
            "levitating biomechanical inverted judgment scissor-kick (Purga Reglamentaria Total), "
            "hovering horizontally mid-air with obsidian-and-gold trench-tunic splayed, drones aligned, "
            "and armored cleat snapping upward toward +X"
        ),
    },
]


def build_sheet_a_prompt(f: dict[str, Any]) -> str:
    """Build deterministic Gemini prompt for Sheet A (Locomotion & Core Combat, 3x2 grid)."""
    return (
        f"Using the attached turnaround reference image ({f['code']} — {f['displayName']}), generate "
        f"a clean 2D fighting-game production sprite sheet on a completely flat seamless studio grey "
        f"background ({BACKGROUND_HEX}).\n\n"
        f"IDENTITY & KIT LOCK (100% EXACT MATCH TO REFERENCE):\n"
        f"{f['characterSpec']}\n"
        f"Preserve the exact facial likeness, hairstyle, facial hair, skin tone, body proportions, "
        f"jersey pattern/number, shorts, socks, wristbands/gloves, and cleats shown in the attached "
        f"Turnaround_{f['code']}.png across all 6 frames.\n\n"
        f"STRICT LAYOUT & CAMERA RULES:\n"
        f"- Exact 3 columns x 2 rows grid (6 equal-sized cells, landscape 16:9 composition).\n"
        f"- ZERO grid lines, ZERO borders, ZERO text labels, ZERO cell numbers, ZERO watermarks.\n"
        f"- ZERO floor turf, ZERO stadium background, ZERO drop shadows, ZERO soccer balls, ZERO VFX sparks.\n"
        f"- ZERO overlap between cells: each full head-to-cleats figure must fit comfortably inside "
        f"the inner 80% of its cell with uniform scale across all 6 poses.\n"
        f"- Pure 2D fighting-game side-profile orthographic camera facing strictly RIGHT (+X) in every cell.\n"
        f"- Consistent neutral studio lighting matching the turnaround sheet.\n\n"
        f"EXACT 6 POSES (LEFT-TO-RIGHT, TOP-TO-BOTTOM):\n"
        f"1. [Row 1, Col 1 — IDLE_GUARD]: Side-profile 3/4 combat readiness stance facing right (+X), "
        f"bent knees, weight balanced, fists raised in tight fighting guard.\n"
        f"2. [Row 1, Col 2 — RUN_1]: Explosive mid-sprint stride A facing right (+X), near knee driven "
        f"high forward, back leg pushing off behind, torso leaned ~26 degrees forward, arms pumping in opposition.\n"
        f"3. [Row 1, Col 3 — RUN_2]: Opposite mid-sprint stride B facing right (+X), rear leg driving "
        f"forward, front leg extending back, chest twisted rhythmically with opposite arm swing.\n"
        f"4. [Row 2, Col 1 — CROUCH]: Deep fighting-game low crouch squat facing right (+X), knees bent "
        f"sharply, chest hunched forward ~30 degrees, chin tucked behind tight protective guard hands.\n"
        f"5. [Row 2, Col 2 — PUNCH_LP]: Fast straight jab facing right (+X), hips and torso twisted into "
        f"the strike, lead arm and fist fully extended horizontally forward, rear fist protecting chin.\n"
        f"6. [Row 2, Col 3 — KICK_HP]: High martial-arts front/roundhouse kick facing right (+X), pivot "
        f"cleat planted firmly, kicking leg and cleat snapped high forward at chest/head height, torso "
        f"leaning back in athletic counterbalance."
    )


def build_sheet_b_prompt(f: dict[str, Any]) -> str:
    """Build deterministic Gemini prompt for Sheet B (Aerial, Defense & Signature Specials, 3x2 grid)."""
    return (
        f"Using the attached turnaround reference image ({f['code']} — {f['displayName']}), generate "
        f"a clean 2D fighting-game production sprite sheet on a completely flat seamless studio grey "
        f"background ({BACKGROUND_HEX}).\n\n"
        f"IDENTITY & KIT LOCK (100% EXACT MATCH TO REFERENCE):\n"
        f"{f['characterSpec']}\n"
        f"Preserve the exact facial likeness, hairstyle, facial hair, skin tone, body proportions, "
        f"jersey pattern/number, shorts, socks, wristbands/gloves, and cleats shown in the attached "
        f"Turnaround_{f['code']}.png across all 6 frames.\n\n"
        f"STRICT LAYOUT & CAMERA RULES:\n"
        f"- Exact 3 columns x 2 rows grid (6 equal-sized cells, landscape 16:9 composition).\n"
        f"- ZERO grid lines, ZERO borders, ZERO text labels, ZERO cell numbers, ZERO watermarks.\n"
        f"- ZERO floor turf, ZERO stadium background, ZERO drop shadows, ZERO soccer balls, ZERO VFX/lasers.\n"
        f"- ZERO overlap between cells: each full head-to-cleats figure must fit comfortably inside "
        f"the inner 80% of its cell with uniform scale across all 6 poses.\n"
        f"- Pure 2D fighting-game side-profile orthographic camera facing strictly RIGHT (+X).\n"
        f"- Consistent neutral studio lighting matching the turnaround sheet.\n\n"
        f"EXACT 6 POSES (LEFT-TO-RIGHT, TOP-TO-BOTTOM):\n"
        f"1. [Row 1, Col 1 — JUMP]: Airborne athletic fighting leap facing right (+X), knees tucked "
        f"upward, body coiled in mid-air, arms balanced and ready for an aerial strike.\n"
        f"2. [Row 1, Col 2 — BLOCK_GUARD]: Tight braced cross-arm/forearm guard absorbing heavy impact "
        f"facing right (+X), knees bent low, cleats anchored firmly against pushback, chin tucked.\n"
        f"3. [Row 1, Col 3 — HITSTUN]: Dramatic whip-back recoil pose upon taking a clean hit from the "
        f"right (+X), torso snapped backward, head tilted back in pain, arms flung open.\n"
        f"4. [Row 2, Col 1 — SHOT_SK]: Signature archetype pose facing right (+X) — {f['shotSkPose']}.\n"
        f"5. [Row 2, Col 2 — CHILENA_SP]: Signature aerial ultimate pose facing right (+X) — {f['chilenaSpPose']}.\n"
        f"6. [Row 2, Col 3 — KO]: Full knockdown stretched horizontally near the bottom of the cell, "
        f"lying flat on back/side facing upward/sideways with head toward the left (-X) and cleats "
        f"resting toward the right (+X), knocked unconscious."
    )


def build_catalog() -> dict[str, Any]:
    """Assemble the complete deterministic 17-fighter prompt catalog."""
    fighters_out: list[dict[str, Any]] = []
    for idx, f in enumerate(FIGHTERS_DATA, start=1):
        code = f["code"]
        turnaround_ref = f"Assets/Design3D_Turnarounds/Turnaround_{code}.png"
        sheet_a_target = f"Assets/Sprites2D/ActionFrames/Sheets/SheetA_{code}.png"
        sheet_b_target = f"Assets/Sprites2D/ActionFrames/Sheets/SheetB_{code}.png"
        frame_targets = {
            frame: f"Assets/Sprites2D/ActionFrames/{code}/{frame}.png"
            for frame in (SHEET_A_FRAMES + SHEET_B_FRAMES)
        }

        fighters_out.append(
            {
                "index": idx,
                "code": code,
                "displayName": f["displayName"],
                "country": f["country"],
                "era": f["era"],
                "archetype": f["archetype"],
                "signatureNotation": f["signatureNotation"],
                "turnaroundRef": turnaround_ref,
                "sheetATarget": sheet_a_target,
                "sheetBTarget": sheet_b_target,
                "frameTargets": frame_targets,
                "characterSpec": f["characterSpec"],
                "signatureFlavor": {
                    "SHOT_SK": f["shotSkPose"],
                    "CHILENA_SP": f["chilenaSpPose"],
                },
                "sheetA": {
                    "sheetName": "Locomotion & Core Combat",
                    "grid": "3x2",
                    "frames": SHEET_A_FRAMES,
                    "aspectRatio": "16:9",
                    "attachment": turnaround_ref,
                    "prompt": build_sheet_a_prompt(f),
                },
                "sheetB": {
                    "sheetName": "Aerial, Defense & Signature Specials",
                    "grid": "3x2",
                    "frames": SHEET_B_FRAMES,
                    "aspectRatio": "16:9",
                    "attachment": turnaround_ref,
                    "prompt": build_sheet_b_prompt(f),
                },
            }
        )

    return {
        "project": "LA COPA ETERNA: SANGRE Y POTRERO",
        "schemaVersion": "1.0.0",
        "backgroundHex": BACKGROUND_HEX,
        "cameraFacing": "+X_RIGHT",
        "gridLayout": "3x2",
        "totalFighters": len(fighters_out),
        "sheetsPerFighter": 2,
        "framesPerSheet": 6,
        "framesPerFighter": 12,
        "totalSheets": len(fighters_out) * 2,
        "totalFrames": len(fighters_out) * 12,
        "sheetAFrames": SHEET_A_FRAMES,
        "sheetBFrames": SHEET_B_FRAMES,
        "fighters": fighters_out,
    }


def main() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    catalog = build_catalog()
    with open(OUTPUT_JSON, "w", encoding="utf-8", newline="\n") as fp:
        json.dump(catalog, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    print(
        f"[build_action_frames_plan] Generated {OUTPUT_JSON} "
        f"({catalog['totalFighters']} fighters, {catalog['totalSheets']} sheets, "
        f"{catalog['totalFrames']} keyframes)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
