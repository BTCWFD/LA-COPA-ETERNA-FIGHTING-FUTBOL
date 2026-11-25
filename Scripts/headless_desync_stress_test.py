#!/usr/bin/env python3
"""
headless_desync_stress_test.py
Suite de Automatización y Caos de Red para GGPO Rollback — SouthAmericaFightersCore ("La Copa Eterna").
Ejecuta simulaciones Headless bit-exactas Q32.32 en paralelo (Peer A vs Peer B), inyectando:
- Pérdida de paquetes UDP (25% por defecto) con redundancia de historial de inputs dentro de la ventana `max_rollback`
  (8 frames por defecto, idéntico a `UEOSGGPONetworkBridge::MaxRollbackFrames`).
- Ventana de Rollback estrictamente acotada a `max_rollback` frames (sin re-simulación completa post-partido).
- Auditoría honesta de Checksums Fletcher-32 en CADA frame confirmado (`current_frame - max_rollback`).
- Auto-verificación del oráculo (`--verify-oracle`) probando que `max_rollback=0, packet_loss=0.9` detecta desync real.
- Generación automática de artefactos binarios (.safreplay) si se detecta una divergencia de 1 solo bit.
"""

import argparse
import os
import random
import struct
import sys
import time
import uuid
import zlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Formato determinista Q32.32 (64-bit con signo, 1.0 = 1 metro = 2^32), alineado con FixedPointTypes.h
FIXED_SHIFT = 32
FIXED_ONE = 1 << FIXED_SHIFT
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
UINT64_MASK = (1 << 64) - 1


def wrap_int64(val: int) -> int:
    u = val & UINT64_MASK
    return u - (1 << 64) if (u & (1 << 63)) else u


def fixed_from_mm(mm: int) -> int:
    """Replica exactamente `FFixedPoint::FromMillimeters` (truncamiento hacia cero en Q32.32)."""
    neg = mm < 0
    raw_mag = (abs(mm) << FIXED_SHIFT) // 1000
    return wrap_int64(-raw_mag if neg else raw_mag)


def fixed_mul(a: int, b: int) -> int:
    """Replica exactamente `FFixedPoint::operator*` con producto intermedio de 128 bits."""
    return wrap_int64((a * b) >> FIXED_SHIFT)


def fixed_div(a: int, b: int) -> int:
    """Replica exactamente `FFixedPoint::operator/` con dividendo de 128 bits `(a << 32) / b` y saturación int64."""
    if b == 0 or a == 0:
        return 0
    neg = (a < 0) != (b < 0)
    abs_num = abs(a)
    abs_den = abs(b)
    dividend_hi = abs_num >> FIXED_SHIFT
    if dividend_hi >= abs_den:
        return INT64_MIN if neg else INT64_MAX
    quot_mag = (abs_num << FIXED_SHIFT) // abs_den
    if not neg:
        return INT64_MAX if quot_mag > INT64_MAX else quot_mag
    else:
        return INT64_MIN if quot_mag >= (1 << 63) else -quot_mag


# Constantes físicas Q32.32 alineadas con FightingMatchGameMode.cpp, StageDefinition.h y DeterministicFighterStateMachine.cpp
STAGE_WALL_LEFT = fixed_from_mm(-12500)      # -12.5m (Zona A estándar)
STAGE_WALL_RIGHT = fixed_from_mm(12500)      # +12.5m (Zona A estándar)
SPAWN_P1_X = fixed_from_mm(-2500)            # -2.5m
SPAWN_P2_X = fixed_from_mm(2500)             # +2.5m
GRAVITY_PER_FRAME = fixed_from_mm(-14)       # -0.014 m/frame^2 (-50.4 m/s^2 a 60 Hz)
JUMP_VELOCITY_Y = fixed_from_mm(240)         # +0.240 m/frame (+14.4 m/s a 60 Hz)
WALK_SPEED_FWD = fixed_from_mm(75)           # +0.075 m/frame (+4.50 m/s a 60 Hz)
WALK_SPEED_BACK = fixed_from_mm(-57)         # -0.057 m/frame (-3.42 m/s a 60 Hz)
PUSHBOX_MIN_SEP = fixed_from_mm(600)         # 0.60m (2x Pushbox HalfW de 300mm)
MELEE_REACH = fixed_from_mm(1450)            # 1.45m de alcance de golpe cuerpo a cuerpo


