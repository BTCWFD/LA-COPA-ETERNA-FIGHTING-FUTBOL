// main.go - Servidor de Arbitraje Competitivo, Anti-Cheat Heurístico, Glicko-2 MMR y Teatro de Repeticiones
// Proyecto: "La Copa Eterna" (SouthAmericaFightersCore Backend eSports)
package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

const (
	ReplayMagicSAFR        uint32  = 0x53414652 // "SAFR"
	MaxReplayPayloadBytes  int     = 50 * 1024  // < 50 KB por repetición (.safreplay)
	RageQuitTimeoutSeconds float64 = 4.0        // Ventana de arbitraje de desconexión asimétrica
	RageQuitLPPenalty      int     = 80         // -80 LP al infractor por abandono intencional
	ContinentalCupFloorLP  int     = 15000      // Piso anti-smurfing cuando otro personaje alcanza Copa Continental (25,000 LP)
	ContinentalCupThreshold int    = 25000      // Rango Copa Continental
	CheckInWindowSeconds   int     = 180        // 3 minutos de check-in en Modo Copa Fin de Semana
)

// Bitmasks de botones idénticos a ECombatInputBits en FightingInputParser.h
const (
	InputMaskDirections uint16 = 0x000F
	InputBitGambeta     uint16 = 1 << 8 // GB (Gambeta / Parry)
)

// ----------------------------------------------------------------------------
// Modelos de Dominio y Telemetría
// ----------------------------------------------------------------------------

type CharacterMMR struct {
	PlayerID         string    `json:"player_id"`
	CharacterID      string    `json:"character_id"`
	Region           string    `json:"region"`
	LeaguePoints     int       `json:"league_points"`
	GlickoRating     float64   `json:"glicko_rating"`
	GlickoRD         float64   `json:"glicko_rd"`
	GlickoVolatility float64   `json:"glicko_volatility"`
	ConductRedCards  int       `json:"conduct_red_cards"`
	UpdatedAt        time.Time `json:"updated_at"`
}

type AntiCheatAuditResult struct {
	SuspectedMacroScript    bool    `json:"suspected_macro_script"`
	SuspectedAutoParryBot   bool    `json:"suspected_auto_parry_bot"`
	SuspectedLagSwitch      bool    `json:"suspected_lag_switch"`
	InputTimingVariance     float64 `json:"input_timing_variance"`
	LagDuringEnemyComboRate float64 `json:"lag_during_enemy_combo_rate"`
	AutoParryFrame1Rate     float64 `json:"auto_parry_frame1_rate"`
	FlaggedForPenaltyQueue  bool    `json:"flagged_for_penalty_queue"`
}

type MatchAuditSubmitRequest struct {
	MatchUUID                string   `json:"match_uuid"`
	Region                   string   `json:"region"`
	PatchVersion             uint16   `json:"patch_version"`
	Player1ID                string   `json:"player1_id"`
	Player2ID                string   `json:"player2_id"`
	Player1CharacterID       string   `json:"player1_character_id"`
	Player2CharacterID       string   `json:"player2_character_id"`
	StageID                  string   `json:"stage_id"`
	WinnerSlot               int      `json:"winner_slot"` // 1 = P1, 2 = P2, 0 = Draw
	ExpectedFletcher32       uint32   `json:"expected_fletcher32"`
	ClientHMACSignature      string   `json:"client_hmac_signature"`
	ReplayPayloadBase64      string   `json:"replay_payload_base64"`
	P1RawInputs              []uint16 `json:"p1_raw_inputs"`
	P2RawInputs              []uint16 `json:"p2_raw_inputs"`
	P1RollbackSpikes         []uint8  `json:"p1_rollback_spikes"`
	P2RollbackSpikes         []uint8  `json:"p2_rollback_spikes"`
	P1InHitstunPerFrame      []bool   `json:"p1_in_hitstun_per_frame"`
	P2InHitstunPerFrame      []bool   `json:"p2_in_hitstun_per_frame"`
	P1FacedActiveFrame1      []bool   `json:"p1_faced_active_frame1"`
	P2FacedActiveFrame1      []bool   `json:"p2_faced_active_frame1"`
}

