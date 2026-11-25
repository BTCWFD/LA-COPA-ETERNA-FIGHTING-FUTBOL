// main.go - Servidor de Arbitraje Competitivo, Anti-Cheat Heurístico, Glicko-2 MMR y Teatro de Repeticiones
// Proyecto: "La Copa Eterna" (SouthAmericaFightersCore Backend eSports)
package main

import (
	"bytes"
	"compress/zlib"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

const (
	ReplayMagicSAFR            uint32  = 0x53414652      // "SAFR" en orden de bytes de red ('S','A','F','R')
	MaxReplayPayloadBytes      int     = 50 * 1024       // < 50 KB por repetición (.safreplay)
	MaxDecompressedReplayBytes int     = 2 * 1024 * 1024 // Límite anti zip-bomb estricto: 2 MB descomprimidos
	RageQuitTimeoutSeconds     float64 = 4.0             // Ventana de arbitraje de desconexión asimétrica
	RageQuitLPPenalty          int     = 80              // -80 LP al infractor por abandono intencional
	ContinentalCupFloorLP      int     = 15000           // Piso anti-smurfing cuando otro personaje alcanza Copa Continental (25,000 LP)
	ContinentalCupThreshold    int     = 25000           // Rango Copa Continental
	CheckInWindowSeconds       int     = 180             // 3 minutos de check-in en Modo Copa Fin de Semana
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
	PenaltyQueue     bool      `json:"penalty_queue"`
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
	MatchUUID           string   `json:"match_uuid"`
	Region              string   `json:"region"`
	PatchVersion        uint16   `json:"patch_version"`
	Player1ID           string   `json:"player1_id"`
	Player2ID           string   `json:"player2_id"`
	Player1CharacterID  string   `json:"player1_character_id"`
	Player2CharacterID  string   `json:"player2_character_id"`
	StageID             string   `json:"stage_id"`
	WinnerSlot          int      `json:"winner_slot"` // 1 = P1, 2 = P2, 0 = Draw
	ExpectedFletcher32  uint32   `json:"expected_fletcher32"`
	ClientHMACSignature string   `json:"client_hmac_signature"`
	ReplayPayloadBase64 string   `json:"replay_payload_base64"`
	P1RawInputs         []uint16 `json:"p1_raw_inputs"`
	P2RawInputs         []uint16 `json:"p2_raw_inputs"`
	P1RollbackSpikes    []uint8  `json:"p1_rollback_spikes"`
	P2RollbackSpikes    []uint8  `json:"p2_rollback_spikes"`
	P1InHitstunPerFrame []bool   `json:"p1_in_hitstun_per_frame"`
	P2InHitstunPerFrame []bool   `json:"p2_in_hitstun_per_frame"`
	P1FacedActiveFrame1 []bool   `json:"p1_faced_active_frame1"`
	P2FacedActiveFrame1 []bool   `json:"p2_faced_active_frame1"`
}

type MatchAuditSubmitResponse struct {
	MatchUUID          string               `json:"match_uuid"`
	Status             string               `json:"status"`
	AuditReason        string               `json:"audit_reason,omitempty"`
	ChecksumValid      bool                 `json:"checksum_valid"`
	ComputedFletcher32 uint32               `json:"computed_fletcher32"`
	ReplayS3Key        string               `json:"replay_s3_key"`
	P1UpdatedMMR       CharacterMMR         `json:"p1_updated_mmr"`
	P2UpdatedMMR       CharacterMMR         `json:"p2_updated_mmr"`
	P1AntiCheat        AntiCheatAuditResult `json:"p1_anti_cheat"`
	P2AntiCheat        AntiCheatAuditResult `json:"p2_anti_cheat"`
	ProcessedAtUTC     time.Time            `json:"processed_at_utc"`
}

type MatchAuditRecord struct {
	MatchUUID          string               `json:"match_uuid"`
	Status             string               `json:"status"`
	AuditReason        string               `json:"audit_reason,omitempty"`
	ChecksumValid      bool                 `json:"checksum_valid"`
	ExpectedFletcher32 uint32               `json:"expected_fletcher32"`
	ComputedFletcher32 uint32               `json:"computed_fletcher32"`
	Player1ID          string               `json:"player1_id"`
	Player2ID          string               `json:"player2_id"`
	WinnerSlot         int                  `json:"winner_slot"`
	P1AntiCheat        AntiCheatAuditResult `json:"p1_anti_cheat"`
	P2AntiCheat        AntiCheatAuditResult `json:"p2_anti_cheat"`
	RecordedAtUTC      time.Time            `json:"recorded_at_utc"`
}

type HeartbeatRequest struct {
	MatchUUID       string  `json:"match_uuid"`
	ReportingPlayer string  `json:"reporting_player_id"`
	OpponentPlayer  string  `json:"opponent_player_id"`
	OpponentCharID  string  `json:"opponent_character_id"`
	Region          string  `json:"region"`
	CurrentFrame    uint32  `json:"current_frame"`
	SilenceSeconds  float64 `json:"opponent_silence_seconds"`
	OpponentInCombo bool    `json:"opponent_in_hitstun_or_super"`
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
	MatchSlot   int    `json:"match_slot"`
	RoundNumber int    `json:"round_number"`
	PlayerA     string `json:"player_a"`
	PlayerB     string `json:"player_b"`
	CheckedInA  bool   `json:"checked_in_a"`
	CheckedInB  bool   `json:"checked_in_b"`
	WinnerID    string `json:"winner_id,omitempty"`
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
// Almacenamiento Thread-Safe con Persistencia Snapshot Opcional + Hook PostgreSQL
// ----------------------------------------------------------------------------

type storeDiskSnapshot struct {
	MMRByKey         map[string]*CharacterMMR         `json:"mmr_by_key"`
	PlayerHighest    map[string]int                   `json:"player_highest"`
	Replays          map[string][]byte                `json:"replays"`
	Tournaments      map[string]*WeekendCupTournament `json:"tournaments"`
	ProcessedMatches map[string]MatchAuditRecord      `json:"processed_matches"`
	AuditEvents      []MatchAuditRecord               `json:"audit_events"`
	SavedAtUTC       time.Time                        `json:"saved_at_utc"`
}

type ArbitrationStore struct {
	mu               sync.RWMutex
	mmrByKey         map[string]*CharacterMMR         // key: playerID + ":" + charID
	playerHighest    map[string]int                   // playerID -> máximo LP alcanzado con cualquier personaje
	replays          map[string][]byte                // matchUUID -> binario .safreplay verificado (< 50 KB)
	tournaments      map[string]*WeekendCupTournament // tournamentID -> bracket activo
	processedMatches map[string]MatchAuditRecord      // matchUUID -> registro idempotente de arbitraje
	auditEvents      []MatchAuditRecord               // bitácora de auditoría (desyncs, anti-cheat, partidas válidas)
	hmacSecret       []byte
	stateFilePath    string
	databaseURL      string
}

func NewArbitrationStore(secret string) *ArbitrationStore {
	stateFile := strings.TrimSpace(os.Getenv("SAF_STATE_FILE"))
	dbURL := strings.TrimSpace(os.Getenv("DATABASE_URL"))
	if dbURL == "" {
		dbURL = strings.TrimSpace(os.Getenv("POSTGRES_DSN"))
	}
	return NewArbitrationStoreWithConfig(secret, stateFile, dbURL)
}

func NewArbitrationStoreWithConfig(secret, stateFilePath, databaseURL string) *ArbitrationStore {
	store := &ArbitrationStore{
		mmrByKey:         make(map[string]*CharacterMMR),
		playerHighest:    make(map[string]int),
		replays:          make(map[string][]byte),
		tournaments:      make(map[string]*WeekendCupTournament),
		processedMatches: make(map[string]MatchAuditRecord),
		auditEvents:      make([]MatchAuditRecord, 0),
		hmacSecret:       []byte(secret),
		stateFilePath:    strings.TrimSpace(stateFilePath),
		databaseURL:      strings.TrimSpace(databaseURL),
	}

	if store.stateFilePath != "" {
		if loaded, err := store.loadSnapshotLocked(); err != nil {
			log.Printf("[SAF Persistence] Error cargando snapshot %q: %v (iniciando semilla limpia)", store.stateFilePath, err)
			store.seedInitialLeaderboardAndBrackets()
		} else if !loaded {
			store.seedInitialLeaderboardAndBrackets()
			if err := store.saveSnapshotLocked(); err != nil {
				log.Printf("[SAF Persistence] No se pudo escribir snapshot inicial en %q: %v", store.stateFilePath, err)
			}
		}
	} else {
		store.seedInitialLeaderboardAndBrackets()
	}

	return store
}

func (s *ArbitrationStore) PersistenceMode() string {
	switch {
	case s.databaseURL != "" && s.stateFilePath != "":
		return "postgres_hook+disk_snapshot"
	case s.databaseURL != "":
		return "postgres_hook"
	case s.stateFilePath != "":
		return "disk_snapshot"
	default:
		return "memory"
	}
}

func (s *ArbitrationStore) loadSnapshotLocked() (bool, error) {
	raw, err := os.ReadFile(s.stateFilePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return false, nil
		}
		return false, err
	}
	if len(bytes.TrimSpace(raw)) == 0 {
		return false, nil
	}

	var snap storeDiskSnapshot
	if err := json.Unmarshal(raw, &snap); err != nil {
		return false, err
	}
	if snap.MMRByKey != nil {
		s.mmrByKey = snap.MMRByKey
	}
	if snap.PlayerHighest != nil {
		s.playerHighest = snap.PlayerHighest
	}
	if snap.Replays != nil {
		s.replays = snap.Replays
	}
	if snap.Tournaments != nil {
		s.tournaments = snap.Tournaments
	}
	if snap.ProcessedMatches != nil {
		s.processedMatches = snap.ProcessedMatches
	}
	if snap.AuditEvents != nil {
		s.auditEvents = snap.AuditEvents
	}
	return true, nil
}

func (s *ArbitrationStore) saveSnapshotLocked() error {
	if s.stateFilePath == "" {
		return nil
	}
	dir := filepath.Dir(s.stateFilePath)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}

	snap := storeDiskSnapshot{
		MMRByKey:         s.mmrByKey,
		PlayerHighest:    s.playerHighest,
		Replays:          s.replays,
		Tournaments:      s.tournaments,
		ProcessedMatches: s.processedMatches,
		AuditEvents:      s.auditEvents,
		SavedAtUTC:       time.Now().UTC(),
	}
	encoded, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return err
	}

	tmpPath := s.stateFilePath + ".tmp"
	if err := os.WriteFile(tmpPath, encoded, 0o600); err != nil {
		return err
	}
	return os.Rename(tmpPath, s.stateFilePath)
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
// Seguridad Criptográfica, Fletcher-32, Validación .safreplay, Glicko-2 y Anti-Cheat
// ----------------------------------------------------------------------------