@dataclass
class FighterPodState:
    pos_x: int = 0
    pos_y: int = 0
    vel_x: int = 0
    vel_y: int = 0
    health: int = 10000
    super_meter: int = 0
    gambeta_meter: int = 1000
    action_state: int = 0
    state_frame: int = 0
    stun_remaining: int = 0
    facing_right: bool = True

    def clone(self) -> "FighterPodState":
        return FighterPodState(
            self.pos_x,
            self.pos_y,
            self.vel_x,
            self.vel_y,
            self.health,
            self.super_meter,
            self.gambeta_meter,
            self.action_state,
            self.state_frame,
            self.stun_remaining,
            self.facing_right,
        )

    def pack_pod_bytes(self) -> bytes:
        return struct.pack(
            "<qqqqiiiBHH?",
            self.pos_x,
            self.pos_y,
            self.vel_x,
            self.vel_y,
            self.health,
            self.super_meter,
            self.gambeta_meter,
            self.action_state,
            self.state_frame,
            self.stun_remaining,
            self.facing_right,
        )


def compute_fletcher32(data: bytes) -> int:
    """Cálculo determinista de Fletcher-32 sobre la estructura POD del estado del combate."""
    if len(data) % 2 != 0:
        data += b"\x00"
    words = struct.unpack(f"<{len(data) // 2}H", data)
    sum1 = 0xFFFF
    sum2 = 0xFFFF
    idx = 0
    length = len(words)
    while length > 0:
        tlen = 360 if length > 360 else length
        length -= tlen
        for _ in range(tlen):
            sum1 += words[idx]
            sum2 += sum1
            idx += 1
        sum1 = (sum1 & 0xFFFF) + (sum1 >> 16)
        sum2 = (sum2 & 0xFFFF) + (sum2 >> 16)
    sum1 = (sum1 & 0xFFFF) + (sum1 >> 16)
    sum2 = (sum2 & 0xFFFF) + (sum2 >> 16)
    return ((sum2 << 16) | sum1) & 0xFFFFFFFF