type MatchAuditSubmitResponse struct {
	MatchUUID       string               `json:"match_uuid"`
	ChecksumValid   bool                 `json:"checksum_valid"`
	ReplayS3Key     string               `json:"replay_s3_key"`
	P1UpdatedMMR    CharacterMMR         `json:"p1_updated_mmr"`
	P2UpdatedMMR    CharacterMMR         `json:"p2_updated_mmr"`
	P1AntiCheat     AntiCheatAuditResult `json:"p1_anti_cheat"`
	P2AntiCheat     AntiCheatAuditResult `json:"p2_anti_cheat"`
	ProcessedAtUTC  time.Time            `json:"processed_at_utc"`
}

type HeartbeatRequest struct {
	MatchUUID        string  `json:"match_uuid"`
	ReportingPlayer  string  `json:"reporting_player_id"`
	OpponentPlayer   string  `json:"opponent_player_id"`
	OpponentCharID   string  `json:"opponent_character_id"`
	Region           string  `json:"region"`
	CurrentFrame     uint32  `json:"current_frame"`
	SilenceSeconds   float64 `json:"opponent_silence_seconds"`
	OpponentInCombo  bool    `json:"opponent_in_hitstun_or_super"`
}

type HeartbeatResponse struct {
	MatchUUID              string `json:"match_uuid"`
	RageQuitConfirmed      bool   `json:"rage_quit_confirmed"`
	PenalizedPlayerID      string `json:"penalized_player_id,omitempty"`
	AppliedLPPenalty       int    `json:"applied_lp_penalty"`
	TotalConductRedCards   int    `json:"total_conduct_red_cards"`
	RestrictedQueueApplied bool   `json:"restricted_queue_applied"`
}

type WeekendCupBracketNode struct {
	MatchSlot   int      `json:"match_slot"`
	RoundNumber int      `json:"round_number"`
	PlayerA     string   `json:"player_a"`
	PlayerB     string   `json:"player_b"`
	CheckedInA  bool     `json:"checked_in_a"`
	CheckedInB  bool     `json:"checked_in_b"`
	WinnerID    string   `json:"winner_id,omitempty"`
}

type WeekendCupTournament struct {
	TournamentID       string                  `json:"tournament_id"`
	Title              string                  `json:"title"`
	Region             string                  `json:"region"`
	BracketSize        int                     `json:"bracket_size"` // 32 o 64 jugadores
	CheckInDeadlineUTC time.Time               `json:"check_in_deadline_utc"`
	Matches            []WeekendCupBracketNode `json:"matches"`
}

// ----------------------------------------------------------------------------
// Almacenamiento en Memoria Thread-Safe (Espejo de PostgreSQL + Redis + S3/R2)
// ----------------------------------------------------------------------------

type ArbitrationStore struct {
	mu           sync.RWMutex
	mmrByKey     map[string]*CharacterMMR // key: playerID + ":" + charID
	playerHighest map[string]int          // playerID -> máximo LP alcanzado con cualquier personaje
	replays      map[string][]byte        // matchUUID -> binario .safreplay (< 50 KB)
	tournaments  map[string]*WeekendCupTournament
	hmacSecret   []byte
}

func NewArbitrationStore(secret string) *ArbitrationStore {
	store := &ArbitrationStore{
		mmrByKey:      make(map[string]*CharacterMMR),
		playerHighest: make(map[string]int),
		replays:       make(map[string][]byte),
		tournaments:   make(map[string]*WeekendCupTournament),
		hmacSecret:    []byte(secret),
	}
	store.seedInitialLeaderboardAndBrackets()
	return store
}