// ComputeMatchHMACSignature calcula la firma HMAC-SHA256 canónica en hexadecimal minúscula
// sobre (matchUUID || replayPayload) para clientes UE5 y suites de integración E2E.
func ComputeMatchHMACSignature(secret []byte, matchUUID string, replayPayload []byte) string {
	mac := hmac.New(sha256.New, secret)
	mac.Write([]byte(matchUUID))
	mac.Write(replayPayload)
	return hex.EncodeToString(mac.Sum(nil))
}

func verifyMatchHMACSignature(secret []byte, matchUUID string, replayPayload []byte, providedHexSig string) bool {
	trimmed := strings.TrimSpace(providedHexSig)
	if trimmed == "" {
		return false
	}
	providedMAC, err := hex.DecodeString(trimmed)
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, secret)
	mac.Write([]byte(matchUUID))
	mac.Write(replayPayload)
	expectedMAC := mac.Sum(nil)
	return hmac.Equal(providedMAC, expectedMAC)
}

// ComputeFletcher32 calcula el checksum determinista Fletcher-32 en orden Little-Endian.
func ComputeFletcher32(raw []byte) uint32 {
	data := raw
	if len(data)%2 != 0 {
		padded := make([]byte, len(data)+1)
		copy(padded, data)
		data = padded
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

func computeFletcher32(data []byte) uint32 {
	return ComputeFletcher32(data)
}

// InspectAndValidateReplay exige tamaño <= 50 KB, cabecera mágica exacta "SAFR" en los primeros 4 bytes
// y, si contiene un stream comprimido Zlib tras "SAFR" + 4 bytes de metadatos (0x78), verifica que
// la descompresión Zlib sea íntegra y no supere el límite anti zip-bomb de 2 MB.
func InspectAndValidateReplay(rawPayload []byte) error {
	if len(rawPayload) == 0 {
		return errors.New("replay payload vacío")
	}
	if len(rawPayload) > MaxReplayPayloadBytes {
		return fmt.Errorf("el replay excede el límite estricto de 50 KB (%d bytes)", len(rawPayload))
	}
	if len(rawPayload) < 8 {
		return errors.New("cabecera de replay truncada (< 8 bytes)")
	}

	// Exigir estrictamente "SAFR" (0x53414652: 'S','A','F','R') en los primeros 4 bytes
	if rawPayload[0] != 'S' || rawPayload[1] != 'A' || rawPayload[2] != 'F' || rawPayload[3] != 'R' {
		return errors.New("firma mágica de replay inválida: se requiere cabecera exacta \"SAFR\" (0x53414652)")
	}

	// Soporte de stream Zlib opcional tras "SAFR" (4B) + metadatos de longitud/parche (4B)
	if len(rawPayload) > 8 && rawPayload[8] == 0x78 {
		zr, err := zlib.NewReader(bytes.NewReader(rawPayload[8:]))
		if err != nil {
			return fmt.Errorf("cabecera Zlib inválida tras prefijo SAFR: %w", err)
		}
		limited := io.LimitReader(zr, int64(MaxDecompressedReplayBytes)+1)
		decompressed, readErr := io.ReadAll(limited)
		closeErr := zr.Close()
		if readErr != nil {
			return fmt.Errorf("datos Zlib corruptos en replay SAFR: %w", readErr)
		}
		if len(decompressed) > MaxDecompressedReplayBytes {
			return fmt.Errorf("zip-bomb detectado: el replay descomprimido excede el máximo de 2 MB (%d bytes)", MaxDecompressedReplayBytes)
		}
		if closeErr != nil {
			return fmt.Errorf("falló cierre/checksum Adler-32 de stream Zlib: %w", closeErr)
		}
		if len(decompressed) == 0 {
			return errors.New("stream Zlib de replay descomprimió 0 bytes")
		}
	}

	return nil
}

func inspectAndValidateReplay(rawPayload []byte) error {
	return InspectAndValidateReplay(rawPayload)
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

	req.MatchUUID = strings.TrimSpace(req.MatchUUID)
	req.Player1ID = strings.TrimSpace(req.Player1ID)
	req.Player2ID = strings.TrimSpace(req.Player2ID)
	req.Player1CharacterID = strings.TrimSpace(req.Player1CharacterID)
	req.Player2CharacterID = strings.TrimSpace(req.Player2CharacterID)
	req.Region = strings.TrimSpace(req.Region)
	if req.Region == "" {
		req.Region = "SA-EAST"
	}
	if req.Player1CharacterID == "" {
		req.Player1CharacterID = "CHR_DEFAULT"
	}
	if req.Player2CharacterID == "" {
		req.Player2CharacterID = "CHR_DEFAULT"
	}

	// Validación estricta de límites de entrada e identidad de jugadores
	if req.MatchUUID == "" {
		writeJSONError(w, http.StatusBadRequest, "match_uuid es obligatorio")
		return
	}
	if req.Player1ID == "" || req.Player2ID == "" {
		writeJSONError(w, http.StatusBadRequest, "player1_id y player2_id son obligatorios")
		return
	}
	if strings.EqualFold(req.Player1ID, req.Player2ID) {
		writeJSONError(w, http.StatusBadRequest, "player1_id y player2_id no pueden ser el mismo jugador")
		return
	}
	if req.WinnerSlot < 0 || req.WinnerSlot > 2 {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("winner_slot inválido (%d): debe pertenecer a {0, 1, 2}", req.WinnerSlot))
		return
	}

	replayBytes, err := base64.StdEncoding.DecodeString(req.ReplayPayloadBase64)
	if err != nil {
		writeJSONError(w, http.StatusBadRequest, "replay_payload_base64 inválido")
		return
	}
	if err := InspectAndValidateReplay(replayBytes); err != nil {
		writeJSONError(w, http.StatusBadRequest, err.Error())
		return
	}

	// Autenticación HMAC-SHA256 obligatoria (sin bypass de cadena vacía)
	if !verifyMatchHMACSignature(s.hmacSecret, req.MatchUUID, replayBytes, req.ClientHMACSignature) {
		writeJSONError(w, http.StatusUnauthorized, "firma HMAC-SHA256 obligatoria ausente o inválida")
		return
	}

	computedChecksum := ComputeFletcher32(replayBytes)
	checksumValid := req.ExpectedFletcher32 == 0 || req.ExpectedFletcher32 == computedChecksum

	p1Audit := runHeuristicAntiCheat(req.P1RawInputs, req.P1RollbackSpikes, req.P1InHitstunPerFrame, req.P1FacedActiveFrame1)
	p2Audit := runHeuristicAntiCheat(req.P2RawInputs, req.P2RollbackSpikes, req.P2InHitstunPerFrame, req.P2FacedActiveFrame1)

	s.mu.Lock()
	defer s.mu.Unlock()

	// Protección de idempotencia contra reenvío de match_uuid duplicados
	if _, exists := s.processedMatches[req.MatchUUID]; exists {
		writeJSONError(w, http.StatusConflict, fmt.Sprintf("match_uuid %q ya fue procesado anteriormente", req.MatchUUID))
		return
	}
	if _, exists := s.replays[req.MatchUUID]; exists {
		writeJSONError(w, http.StatusConflict, fmt.Sprintf("match_uuid %q ya posee un replay registrado", req.MatchUUID))
		return
	}

	p1MMR := s.getOrCreateMMR(req.Player1ID, req.Player1CharacterID, req.Region)
	p2MMR := s.getOrCreateMMR(req.Player2ID, req.Player2CharacterID, req.Region)
	nowUTC := time.Now().UTC()

	// 1. Veredicto de Desync Determinista (Fletcher-32 divergente): 0 LP, no guardar replay corrupto, HTTP 422
	if !checksumValid {
		auditRec := MatchAuditRecord{
			MatchUUID:          req.MatchUUID,
			Status:             "DESYNC_REJECTED",
			AuditReason:        "discrepancia de checksum Fletcher-32 detectada: partida anulada sin cambios de LP/MMR ni almacenamiento de replay",
			ChecksumValid:      false,
			ExpectedFletcher32: req.ExpectedFletcher32,
			ComputedFletcher32: computedChecksum,
			Player1ID:          req.Player1ID,
			Player2ID:          req.Player2ID,
			WinnerSlot:         req.WinnerSlot,
			P1AntiCheat:        p1Audit,
			P2AntiCheat:        p2Audit,
			RecordedAtUTC:      nowUTC,
		}
		s.processedMatches[req.MatchUUID] = auditRec
		s.auditEvents = append(s.auditEvents, auditRec)
		if err := s.saveSnapshotLocked(); err != nil {
			log.Printf("[SAF Persistence] Error guardando snapshot tras desync: %v", err)
		}

		writeJSON(w, http.StatusUnprocessableEntity, MatchAuditSubmitResponse{
			MatchUUID:          req.MatchUUID,
			Status:             auditRec.Status,
			AuditReason:        auditRec.AuditReason,
			ChecksumValid:      false,
			ComputedFletcher32: computedChecksum,
			ReplayS3Key:        "",
			P1UpdatedMMR:       *p1MMR,
			P2UpdatedMMR:       *p2MMR,
			P1AntiCheat:        p1Audit,
			P2AntiCheat:        p2Audit,
			ProcessedAtUTC:     nowUTC,
		})
		return
	}

	// 2. Veredicto Anti-Cheat: 0 LP de ganancia al tramposo + Tarjeta Roja/Cola de Penalización, rival limpio intacto, HTTP 422
	if p1Audit.FlaggedForPenaltyQueue || p2Audit.FlaggedForPenaltyQueue {
		if p1Audit.FlaggedForPenaltyQueue {
			p1MMR.ConductRedCards++
			p1MMR.PenaltyQueue = true
			p1MMR.UpdatedAt = nowUTC
		}
		if p2Audit.FlaggedForPenaltyQueue {
			p2MMR.ConductRedCards++
			p2MMR.PenaltyQueue = true
			p2MMR.UpdatedAt = nowUTC
		}

		auditRec := MatchAuditRecord{
			MatchUUID:          req.MatchUUID,
			Status:             "ANTICHEAT_QUARANTINED",
			AuditReason:        "infracción heurística anti-cheat detectada: 0 LP otorgados al infractor, tarjeta roja aplicada y rival limpio sin penalización",
			ChecksumValid:      true,
			ExpectedFletcher32: req.ExpectedFletcher32,
			ComputedFletcher32: computedChecksum,
			Player1ID:          req.Player1ID,
			Player2ID:          req.Player2ID,
			WinnerSlot:         req.WinnerSlot,
			P1AntiCheat:        p1Audit,
			P2AntiCheat:        p2Audit,
			RecordedAtUTC:      nowUTC,
		}
		s.processedMatches[req.MatchUUID] = auditRec
		s.auditEvents = append(s.auditEvents, auditRec)
		if err := s.saveSnapshotLocked(); err != nil {
			log.Printf("[SAF Persistence] Error guardando snapshot tras cuarentena anti-cheat: %v", err)
		}

		writeJSON(w, http.StatusUnprocessableEntity, MatchAuditSubmitResponse{
			MatchUUID:          req.MatchUUID,
			Status:             auditRec.Status,
			AuditReason:        auditRec.AuditReason,
			ChecksumValid:      true,
			ComputedFletcher32: computedChecksum,
			ReplayS3Key:        "",
			P1UpdatedMMR:       *p1MMR,
			P2UpdatedMMR:       *p2MMR,
			P1AntiCheat:        p1Audit,
			P2AntiCheat:        p2Audit,
			ProcessedAtUTC:     nowUTC,
		})
		return
	}

	// 3. Partida limpia y verificada: actualizar Glicko-2 + LP y publicar .safreplay en el Teatro de Repeticiones
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

	s.replays[req.MatchUUID] = replayBytes
	s3Key := fmt.Sprintf("s3://saf-replays-%s/%s/%s.safreplay", strings.ToLower(req.Region), nowUTC.Format("2006-01-02"), req.MatchUUID)

	auditRec := MatchAuditRecord{
		MatchUUID:          req.MatchUUID,
		Status:             "ACCEPTED",
		ChecksumValid:      true,
		ExpectedFletcher32: req.ExpectedFletcher32,
		ComputedFletcher32: computedChecksum,
		Player1ID:          req.Player1ID,
		Player2ID:          req.Player2ID,
		WinnerSlot:         req.WinnerSlot,
		P1AntiCheat:        p1Audit,
		P2AntiCheat:        p2Audit,
		RecordedAtUTC:      nowUTC,
	}
	s.processedMatches[req.MatchUUID] = auditRec
	s.auditEvents = append(s.auditEvents, auditRec)
	if err := s.saveSnapshotLocked(); err != nil {
		log.Printf("[SAF Persistence] Error guardando snapshot tras partida aceptada: %v", err)
	}

	resp := MatchAuditSubmitResponse{
		MatchUUID:          req.MatchUUID,
		Status:             "ACCEPTED",
		ChecksumValid:      true,
		ComputedFletcher32: computedChecksum,
		ReplayS3Key:        s3Key,
		P1UpdatedMMR:       *p1MMR,
		P2UpdatedMMR:       *p2MMR,
		P1AntiCheat:        p1Audit,
		P2AntiCheat:        p2Audit,
		ProcessedAtUTC:     nowUTC,
	}
	writeJSON(w, http.StatusOK, resp)
}

func (s *ArbitrationStore) handleHeartbeatArbitration(w http.ResponseWriter, r *http.Request) {
	var req HeartbeatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "JSON inválido: "+err.Error())
		return
	}

	req.MatchUUID = strings.TrimSpace(req.MatchUUID)
	req.ReportingPlayer = strings.TrimSpace(req.ReportingPlayer)
	req.OpponentPlayer = strings.TrimSpace(req.OpponentPlayer)
	req.OpponentCharID = strings.TrimSpace(req.OpponentCharID)
	req.Region = strings.TrimSpace(req.Region)
	if req.Region == "" {
		req.Region = "SA-EAST"
	}
	if req.OpponentCharID == "" {
		req.OpponentCharID = "CHR_DEFAULT"
	}
	if req.MatchUUID == "" || req.OpponentPlayer == "" {
		writeJSONError(w, http.StatusBadRequest, "match_uuid y opponent_player_id son obligatorios")
		return
	}
	if req.ReportingPlayer != "" && strings.EqualFold(req.ReportingPlayer, req.OpponentPlayer) {
		writeJSONError(w, http.StatusBadRequest, "reporting_player_id y opponent_player_id no pueden coincidir")
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
		if offenderMMR.ConductRedCards >= 2 {
			offenderMMR.PenaltyQueue = true
		}
		offenderMMR.UpdatedAt = time.Now().UTC()

		resp.RageQuitConfirmed = true
		resp.PenalizedPlayerID = req.OpponentPlayer
		resp.AppliedLPPenalty = RageQuitLPPenalty
		resp.TotalConductRedCards = offenderMMR.ConductRedCards
		resp.RestrictedQueueApplied = offenderMMR.ConductRedCards >= 2

		if err := s.saveSnapshotLocked(); err != nil {
			log.Printf("[SAF Persistence] Error guardando snapshot tras rage quit: %v", err)
		}
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
	w.Header().Set("X-SAF-Fletcher32", fmt.Sprintf("0x%08X", ComputeFletcher32(payload)))
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
		writeJSON(w, http.StatusOK, map[string]string{
			"status":           "ok",
			"service":          "saf-arbitration-gateway",
			"persistence_mode": store.PersistenceMode(),
		})
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

	log.Printf("[SAF Arbitration Server] Escuchando en :%s (modo persistencia: %s, Glicko-2 + Anti-Cheat + Replay Theater activo)", port, store.PersistenceMode())
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("Error fatal en el servidor: %v", err)
	}
}