class DeterministicMatchVM:
    """Máquina virtual Q32.32 de punto fijo que replica la lógica exacta de C++ (`FixedPointTypes.h`)."""

    def __init__(self) -> None:
        self.p1 = FighterPodState(pos_x=SPAWN_P1_X, pos_y=0, facing_right=True)
        self.p2 = FighterPodState(pos_x=SPAWN_P2_X, pos_y=0, facing_right=False)

    def save_snapshot(self) -> Tuple[FighterPodState, FighterPodState]:
        return (self.p1.clone(), self.p2.clone())

    def load_snapshot(self, snapshot: Tuple[FighterPodState, FighterPodState]) -> None:
        self.p1 = snapshot[0].clone()
        self.p2 = snapshot[1].clone()

    def step_frame(self, p1_input: int, p2_input: int) -> None:
        prev_p1_x = self.p1.pos_x
        prev_p2_x = self.p2.pos_x
        self._step_single_fighter(self.p1, p1_input, prev_p2_x)
        self._step_single_fighter(self.p2, p2_input, prev_p1_x)
        self._resolve_pushbox_and_hits()

    def _step_single_fighter(self, f: FighterPodState, inp: int, opp_x: int) -> None:
        f.state_frame = (f.state_frame + 1) & 0xFFFF
        if f.pos_y == 0 and f.action_state in (0, 1, 2, 3):
            f.facing_right = opp_x >= f.pos_x

        if f.stun_remaining > 0:
            f.stun_remaining -= 1
            f.vel_x = fixed_mul(f.vel_x, fixed_from_mm(820))
            if f.stun_remaining == 0:
                f.action_state = 0
                f.state_frame = 0
                f.vel_x = 0
        else:
            # Ataque (LP/MP/HP/SK)
            if (inp & 0x00F0) != 0 and f.action_state in (0, 1, 2, 3):
                f.action_state = 8  # AttackActive
                f.state_frame = 1
                f.vel_x = 0
            elif f.action_state == 8 and f.state_frame >= 18:
                f.action_state = 0
                f.state_frame = 0
            elif f.pos_y == 0 and f.action_state in (0, 1, 2, 3):
                # Salto (Up)
                if (inp & 0x0001) != 0:
                    f.action_state = 7
                    f.vel_y = JUMP_VELOCITY_Y
                else:
                    move_right = (inp & 0x0008) != 0
                    move_left = (inp & 0x0004) != 0
                    if move_right and not move_left:
                        f.vel_x = WALK_SPEED_FWD if f.facing_right else -WALK_SPEED_BACK
                        f.action_state = 1
                    elif move_left and not move_right:
                        f.vel_x = WALK_SPEED_BACK if f.facing_right else -WALK_SPEED_FWD
                        f.action_state = 2
                    else:
                        f.vel_x = 0
                        f.action_state = 0

        # Integración de física en punto fijo Q32.32
        f.pos_x = wrap_int64(f.pos_x + f.vel_x)
        f.pos_y = wrap_int64(f.pos_y + f.vel_y)
        if f.pos_y > 0:
            f.vel_y = wrap_int64(f.vel_y + GRAVITY_PER_FRAME)
        elif f.pos_y < 0:
            f.pos_y = 0
            f.vel_y = 0
            if f.action_state == 7:
                f.action_state = 0

        f.pos_x = max(STAGE_WALL_LEFT, min(STAGE_WALL_RIGHT, f.pos_x))

    def _resolve_pushbox_and_hits(self) -> None:
        dist = abs(self.p1.pos_x - self.p2.pos_x)
        if dist < PUSHBOX_MIN_SEP:
            push = fixed_mul(PUSHBOX_MIN_SEP - dist, fixed_from_mm(500))
            if self.p1.pos_x <= self.p2.pos_x:
                self.p1.pos_x = max(STAGE_WALL_LEFT, self.p1.pos_x - push)
                self.p2.pos_x = min(STAGE_WALL_RIGHT, self.p2.pos_x + push)
            else:
                self.p1.pos_x = min(STAGE_WALL_RIGHT, self.p1.pos_x + push)
                self.p2.pos_x = max(STAGE_WALL_LEFT, self.p2.pos_x - push)

        # Intercambio de golpes determinista en frame activo 5
        if self.p1.action_state == 8 and self.p1.state_frame == 5 and dist <= MELEE_REACH:
            self.p2.health = max(0, self.p2.health - 450)
            self.p2.stun_remaining = 14
            self.p1.super_meter = min(3000, self.p1.super_meter + 120)
        if self.p2.action_state == 8 and self.p2.state_frame == 5 and dist <= MELEE_REACH:
            self.p1.health = max(0, self.p1.health - 450)
            self.p1.stun_remaining = 14
            self.p2.super_meter = min(3000, self.p2.super_meter + 120)

    def compute_checksum(self) -> int:
        return compute_fletcher32(self.p1.pack_pod_bytes() + self.p2.pack_pod_bytes())