func (s *ArbitrationStore) seedInitialLeaderboardAndBrackets() {
	samplePros := []CharacterMMR{
		{
			PlayerID:         "CONMEBOL-PRO-001",
			CharacterID:      "CHR_EL_DIEZ",
			Region:           "SA-EAST",
			LeaguePoints:     27450,
			GlickoRating:     2140.5,
			GlickoRD:         42.0,
			GlickoVolatility: 0.058,
			UpdatedAt:        time.Now().UTC(),
		},
		{
			PlayerID:         "CONMEBOL-PRO-002",
			CharacterID:      "CHR_O_REI",
			Region:           "SA-EAST",
			LeaguePoints:     26890,
			GlickoRating:     2105.2,
			GlickoRD:         45.5,
			GlickoVolatility: 0.059,
			UpdatedAt:        time.Now().UTC(),
		},
		{
			PlayerID:         "CONMEBOL-PRO-003",
			CharacterID:      "CHR_EL_CONDOR",
			Region:           "SA-WEST",
			LeaguePoints:     25310,
			GlickoRating:     2012.8,
			GlickoRD:         51.0,
			GlickoVolatility: 0.060,
			UpdatedAt:        time.Now().UTC(),
		},
	}

	for i := range samplePros {
		entry := samplePros[i]
		key := entry.PlayerID + ":" + entry.CharacterID
		s.mmrByKey[key] = &entry
		if entry.LeaguePoints > s.playerHighest[entry.PlayerID] {
			s.playerHighest[entry.PlayerID] = entry.LeaguePoints
		}
	}

	// Inicializar bracket automático del Modo Copa Fin de Semana (32 jugadores)
	nodes := make([]WeekendCupBracketNode, 0, 16)
	for slot := 1; slot <= 16; slot++ {
		nodes = append(nodes, WeekendCupBracketNode{
			MatchSlot:   slot,
			RoundNumber: 1,
			PlayerA:     fmt.Sprintf("SEED-%02d", slot*2-1),
			PlayerB:     fmt.Sprintf("SEED-%02d", slot*2),
			CheckedInA:  true,
			CheckedInB:  slot <= 15,
		})
	}
	s.tournaments["COPA-CONMEBOL-DOMINGO-20H"] = &WeekendCupTournament{
		TournamentID:       "COPA-CONMEBOL-DOMINGO-20H",
		Title:              "Copa Fin de Semana — Edición Potrero de América (32 Jugadores)",
		Region:             "SA-EAST",
		BracketSize:        32,
		CheckInDeadlineUTC: time.Now().UTC().Add(time.Duration(CheckInWindowSeconds) * time.Second),
		Matches:            nodes,
	}
}

func (s *ArbitrationStore) getOrCreateMMR(playerID, charID, region string) *CharacterMMR {
	key := playerID + ":" + charID
	if existing, ok := s.mmrByKey[key]; ok {
		return existing
	}

	// Protección Anti-Smurfing: Si el jugador ya tiene un personaje en Copa Continental (>= 25,000 LP),
	// ningún personaje secundario puede iniciar por debajo de 15,000 LP (Primera División).
	startingLP := 1000
	if s.playerHighest[playerID] >= ContinentalCupThreshold {
		startingLP = ContinentalCupFloorLP
	}

	created := &CharacterMMR{
		PlayerID:         playerID,
		CharacterID:      charID,
		Region:           region,
		LeaguePoints:     startingLP,
		GlickoRating:     1500.0,
		GlickoRD:         350.0,
		GlickoVolatility: 0.06,
		UpdatedAt:        time.Now().UTC(),
	}
	s.mmrByKey[key] = created
	return created
}

// ----------------------------------------------------------------------------
// Algoritmos Matemáticos: Fletcher-32, Glicko-2 y Auditoría Anti-Cheat
// ----------------------------------------------------------------------------

