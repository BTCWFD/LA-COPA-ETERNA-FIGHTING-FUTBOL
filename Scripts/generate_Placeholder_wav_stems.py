#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_Placeholder_wav_stems.py
Generador Procedural de Efectos de Combate, Coro "¡OOOO-LÉ!", Haptics DualSense y los 10 Stems Nacionales
CONMEBOL cuantizados al BPM exacto de DT_StagesCONMEBOL.json (48kHz 16-bit PCM Mono WAV).
Usa exclusivamente la librería estándar de Python (wave, math, struct, random, os).
"""

import os
import wave
import math
import struct
import random

SAMPLE_RATE = 48000
MAX_AMP = 30000  # Techo seguro (~ -0.8 dBFS) compatible con Wwise Peak Limiter (-1.0 dBFS)


def write_wav_mono(filepath: str, samples: list[float]) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(SAMPLE_RATE)
        packed = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            packed.extend(struct.pack("<h", int(clamped * MAX_AMP)))
        wf.writeframes(packed)


def generate_hit_light_jab() -> list[float]:
    """Impacto corto y seco de botín/puño (140 ms): punch en 160Hz->55Hz + transiente de cuero."""
    duration = 0.14
    num_samples = int(SAMPLE_RATE * duration)
    rng = random.Random(101)
    out = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 28.0)
        freq = 55.0 + 115.0 * math.exp(-t * 45.0)
        body = math.sin(2.0 * math.pi * freq * t)
        snap = (rng.uniform(-1.0, 1.0)) * math.exp(-t * 95.0)
        out.append((0.75 * body + 0.45 * snap) * env)
    return out


def generate_hit_heavy_counter() -> list[float]:
    """Counter-Hit pesado / Trancazo (360 ms): sub-bass 95Hz->38Hz + armónicos de impacto + crujido."""
    duration = 0.36
    num_samples = int(SAMPLE_RATE * duration)
    rng = random.Random(202)
    out = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 10.5)
        sub_freq = 38.0 + 90.0 * math.exp(-t * 25.0)
        sub = math.sin(2.0 * math.pi * sub_freq * t)
        mid = math.sin(2.0 * math.pi * (sub_freq * 2.4) * t) * math.exp(-t * 18.0)
        crack = rng.uniform(-1.0, 1.0) * math.exp(-t * 50.0)
        val = math.tanh(1.6 * (0.75 * sub + 0.35 * mid + 0.40 * crack)) * env
        out.append(val)
    return out


def generate_block_shield_plus() -> list[float]:
    """Guardia sólida / Blockstun (190 ms): resonancia grave amortiguada + doble transiente."""
    duration = 0.19
    num_samples = int(SAMPLE_RATE * duration)
    out = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 20.0)
        thud = math.sin(2.0 * math.pi * 110.0 * t) + 0.5 * math.sin(2.0 * math.pi * 245.0 * t)
        shimmer = math.sin(2.0 * math.pi * 680.0 * t) * math.exp(-t * 40.0)
        out.append((0.6 * thud + 0.3 * shimmer) * env)
    return out


def generate_gambeta_whoosh_parry() -> list[float]:
    """Esquiva / Parry de Gambeta (260 ms): barrido de aire filtrado + destello armónico ascendente."""
    duration = 0.26
    num_samples = int(SAMPLE_RATE * duration)
    rng = random.Random(303)
    out = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        window = math.sin(math.pi * (t / duration))
        sweep_freq = 220.0 + 980.0 * (t / duration) ** 1.5
        phase += 2.0 * math.pi * sweep_freq / SAMPLE_RATE
        chime = math.sin(phase) + 0.4 * math.sin(phase * 1.5)
        air = rng.uniform(-0.35, 0.35) * window
        out.append((0.65 * chime * window) + air)
    return out


def generate_referee_whistle_start() -> list[float]:
    """Silbato arbitral clásico con trino de bolilla (550 ms): 2860Hz + 3140Hz modulado a 42Hz."""
    duration = 0.55
    num_samples = int(SAMPLE_RATE * duration)
    rng = random.Random(404)
    out = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        attack = min(1.0, t / 0.015)
        release = min(1.0, max(0.0, (duration - t) / 0.08))
        env = attack * release
        pea_trill = 0.65 + 0.35 * math.sin(2.0 * math.pi * 42.0 * t)
        tone = 0.6 * math.sin(2.0 * math.pi * 2860.0 * t) + 0.4 * math.sin(2.0 * math.pi * 3140.0 * t)
        breath = rng.uniform(-0.12, 0.12)
        out.append((tone * pea_trill + breath) * env * 0.85)
    return out


def generate_crossbar_metallic_clank() -> list[float]:
    """Balonazo en el travesaño metálico (650 ms): parciales inarmónicos de tubo de acero."""
    duration = 0.65
    num_samples = int(SAMPLE_RATE * duration)
    modes = [
        (415.0, 1.0, 5.5),
        (892.0, 0.75, 7.5),
        (1480.0, 0.55, 10.0),
        (2310.0, 0.40, 14.0),
        (3490.0, 0.25, 22.0),
    ]
    out = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        val = 0.0
        for freq, amp, decay in modes:
            val += amp * math.sin(2.0 * math.pi * freq * t) * math.exp(-t * decay)
        out.append(math.tanh(val * 0.8))
    return out


def generate_var_glitch_rewind() -> list[float]:
    """Efecto de rebobinado temporal V.A.R. - ZERO (600 ms): barrido inverso cuantizado."""
    duration = 0.60
    num_samples = int(SAMPLE_RATE * duration)
    out = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        step_t = math.floor(t * 32.0) / 32.0
        freq = 1400.0 - 1150.0 * (step_t / duration) + 180.0 * math.sin(2.0 * math.pi * 18.0 * t)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        raw = math.sin(phase) + 0.5 * (1.0 if math.sin(phase * 2.0) >= 0 else -1.0)
        env = math.sin(math.pi * (t / duration))
        out.append(raw * 0.55 * env)
    return out


def generate_crowd_ole_chant() -> list[float]:
    """ Rugido coral de tribuna "¡OOOO-LÉ!" (820 ms) con síntesis de formantes vocales ('O' -> 'E') + ambiente de estadio."""
    duration = 0.82
    num_samples = int(SAMPLE_RATE * duration)
    rng = random.Random(505)
    # Voces desafinadas ligeramente para efecto coral masivo de popular sudamericana
    choir_detunes = [0.985, 0.994, 1.0, 1.007, 1.016, 0.5, 1.5]
    phases = [0.0] * len(choir_detunes)
    out = []

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Primera sílaba "OOOO..." (0.0 -> 0.46s) subiendo a segunda sílaba "...LÉ!" (0.46 -> 0.82s)
        if t < 0.46:
            base_f0 = 196.0 + 18.0 * (t / 0.46)  # Sol3 -> Sol#3
            f1, f2 = 460.0, 840.0  # Formantes vocal 'O'
            syll_env = math.sin(math.pi * (t / 0.48)) ** 0.65
        else:
            u = (t - 0.46) / (duration - 0.46)
            base_f0 = 246.94 * (1.0 + 0.015 * math.sin(2.0 * math.pi * 5.5 * t))  # Si3 ("¡LÉ!")
            f1, f2 = 530.0, 1840.0  # Formantes vocal 'E'
            attack = min(1.0, u / 0.06)
            decay = math.exp(-u * 3.2)
            syll_env = attack * decay * 1.15

        vocal_sum = 0.0
        for idx, det in enumerate(choir_detunes):
            f_voice = base_f0 * det
            phases[idx] += 2.0 * math.pi * f_voice / SAMPLE_RATE
            p = phases[idx]
            h1 = math.sin(p)
            h_f1 = 0.55 * math.sin(2.0 * math.pi * f1 * t + 0.3 * math.sin(p))
            h_f2 = 0.30 * math.sin(2.0 * math.pi * f2 * t + 0.2 * math.sin(p))
            vocal_sum += (0.50 * h1 + h_f1 + h_f2) / len(choir_detunes)

        crowd_roar = rng.uniform(-0.28, 0.28) * syll_env
        out.append(math.tanh((vocal_sum * 1.35 + crowd_roar) * syll_env * 0.85))
    return out


def generate_percussion_loop(bpm: float, bars: int, style: str) -> list[float]:
    """Genera un loop percusivo de hinchada sudamericana cuantizado exactamente al BPM indicado."""
    beats_per_bar = 4
    total_beats = bars * beats_per_bar
    sec_per_beat = 60.0 / bpm
    duration = total_beats * sec_per_beat
    num_samples = int(round(SAMPLE_RATE * duration))
    out = [0.0] * num_samples
    # Semilla determinista independiente de PYTHONHASHSEED
    seed = sum((idx + 1) * ord(ch) for idx, ch in enumerate(style))
    rng = random.Random(seed)

    def add_drum_hit(start_sec: float, f_start: float, f_end: float, decay: float, gain: float, noise_mix: float = 0.15):
        start_idx = int(start_sec * SAMPLE_RATE)
        hit_len = int(0.28 * SAMPLE_RATE)
        for k in range(hit_len):
            idx = (start_idx + k) % num_samples
            t = k / SAMPLE_RATE
            env = math.exp(-t * decay)
            f = f_end + (f_start - f_end) * math.exp(-t * 35.0)
            tone = math.sin(2.0 * math.pi * f * t)
            n = rng.uniform(-1.0, 1.0) * math.exp(-t * (decay * 2.2))
            out[idx] += (tone * (1.0 - noise_mix) + n * noise_mix) * env * gain

    for beat in range(total_beats):
        t_beat = beat * sec_per_beat
        sub_step = sec_per_beat / 4.0  # semicorcheas (16th notes)

        if style == "batucada":
            # Brasil (115 BPM): Surdo de primera y segunda + repinique sincopado
            f_surdo = 62.0 if (beat % 2 == 0) else 78.0
            add_drum_hit(t_beat, 120.0, f_surdo, 11.0, 0.80, 0.08)
            add_drum_hit(t_beat + 2 * sub_step, 320.0, 190.0, 24.0, 0.45, 0.35)
            add_drum_hit(t_beat + 3 * sub_step, 360.0, 210.0, 26.0, 0.55, 0.40)

        elif style == "murga":
            # Argentina (128 BPM): Bombo con platillo de cancha argentina
            add_drum_hit(t_beat, 115.0, 54.0, 10.0, 0.85, 0.10)
            add_drum_hit(t_beat + 2 * sub_step, 900.0, 620.0, 20.0, 0.50, 0.75)
            if beat % 2 == 1:
                add_drum_hit(t_beat + 3 * sub_step, 125.0, 58.0, 14.0, 0.65, 0.12)

        elif style == "candombe":
            # Uruguay (120 BPM): Cuerda de tambores Piano, Repique y Chico (clave 3-2)
            add_drum_hit(t_beat, 110.0, 58.0, 11.0, 0.82, 0.10)
            add_drum_hit(t_beat + 1 * sub_step, 420.0, 280.0, 28.0, 0.48, 0.30)
            add_drum_hit(t_beat + 2.5 * sub_step, 380.0, 240.0, 25.0, 0.55, 0.35)

        elif style == "cumbia":
            # Colombia (130 BPM): Tambora caribeña + llamador en contratiempo + maracón
            add_drum_hit(t_beat, 130.0, 65.0, 12.0, 0.80, 0.10)
            add_drum_hit(t_beat + 2 * sub_step, 260.0, 165.0, 18.0, 0.65, 0.45)
            add_drum_hit(t_beat + 3 * sub_step, 520.0, 310.0, 30.0, 0.40, 0.65)

        elif style == "cueca":
            # Chile (125 BPM): Bombo de estadio en cadencia de Cueca Brava + redoble y palmas
            add_drum_hit(t_beat, 118.0, 56.0, 11.0, 0.84, 0.10)
            add_drum_hit(t_beat + 1.5 * sub_step, 390.0, 230.0, 26.0, 0.52, 0.48)
            add_drum_hit(t_beat + 3 * sub_step, 640.0, 410.0, 28.0, 0.46, 0.60)

        elif style == "polka_guarani":
            # Paraguay (120 BPM): Polka Guaraní sincopada (polirritmia 6/8 sobre bajo 3/4) + redoblante
            add_drum_hit(t_beat, 112.0, 55.0, 10.5, 0.83, 0.09)
            add_drum_hit(t_beat + 1.33 * sub_step, 340.0, 200.0, 24.0, 0.50, 0.42)
            add_drum_hit(t_beat + 2.66 * sub_step, 460.0, 275.0, 25.0, 0.56, 0.45)

        elif style == "cajon":
            # Perú (118 BPM): Cajón peruano afro-costeño (grave central + slap agudo de borde + quijada)
            add_drum_hit(t_beat, 135.0, 64.0, 13.0, 0.82, 0.12)
            add_drum_hit(t_beat + 1.5 * sub_step, 680.0, 420.0, 32.0, 0.54, 0.62)
            add_drum_hit(t_beat + 3 * sub_step, 720.0, 450.0, 30.0, 0.58, 0.65)

        elif style == "sanjuanito":
            # Ecuador (135 BPM): San Juanito andino vivaz + marimba y bombo
            add_drum_hit(t_beat, 122.0, 60.0, 12.0, 0.82, 0.09)
            add_drum_hit(t_beat + 2 * sub_step, 440.0, 295.0, 24.0, 0.55, 0.28)
            add_drum_hit(t_beat + 3 * sub_step, 520.0, 350.0, 28.0, 0.48, 0.35)

        elif style == "joropo":
            # Venezuela (170 BPM): Joropo / Tambor urbano de alta velocidad + cumaco y charrasca
            add_drum_hit(t_beat, 140.0, 68.0, 14.0, 0.80, 0.12)
            add_drum_hit(t_beat + 2 * sub_step, 490.0, 310.0, 28.0, 0.52, 0.55)
            if beat % 2 == 0:
                add_drum_hit(t_beat + 3 * sub_step, 820.0, 540.0, 34.0, 0.44, 0.72)

        elif style == "andes":
            # Bolivia (110 BPM): Bombo legüero (aro + parche profundo a 3600m)
            add_drum_hit(t_beat, 105.0, 48.0, 9.5, 0.85, 0.08)
            add_drum_hit(t_beat + 1.5 * sub_step, 480.0, 340.0, 26.0, 0.50, 0.50)
            add_drum_hit(t_beat + 3 * sub_step, 110.0, 52.0, 12.0, 0.70, 0.10)

    return [math.tanh(s) for s in out]


def generate_haptic_dualsense_turf_slide() -> list[float]:
    """Onda táctil 40Hz-160Hz (380 ms) optimizada para los actuadores de voz de DualSense (Wwise Motion)."""
    duration = 0.38
    num_samples = int(SAMPLE_RATE * duration)
    out = []
    phase = 0.0
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (t / duration))
        freq = 155.0 - 110.0 * (t / duration)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        grain = 0.75 + 0.25 * math.sin(2.0 * math.pi * 34.0 * t)
        out.append(math.sin(phase) * grain * env * 0.90)
    return out


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo_root, "Audio", "GeneratedStems")
    os.makedirs(out_dir, exist_ok=True)

    # Limpiar archivo duplicado heredado con espacio si existiera
    legacy_dup = os.path.join(out_dir, "Haptic_DualSense_SubBass_ TurfSlide.wav")
    if os.path.isfile(legacy_dup):
        os.remove(legacy_dup)

    stems = {
        # 8 SFX de Combate, Arbitraje y Coro Reactivo
        "SFX_Hit_Light_Jab.wav": generate_hit_light_jab(),
        "SFX_Hit_Heavy_Counter.wav": generate_hit_heavy_counter(),
        "SFX_Block_Shield_Plus.wav": generate_block_shield_plus(),
        "SFX_Gambeta_Whoosh_Parry.wav": generate_gambeta_whoosh_parry(),
        "SFX_Referee_Whistle_Start.wav": generate_referee_whistle_start(),
        "SFX_Crossbar_Metallic_Clank.wav": generate_crossbar_metallic_clank(),
        "SFX_VAR_Glitch_Rewind.wav": generate_var_glitch_rewind(),
        "SFX_Crowd_Ole_Chant.wav": generate_crowd_ole_chant(),
        # 10 Stems Nacionales CONMEBOL a su BPM exacto de DT_StagesCONMEBOL.json
        "Stem_Crowd_Brazil_Batucada_115BPM.wav": generate_percussion_loop(115.0, 1, "batucada"),
        "Stem_Crowd_Argentina_BomboMurga_128BPM.wav": generate_percussion_loop(128.0, 1, "murga"),
        "Stem_Crowd_Uruguay_Candombe_120BPM.wav": generate_percussion_loop(120.0, 1, "candombe"),
        "Stem_Crowd_Colombia_CumbiaTambora_130BPM.wav": generate_percussion_loop(130.0, 1, "cumbia"),
        "Stem_Crowd_Chile_CuecaBombo_125BPM.wav": generate_percussion_loop(125.0, 1, "cueca"),
        "Stem_Crowd_Paraguay_PolkaGuarani_120BPM.wav": generate_percussion_loop(120.0, 1, "polka_guarani"),
        "Stem_Crowd_Peru_CajonCriollo_118BPM.wav": generate_percussion_loop(118.0, 1, "cajon"),
        "Stem_Crowd_Ecuador_SanJuanitoAndino_135BPM.wav": generate_percussion_loop(135.0, 1, "sanjuanito"),
        "Stem_Crowd_Venezuela_JoropoTambor_170BPM.wav": generate_percussion_loop(170.0, 1, "joropo"),
        "Stem_Crowd_Andes_BomboLeguero_110BPM.wav": generate_percussion_loop(110.0, 1, "andes"),
        # 1 Sub-grave Háptico DualSense (Wwise Motion 30-180Hz)
        "Haptic_DualSense_SubBass_TurfSlide.wav": generate_haptic_dualsense_turf_slide(),
    }

    for filename, samples in stems.items():
        full_path = os.path.join(out_dir, filename)
        write_wav_mono(full_path, samples)
        print(f"[OK] Generado: {filename} ({len(samples)} muestras @ {SAMPLE_RATE}Hz, {os.path.getsize(full_path)} bytes)")


if __name__ == "__main__":
    main()