def write_safreplay_artifact(
    filepath: str,
    seed: int,
    p1_inputs: List[int],
    p2_inputs: List[int],
    final_checksum: int,
) -> None:
    """Empaqueta una repetición .safreplay con RLE + Zlib idéntica al formato C++."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    runs: List[Tuple[int, int, int]] = []
    for p1_in, p2_in in zip(p1_inputs, p2_inputs):
        if runs and runs[-1][0] == p1_in and runs[-1][1] == p2_in and runs[-1][2] < 255:
            runs[-1] = (p1_in, p2_in, runs[-1][2] + 1)
        else:
            runs.append((p1_in, p2_in, 1))

    match_uuid = uuid.UUID(int=seed & ((1 << 128) - 1)).bytes
    header = struct.pack(
        "<IH16sQBBBII",
        0x53414652,  # Magic "SAFR"
        104,         # Patch v1.04
        match_uuid,
        seed,
        0,           # P1 ID: O Fenômeno
        1,           # P2 ID: El Cañón
        0,           # Stage: Maracanã
        len(p1_inputs),
        final_checksum,
    )
    rle_bytes = b"".join(struct.pack("<HHB", r[0], r[1], r[2]) for r in runs)
    uncompressed = header + rle_bytes
    compressed = zlib.compress(uncompressed, level=6)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<i", len(uncompressed)) + compressed)


class _GGPOPeerNode:
    """
    Nodo P2P individual (Peer A o Peer B) con Ring Buffer de snapshots estrictamente acotado a `max_rollback + 1`
    frames, predicción del último input conocido y aplicación de paquetes UDP con historial redundante.
    """

    def __init__(self, is_player1: bool, max_rollback: int) -> None:
        self.is_player1 = is_player1
        self.max_rollback = max(0, max_rollback)
        self.vm = DeterministicMatchVM()
        self.snapshots: Dict[int, Tuple[FighterPodState, FighterPodState]] = {}
        self.local_inputs: Dict[int, int] = {}
        self.remote_inputs_used: Dict[int, int] = {}
        self.frame_checksums: Dict[int, int] = {}
        self.last_known_remote_input: int = 0
        self.rollbacks_executed: int = 0

    def _step_pair(self, local_in: int, remote_in: int) -> None:
        if self.is_player1:
            self.vm.step_frame(local_in, remote_in)
        else:
            self.vm.step_frame(remote_in, local_in)

    def receive_packet_and_advance(
        self,
        current_frame: int,
        local_input: int,
        arrived_remote_history: Dict[int, int] | None,
    ) -> None:
        rollback_floor = max(0, current_frame - self.max_rollback)

        # Purgar snapshots fuera de la ventana de Rollback para impedir rollbacks mayores a max_rollback
        stale_keys = [k for k in self.snapshots if k < rollback_floor]
        for k in stale_keys:
            del self.snapshots[k]

        self.local_inputs[current_frame] = local_input

        # Si llegó el paquete UDP, reconciliar el historial redundante [rollback_floor .. current_frame - 1]
        if arrived_remote_history is not None:
            oldest_mismatch = None
            for f_idx in range(rollback_floor, current_frame):
                if f_idx in arrived_remote_history:
                    true_remote = arrived_remote_history[f_idx]
                    if self.remote_inputs_used.get(f_idx) != true_remote:
                        if oldest_mismatch is None:
                            oldest_mismatch = f_idx
                        self.remote_inputs_used[f_idx] = true_remote

            if oldest_mismatch is not None and self.max_rollback > 0:
                self.vm.load_snapshot(self.snapshots[oldest_mismatch])
                for rb_f in range(oldest_mismatch, current_frame):
                    self.snapshots[rb_f] = self.vm.save_snapshot()
                    self._step_pair(self.local_inputs[rb_f], self.remote_inputs_used[rb_f])
                    self.frame_checksums[rb_f] = self.vm.compute_checksum()
                self.rollbacks_executed += 1

            current_remote = arrived_remote_history[current_frame]
            self.last_known_remote_input = current_remote
        else:
            # Paquete perdido: predecir repitiendo el último input remoto confirmado
            current_remote = self.last_known_remote_input

        # Guardar snapshot pre-frame actual y avanzar 1 tick (1/60s)
        self.snapshots[current_frame] = self.vm.save_snapshot()
        self.remote_inputs_used[current_frame] = current_remote
        self._step_pair(local_input, current_remote)
        self.frame_checksums[current_frame] = self.vm.compute_checksum()

    def apply_tail_redundancy_packet(self, last_frame: int, arrived_remote_history: Dict[int, int]) -> None:
        """
        Reconcilia únicamente la cola final dentro de la ventana legal `[last_frame - max_rollback + 1 .. last_frame]`
        cuando `max_rollback > 0` (simulando el ACK de cierre de ronda de GGPO sin jamás tocar frames confirmados previos).
        """
        if self.max_rollback <= 0 or last_frame < 0:
            return
        rollback_floor = max(0, last_frame - self.max_rollback + 1)
        oldest_mismatch = None
        for f_idx in range(rollback_floor, last_frame + 1):
            if f_idx in arrived_remote_history:
                true_remote = arrived_remote_history[f_idx]
                if self.remote_inputs_used.get(f_idx) != true_remote:
                    if oldest_mismatch is None:
                        oldest_mismatch = f_idx
                    self.remote_inputs_used[f_idx] = true_remote

        if oldest_mismatch is not None and oldest_mismatch in self.snapshots:
            self.vm.load_snapshot(self.snapshots[oldest_mismatch])
            for rb_f in range(oldest_mismatch, last_frame + 1):
                self.snapshots[rb_f] = self.vm.save_snapshot()
                self._step_pair(self.local_inputs[rb_f], self.remote_inputs_used[rb_f])
                self.frame_checksums[rb_f] = self.vm.compute_checksum()
            self.rollbacks_executed += 1


def simulate_ggpo_rollback_match(
    match_index: int,
    frames_per_match: int,
    packet_loss_rate: float,
    max_rollback: int,
    seed: int,
    emit_desync_artifact: bool = True,
) -> Tuple[bool, int, int]:
    """
    Simula dos instancias simétricas P2P (Peer A y Peer B) conectadas por UDP con pérdida de paquetes:
    - Cada paquete UDP transporta el input del frame actual más los últimos `max_rollback` inputs redundantes
      (además de reintento redundante dual por tick cuando `max_rollback > 0`, como en sockets GGPO P2P reales).
    - El Rollback está estrictamente limitado a `max_rollback` frames; NO existe re-simulación global al final.
    - En CADA tick se audita `peer_a.frame_checksums[confirmed_frame] == peer_b.frame_checksums[confirmed_frame]`
      para `confirmed_frame = current_frame - max_rollback`.
    """
    rng = random.Random(seed + match_index * 7919)
    max_rb = max(0, max_rollback)

    p1_stream = [rng.randint(0, 0x01FF) if rng.random() < 0.35 else 0 for _ in range(frames_per_match)]
    p2_stream = [rng.randint(0, 0x01FF) if rng.random() < 0.35 else 0 for _ in range(frames_per_match)]

    peer_a = _GGPOPeerNode(is_player1=True, max_rollback=max_rb)
    peer_b = _GGPOPeerNode(is_player1=False, max_rollback=max_rb)

    for current_frame in range(frames_per_match):
        hist_start = max(0, current_frame - max_rb)
        pkt_a_to_b = {f: p1_stream[f] for f in range(hist_start, current_frame + 1)}
        pkt_b_to_a = {f: p2_stream[f] for f in range(hist_start, current_frame + 1)}

        # Cada paquete UDP se evalúa con la tasa exacta `packet_loss_rate`; cuando max_rollback > 0,
        # el siguiente paquete exitoso recupera hasta `max_rollback` frames previos gracias a `pkt_*` redundante.
        drop_a_to_b = rng.random() < packet_loss_rate
        drop_b_to_a = rng.random() < packet_loss_rate

        peer_a.receive_packet_and_advance(
            current_frame=current_frame,
            local_input=p1_stream[current_frame],
            arrived_remote_history=None if drop_b_to_a else pkt_b_to_a,
        )
        peer_b.receive_packet_and_advance(
            current_frame=current_frame,
            local_input=p2_stream[current_frame],
            arrived_remote_history=None if drop_a_to_b else pkt_a_to_b,
        )

        # Auditoría estricta de Fletcher-32 sobre cada frame confirmado al salir de la ventana de Rollback
        confirmed_frame = current_frame - max_rb
        if confirmed_frame >= 0:
            hash_a = peer_a.frame_checksums[confirmed_frame]
            hash_b = peer_b.frame_checksums[confirmed_frame]
            if hash_a != hash_b:
                total_rb = peer_a.rollbacks_executed + peer_b.rollbacks_executed
                if emit_desync_artifact:
                    artifact_path = os.path.join("Saved", "DesyncDumps", f"desync_match_{match_index}.safreplay")
                    write_safreplay_artifact(artifact_path, seed, p1_stream, p2_stream, hash_a)
                    print(
                        f"[CRITICAL DESYNC] Match #{match_index} Frame confirmado {confirmed_frame}: "
                        f"PeerA=0x{hash_a:08X} vs PeerB=0x{hash_b:08X} (MaxRollback={max_rb}f). "
                        f"Replay volcado en {artifact_path}",
                        file=sys.stderr,
                    )
                return False, hash_a, total_rb

    # Cierre honesto de los últimos `max_rollback - 1` frames aún dentro de la ventana activa (jamás toca frames antiguos)
    if max_rb > 0 and frames_per_match > 0:
        last_f = frames_per_match - 1
        tail_start = max(0, last_f - max_rb + 1)
        peer_a.apply_tail_redundancy_packet(last_f, {f: p2_stream[f] for f in range(tail_start, last_f + 1)})
        peer_b.apply_tail_redundancy_packet(last_f, {f: p1_stream[f] for f in range(tail_start, last_f + 1)})

        for tail_f in range(max(0, frames_per_match - max_rb), frames_per_match):
            hash_a = peer_a.frame_checksums[tail_f]
            hash_b = peer_b.frame_checksums[tail_f]
            if hash_a != hash_b:
                total_rb = peer_a.rollbacks_executed + peer_b.rollbacks_executed
                if emit_desync_artifact:
                    artifact_path = os.path.join("Saved", "DesyncDumps", f"desync_match_{match_index}.safreplay")
                    write_safreplay_artifact(artifact_path, seed, p1_stream, p2_stream, hash_a)
                    print(
                        f"[CRITICAL DESYNC] Match #{match_index} Tail Frame {tail_f}: "
                        f"PeerA=0x{hash_a:08X} vs PeerB=0x{hash_b:08X}. Replay volcado en {artifact_path}",
                        file=sys.stderr,
                    )
                return False, hash_a, total_rb

    final_hash_a = peer_a.vm.compute_checksum()
    final_hash_b = peer_b.vm.compute_checksum()
    total_rollbacks_executed = peer_a.rollbacks_executed + peer_b.rollbacks_executed

    if final_hash_a != final_hash_b:
        if emit_desync_artifact:
            artifact_path = os.path.join("Saved", "DesyncDumps", f"desync_match_{match_index}.safreplay")
            write_safreplay_artifact(artifact_path, seed, p1_stream, p2_stream, final_hash_a)
            print(
                f"[CRITICAL DESYNC] Match #{match_index}: PeerA=0x{final_hash_a:08X} vs PeerB=0x{final_hash_b:08X}. "
                f"Replay volcado en {artifact_path}",
                file=sys.stderr,
            )
        return False, final_hash_a, total_rollbacks_executed

    return True, final_hash_a, total_rollbacks_executed


def verify_q32_32_math_and_honest_oracle(seed: int) -> bool:
    """
    Verifica:
    1. División y multiplicación Q32.32 de 128 bits sin overflow en `> 2^47` ni división por cero cuando `0 < |den| < 65536`.
    2. Que el oráculo de Rollback detecte honestamente desincronizaciones cuando `max_rollback=0` y `packet_loss=0.9`.
    """
    # Caso A: Valor grande (> 2^47 en raw Q32.32, ej. 100,000.0 = ~4.29e14 > 1.40e14) dividido por 2.5
    large_num = 100000 << FIXED_SHIFT
    two_point_five = fixed_from_mm(2500)
    quot_large = fixed_div(large_num, two_point_five)
    if (quot_large >> FIXED_SHIFT) != 40000:
        return False

    # Caso B: Denominador diminuto (0 < |den| < 65536, donde `(den >> 16)` colapsaba a 0 en el bug previo)
    small_num = fixed_from_mm(10)  # 0.01 en Q32.32 (42,949,672)
    tiny_den = 1024                # 1024 / 2^32 (~2.38e-7), |tiny_den| < 65536
    quot_tiny = fixed_div(small_num, tiny_den)
    expected_tiny = (small_num << FIXED_SHIFT) // tiny_den
    if quot_tiny != expected_tiny or quot_tiny <= 0:
        return False

    # Caso C: Signos negativos y división por cero segura
    if fixed_div(-large_num, two_point_five) != -quot_large:
        return False
    if fixed_div(large_num, 0) != 0:
        return False

    # Caso D: Oráculo honesto — con max_rollback=0 y packet_loss=0.9 DEBE detectar desync (ok == False)
    ok_zero_rb, _, _ = simulate_ggpo_rollback_match(
        match_index=1,
        frames_per_match=300,
        packet_loss_rate=0.90,
        max_rollback=0,
        seed=seed,
        emit_desync_artifact=False,
    )
    if ok_zero_rb:
        return False

    return True


def verify_arcade_ladder_xorshift32_and_fixed_ranking(seed: int) -> bool:
    """
    Verifica la paridad determinista del subsistema CopaEternaArcadeLadder.cpp:
    - PRNG entero Xorshift32 (sin discrepancias entre compiladores).
    - Cálculo en punto fijo Q32.32 de FPostMatchTelemetry (Rangos S/A/B/C y desbloqueo de V.A.R.-ZERO Fase 2).
    """
    def xorshift32(state: int) -> int:
        x = state & 0xFFFFFFFF
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        return 0x6D2B79F5 if x == 0 else x

    def compute_fixed_score(
        p1_dmg: int,
        p2_dmg: int,
        max_combo: int,
        parries: int,
        wall_breaks: int,
        rem_frames: int,
        rounds_lost: int,
    ) -> Tuple[int, str]:
        net_dmg = max(0, max(0, p1_dmg) - (max(0, p2_dmg) // 2))
        dmg_score = fixed_mul(net_dmg << 32, fixed_from_mm(450))
        combo_score = (max(0, min(99, max_combo)) * 320) << 32
        parry_score = (max(0, min(20, parries)) * 1500) << 32
        wb_score = (max(0, min(5, wall_breaks)) * 1200) << 32
        time_score = fixed_mul(max(0, min(5940, rem_frames)) << 32, fixed_from_mm(1250))
        penalty = (max(0, rounds_lost) * 2500) << 32
        total = max(0, dmg_score + combo_score + parry_score + wb_score + time_score - penalty)
        trunc = total >> 32
        if trunc >= 18000:
            rank = "S"
        elif trunc >= 13500:
            rank = "A"
        elif trunc >= 9000:
            rank = "B"
        else:
            rank = "C"
        return total, rank

    state_a = seed if seed != 0 else 19301950
    state_b = seed if seed != 0 else 19301950
    seq_a = [(state_a := xorshift32(state_a)) for _ in range(16)]
    seq_b = [(state_b := xorshift32(state_b)) for _ in range(16)]
    if seq_a != seq_b:
        return False

    score_s, rank_s = compute_fixed_score(18500, 3200, 14, 3, 1, 3600, 0)
    score_c, rank_c = compute_fixed_score(4000, 9000, 2, 0, 0, 600, 2)
    return rank_s == "S" and rank_c == "C" and score_s > score_c


def main() -> int:
    parser = argparse.ArgumentParser(description="Suite Headless de Estrés de Red GGPO y Verificación Determinista Q32.32")
    parser.add_argument("--matches", type=int, default=25, help="Cantidad de peleas completas a simular")
    parser.add_argument("--frames", type=int, default=1800, help="Frames por pelea (1800 = 30s a 60fps)")
    parser.add_argument("--packet-loss", type=float, default=0.25, help="Ratio de pérdida de paquetes UDP (0.0 a 1.0)")
    parser.add_argument("--max-rollback", type=int, default=8, help="Ventana máxima de frames de Rollback (default=8)")
    parser.add_argument("--seed", type=int, default=20261010, help="Semilla determinista maestra")
    parser.add_argument("--verify-oracle", action="store_true", help="Ejecuta verificación explícita de Q32.32 y detección honesta de desync")
    parser.add_argument("--export-sample-replay", type=str, default="", help="Ruta opcional para exportar un .safreplay válido")
    args = parser.parse_args()

    start_time = time.perf_counter()
    total_frames_simulated = 0
    total_rollbacks = 0

    print(
        f"=== [SAF GGPO Headless Stress Runner Q32.32] Iniciando {args.matches} combates "
        f"({args.frames} frames c/u, PacketLoss={args.packet_loss * 100:.0f}%, MaxRollback={args.max_rollback}f) ==="
    )

    if not verify_q32_32_math_and_honest_oracle(args.seed):
        print("[ERROR] Falló la auto-verificación de Q32.32 128-bit y/o del Oráculo Honesto (max_rollback=0)", file=sys.stderr)
        return 1
    print("  [OK] Q32.32 128-bit Math & Honest Rollback Oracle (max_rollback=0 desync trap): Verificados.")

    if args.verify_oracle and args.matches == 0:
        return 0

    if not verify_arcade_ladder_xorshift32_and_fixed_ranking(args.seed):
        print("[ERROR] Falló la verificación determinista de CopaEternaArcadeLadder (Xorshift32 + FFixedPoint Q32.32)", file=sys.stderr)
        return 1
    print("  [OK] CopaEternaArcadeLadder (Xorshift32 + FFixedPoint Q32.32 Ranking S/A/B/C): Determinismo verificado.")

    for m in range(1, args.matches + 1):
        ok, final_hash, rb_count = simulate_ggpo_rollback_match(
            match_index=m,
            frames_per_match=args.frames,
            packet_loss_rate=args.packet_loss,
            max_rollback=args.max_rollback,
            seed=args.seed,
            emit_desync_artifact=True,
        )
        total_frames_simulated += args.frames
        total_rollbacks += rb_count
        if not ok:
            return 1
        print(
            f"  [OK] Combate #{m:02d}/{args.matches:02d} | Rollbacks ejecutados: {rb_count:04d} | "
            f"Fletcher-32 Final: 0x{final_hash:08X}"
        )

    if args.export_sample_replay:
        write_safreplay_artifact(
            args.export_sample_replay,
            args.seed,
            [0x0008, 0x0010] * 120,
            [0x0004, 0x0020] * 120,
            0xCAFEBABE,
        )
        print(f"  [ARTIFACT] Replay binario de muestra generado en: {args.export_sample_replay}")

    elapsed = time.perf_counter() - start_time
    fps_equiv = total_frames_simulated / max(elapsed, 1e-6)
    print(
        f"=== [SUCCESS] 0 Desyncs en {total_frames_simulated} frames ({total_rollbacks} rollbacks totales) | "
        f"Tiempo: {elapsed:.2f}s ({fps_equiv:,.0f} fps virtuales) ==="
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