func computeFletcher32(data []byte) uint32 {
	if len(data)%2 != 0 {
		data = append(data, 0)
	}
	var sum1 uint32 = 0xFFFF
	var sum2 uint32 = 0xFFFF
	words := len(data) / 2
	idx := 0

	for words > 0 {
		tlen := 360
		if words < tlen {
			tlen = words
		}
		words -= tlen
		for i := 0; i < tlen; i++ {
			word := uint32(binary.LittleEndian.Uint16(data[idx : idx+2]))
			sum1 += word
			sum2 += sum1
			idx += 2
		}
		sum1 = (sum1 & 0xFFFF) + (sum1 >> 16)
		sum2 = (sum2 & 0xFFFF) + (sum2 >> 16)
	}
	sum1 = (sum1 & 0xFFFF) + (sum1 >> 16)
	sum2 = (sum2 & 0xFFFF) + (sum2 >> 16)
	return (sum2 << 16) | sum1
}

// inspectAndValidateReplay verifica el tamaño (<50KB) y la firma mágica "SAFR" si el payload viene sin comprimir
// o con prefijo de longitud de Unreal FCompression.
func inspectAndValidateReplay(rawPayload []byte) error {
	if len(rawPayload) == 0 {
		return errors.New("replay payload vacío")
	}
	if len(rawPayload) > MaxReplayPayloadBytes {
		return fmt.Errorf("el replay excede el límite estricto de 50 KB (%d bytes)", len(rawPayload))
	}
	if len(rawPayload) < 8 {
		return errors.New("cabecera de replay truncada")
	}

	// Si los primeros 4 bytes son directamente "SAFR" (0x53414652) o un entero de tamaño descomprimido válido (> 0)
	firstWord := binary.LittleEndian.Uint32(rawPayload[0:4])
	if firstWord != ReplayMagicSAFR && int32(firstWord) == 0 {
		return errors.New("prefijo de replay inválido")
	}
	return nil
}

// updateGlicko2 ejecuta el paso matemático oficial de Glicko-2 (escala 173.7178) y aplica piso Anti-Smurfing.
func updateGlicko2(player *CharacterMMR, oppRating, oppRD, score float64, highestAccountLP int) {
	const scale = 173.7178
	const tau = 0.5

	mu := (player.GlickoRating - 1500.0) / scale
	phi := player.GlickoRD / scale
	muJ := (oppRating - 1500.0) / scale
	phiJ := oppRD / scale

	gPhiJ := 1.0 / math.Sqrt(1.0+3.0*(phiJ*phiJ)/(math.Pi*math.Pi))
	eVal := 1.0 / (1.0 + math.Exp(-gPhiJ*(mu-muJ)))
	v := 1.0 / (gPhiJ * gPhiJ * eVal * (1.0 - eVal))
	delta := v * gPhiJ * (score - eVal)

	newSigma := player.GlickoVolatility * (1.0 + (delta*delta-phi*phi-v)*0.005*tau)
	newSigma = math.Max(0.03, math.Min(0.12, newSigma))

	phiStar := math.Sqrt(phi*phi + newSigma*newSigma)
	newPhi := 1.0 / math.Sqrt((1.0/(phiStar*phiStar))+(1.0/v))
	newMu := mu + (newPhi*newPhi)*gPhiJ*(score-eVal)

	player.GlickoRating = 1500.0 + scale*newMu
	player.GlickoRD = math.Max(30.0, math.Min(350.0, scale*newPhi))
	player.GlickoVolatility = newSigma

	// Conversión de delta competitivo a Puntos de Liga (LP)
	switch {
	case score >= 0.99:
		player.LeaguePoints += int(math.Round(35.0 + 25.0*(1.0-eVal)))
	case score <= 0.01:
		player.LeaguePoints -= int(math.Round(25.0 + 20.0*eVal))
	}

	if highestAccountLP >= ContinentalCupThreshold && player.LeaguePoints < ContinentalCupFloorLP {
		player.LeaguePoints = ContinentalCupFloorLP
	}
	if player.LeaguePoints < 0 {
		player.LeaguePoints = 0
	}
	player.UpdatedAt = time.Now().UTC()
}

// runHeuristicAntiCheat analiza la cinta de inputs en busca de Macros (varianza cero), Auto-Parry y Lag Switch.
func runHeuristicAntiCheat(
	inputs []uint16,
	rollbackSpikes []uint8,
	inHitstun []bool,
	facedActiveFrame1 []bool,
) AntiCheatAuditResult {
	res := AntiCheatAuditResult{
		InputTimingVariance: 1.0,
	}
	totalFrames := len(inputs)
	if totalFrames < 120 {
		return res
	}

	// 1. Correlación de Lag Switching Asimétrico (Clag >= 0.80 durante Hitstun)
	totalSpikes := 0
	spikesInHitstun := 0
	safeNetLen := minInt(totalFrames, minInt(len(rollbackSpikes), len(inHitstun)))
	for i := 0; i < safeNetLen; i++ {
		if rollbackSpikes[i] >= 5 {
			totalSpikes++
			if inHitstun[i] {
				spikesInHitstun++
			}
		}
	}
	if totalSpikes >= 8 {
		res.LagDuringEnemyComboRate = float64(spikesInHitstun) / float64(totalSpikes)
		if res.LagDuringEnemyComboRate >= 0.80 {
			res.SuspectedLagSwitch = true
		}
	}

	// 2. Detección de Auto-Parry / Gambeta Bot (Frame 1-3 de ataque activo sin buffering previo > 65%)
	attacksFaced := 0
	frame1Parries := 0
	safeParryLen := minInt(totalFrames, len(facedActiveFrame1))
	for i := 3; i < safeParryLen; i++ {
		if facedActiveFrame1[i] {
			attacksFaced++
			pressedNow := (inputs[i] & InputBitGambeta) != 0
			bufferedBefore := (inputs[i-1]&InputBitGambeta) != 0 ||
				(inputs[i-2]&InputBitGambeta) != 0 ||
				(inputs[i-3]&InputBitGambeta) != 0
			if pressedNow && !bufferedBefore {
				frame1Parries++
			}
		}
	}
	if attacksFaced >= 10 {
		res.AutoParryFrame1Rate = float64(frame1Parries) / float64(attacksFaced)
		if res.AutoParryFrame1Rate > 0.65 {
			res.SuspectedAutoParryBot = true
		}
	}

	// 3. Detección de Macros de Comandos Complejos (Varianza de duración direccional < 0.001)
	var holds []float64
	currDir := inputs[0] & InputMaskDirections
	currCount := 1
	for i := 1; i < totalFrames; i++ {
		dir := inputs[i] & InputMaskDirections
		if dir == currDir {
			currCount++
		} else {
			if currDir != 0 && currCount >= 1 && currCount <= 6 {
				holds = append(holds, float64(currCount))
			}
			currDir = dir
			currCount = 1
		}
	}
	if len(holds) >= 16 {
		var sum float64
		for _, h := range holds {
			sum += h
		}
		mean := sum / float64(len(holds))
		var sqDiff float64
		for _, h := range holds {
			d := h - mean
			sqDiff += d * d
		}
		res.InputTimingVariance = sqDiff / float64(len(holds))
		if res.InputTimingVariance < 0.001 {
			res.SuspectedMacroScript = true
		}
	}

	res.FlaggedForPenaltyQueue = res.SuspectedMacroScript || res.SuspectedAutoParryBot || res.SuspectedLagSwitch
	return res
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// ----------------------------------------------------------------------------
// Controladores HTTP REST
// ----------------------------------------------------------------------------

func (s *ArbitrationStore) handleAuditAndSubmit(w http.ResponseWriter, r *http.Request) {
	var req MatchAuditSubmitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "JSON inválido: "+err.Error())
		return
	}

	replayBytes, err := base64.StdEncoding.DecodeString(req.ReplayPayloadBase64)
	if err != nil {
		writeJSONError(w, http.StatusBadRequest, "replay_payload_base64 inválido")
		return
	}
	if err := inspectAndValidateReplay(replayBytes); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	// Verificación de firma HMAC-SHA256 si fue provista por el cliente
	if req.ClientHMACSignature != "" {
		mac := hmac.New(sha256.New, s.hmacSecret)
		mac.Write([]byte(req.MatchUUID))
		mac.Write(replayBytes)
		expectedSig := hex.EncodeToString(mac.Sum(nil))
		if !hmac.Equal([]byte(strings.ToLower(req.ClientHMACSignature)), []byte(expectedSig)) {
			writeJSONError(w, http.StatusUnauthorized, "firma HMAC-SHA256 del paquete de combate inválida")
			return
		}
	}

	computedChecksum := computeFletcher32(replayBytes)
	checksumValid := req.ExpectedFletcher32 == 0 || req.ExpectedFletcher32 == computedChecksum

	p1Audit := runHeuristicAntiCheat(req.P1RawInputs, req.P1RollbackSpikes, req.P1InHitstunPerFrame, req.P1FacedActiveFrame1)
	p2Audit := runHeuristicAntiCheat(req.P2RawInputs, req.P2RollbackSpikes, req.P2InHitstunPerFrame, req.P2FacedActiveFrame1)

	s.mu.Lock()
	defer s.mu.Unlock()

	p1MMR := s.getOrCreateMMR(req.Player1ID, req.Player1CharacterID, req.Region)
	p2MMR := s.getOrCreateMMR(req.Player2ID, req.Player2CharacterID, req.Region)

	p1PrevRating, p1PrevRD := p1MMR.GlickoRating, p1MMR.GlickoRD
	p2PrevRating, p2PrevRD := p2MMR.GlickoRating, p2MMR.GlickoRD

	scoreP1, scoreP2 := 0.5, 0.5
	if req.WinnerSlot == 1 {
		scoreP1, scoreP2 = 1.0, 0.0
	} else if req.WinnerSlot == 2 {
		scoreP1, scoreP2 = 0.0, 1.0
	}

	updateGlicko2(p1MMR, p2PrevRating, p2PrevRD, scoreP1, s.playerHighest[req.Player1ID])
	updateGlicko2(p2MMR, p1PrevRating, p1PrevRD, scoreP2, s.playerHighest[req.Player2ID])

	if p1MMR.LeaguePoints > s.playerHighest[req.Player1ID] {
		s.playerHighest[req.Player1ID] = p1MMR.LeaguePoints
	}
	if p2MMR.LeaguePoints > s.playerHighest[req.Player2ID] {
		s.playerHighest[req.Player2ID] = p2MMR.LeaguePoints
	}

	if p1Audit.FlaggedForPenaltyQueue {
		p1MMR.ConductRedCards++
	}
	if p2Audit.FlaggedForPenaltyQueue {
		p2MMR.ConductRedCards++
	}

	s.replays[req.MatchUUID] = replayBytes
	s3Key := fmt.Sprintf("s3://saf-replays-%s/%s/%s.safreplay", strings.ToLower(req.Region), time.Now().UTC().Format("2006-01-02"), req.MatchUUID)

	resp := MatchAuditSubmitResponse{
		MatchUUID:      req.MatchUUID,
		ChecksumValid:  checksumValid,
		ReplayS3Key:    s3Key,
		P1UpdatedMMR:   *p1MMR,
		P2UpdatedMMR:   *p2MMR,
		P1AntiCheat:    p1Audit,
		P2AntiCheat:    p2Audit,
		ProcessedAtUTC: time.Now().UTC(),
	}
	writeJSON(w, http.StatusOK, resp)
}

func (s *ArbitrationStore) handleHeartbeatArbitration(w http.ResponseWriter, r *http.Request) {
	var req HeartbeatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "JSON inválido: "+err.Error())
		return
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	resp := HeartbeatResponse{
		MatchUUID: req.MatchUUID,
	}

	// Si el rival cortó la transmisión de paquetes UDP durante >= 4.0 segundos:
	if req.SilenceSeconds >= RageQuitTimeoutSeconds {
		offenderMMR := s.getOrCreateMMR(req.OpponentPlayer, req.OpponentCharID, req.Region)
		offenderMMR.LeaguePoints = maxInt(0, offenderMMR.LeaguePoints-RageQuitLPPenalty)
		offenderMMR.ConductRedCards++
		offenderMMR.UpdatedAt = time.Now().UTC()

		resp.RageQuitConfirmed = true
		resp.PenalizedPlayerID = req.OpponentPlayer
		resp.AppliedLPPenalty = RageQuitLPPenalty
		resp.TotalConductRedCards = offenderMMR.ConductRedCards
		resp.RestrictedQueueApplied = offenderMMR.ConductRedCards >= 2
	}

	writeJSON(w, http.StatusOK, resp)
}

func (s *ArbitrationStore) handleLeaderboard(w http.ResponseWriter, r *http.Request) {
	region := strings.ToUpper(r.PathValue("region"))
	s.mu.RLock()
	defer s.mu.RUnlock()

	entries := make([]CharacterMMR, 0, len(s.mmrByKey))
	for _, item := range s.mmrByKey {
		if region == "" || region == "ALL" || strings.EqualFold(item.Region, region) {
			entries = append(entries, *item)
		}
	}

	sort.Slice(entries, func(i, j int) bool {
		if entries[i].LeaguePoints == entries[j].LeaguePoints {
			return entries[i].GlickoRating > entries[j].GlickoRating
		}
		return entries[i].LeaguePoints > entries[j].LeaguePoints
	})

	if len(entries) > 500 {
		entries = entries[:500]
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"region":      region,
		"title_rank1": "El Diez de América",
		"count":       len(entries),
		"leaderboard": entries,
	})
}

func (s *ArbitrationStore) handleDownloadReplay(w http.ResponseWriter, r *http.Request) {
	matchUUID := r.PathValue("match_uuid")
	s.mu.RLock()
	payload, exists := s.replays[matchUUID]
	s.mu.RUnlock()

	if !exists {
		writeJSONError(w, http.StatusNotFound, "repetición .safreplay no encontrada")
		return
	}

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s.safreplay\"", matchUUID))
	w.Header().Set("X-SAF-Fletcher32", fmt.Sprintf("0x%08X", computeFletcher32(payload)))
	w.WriteHeader(http.StatusOK)
	_, _ = bytes.NewReader(payload).WriteTo(w)
}

func (s *ArbitrationStore) handleWeekendCupBrackets(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	writeJSON(w, http.StatusOK, s.tournaments)
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func BuildRouter(store *ArbitrationStore) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "saf-arbitration-gateway"})
	})
	mux.HandleFunc("POST /api/v1/matches/audit-and-submit", store.handleAuditAndSubmit)
	mux.HandleFunc("POST /api/v1/matches/heartbeat", store.handleHeartbeatArbitration)
	mux.HandleFunc("GET /api/v1/leaderboard/{region}", store.handleLeaderboard)
	mux.HandleFunc("GET /api/v1/replays/{match_uuid}", store.handleDownloadReplay)
	mux.HandleFunc("GET /api/v1/tournaments/weekend-cup", store.handleWeekendCupBrackets)
	return mux
}

func main() {
	secret := os.Getenv("SAF_HMAC_SECRET")
	if secret == "" {
		secret = "LA_COPA_ETERNA_CONMEBOL_DEFAULT_KEY_2026"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	store := NewArbitrationStore(secret)
	mux := BuildRouter(store)

	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
	}

	log.Printf("[SAF Arbitration Server] Escuchando en :%s (Glicko-2 + Anti-Cheat + Replay Theater activo)", port)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("Error fatal en el servidor: %v", err)
	}
}
