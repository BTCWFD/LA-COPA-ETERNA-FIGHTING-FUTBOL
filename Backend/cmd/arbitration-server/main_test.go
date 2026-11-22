// main_test.go - Suite de Pruebas Unitarias e Integración del Servidor de Arbitraje eSports
// Cubre: Glicko-2 + Piso Anti-Smurfing, Validación .safreplay, Checksum Fletcher-32,
// Rechazo de Desync/HMAC, Motor Heurístico Anti-Cheat y Arbitraje de Rage Quit.
package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func buildValidSAFRPayload(totalFrames uint32, finalChecksum uint32) []byte {
	buf := new(bytes.Buffer)
	_ = binary.Write(buf, binary.LittleEndian, ReplayMagicSAFR) // 0x53414652 "SAFR"
	_ = binary.Write(buf, binary.LittleEndian, uint16(104))     // BalancePatchVersion
	buf.Write(make([]byte, 16))                                 // MatchUUID (16 bytes)
	_ = binary.Write(buf, binary.LittleEndian, uint64(19301950))
	buf.WriteByte(0) // P1 Character
	buf.WriteByte(1) // P2 Character
	buf.WriteByte(0) // Stage
	_ = binary.Write(buf, binary.LittleEndian, totalFrames)
	_ = binary.Write(buf, binary.LittleEndian, finalChecksum)
	// Agregar 4 runs RLE (5 bytes cada uno)
	for i := 0; i < 4; i++ {
		_ = binary.Write(buf, binary.LittleEndian, uint16(0x0008))
		_ = binary.Write(buf, binary.LittleEndian, uint16(0x0004))
		buf.WriteByte(60)
	}
	return buf.Bytes()
}

func TestGlicko2RatingUpdateAndAntiSmurfFloor(t *testing.T) {
	store := NewArbitrationStore("TEST_SECRET_KEY")

	p1 := store.getOrCreateMMR("PLAYER_A", "FENOMENO_BR", "SA-EAST")
	p2 := store.getOrCreateMMR("PLAYER_B", "CANON_AR", "SA-EAST")

	initialP1Rating := p1.GlickoRating
	initialP1RD := p1.GlickoRD
	initialP1LP := p1.LeaguePoints

	updateGlicko2(p1, p2.GlickoRating, p2.GlickoRD, 1.0, 1000)
	updateGlicko2(p2, initialP1Rating, initialP1RD, 0.0, 1000)

	if p1.GlickoRating <= initialP1Rating {
		t.Fatalf("se esperaba incremento en GlickoRating tras victoria: previo=%.2f, actual=%.2f", initialP1Rating, p1.GlickoRating)
	}
	if p1.GlickoRD >= initialP1RD {
		t.Fatalf("se esperaba reducción de incertidumbre (RD) tras partida: previo=%.2f, actual=%.2f", initialP1RD, p1.GlickoRD)
	}
	if p1.LeaguePoints <= initialP1LP {
		t.Fatalf("se esperaba incremento de LP tras victoria: previo=%d, actual=%d", initialP1LP, p1.LeaguePoints)
	}
	if p2.GlickoRating >= 1500.0 {
		t.Fatalf("se esperaba descenso de GlickoRating tras derrota: actual=%.2f", p2.GlickoRating)
	}

	// Verificar Piso Anti-Smurfing (15,000 LP) para cuenta en Copa Continental (>= 25,000 LP)
	store.playerHighest["CONMEBOL-PRO-001"] = 27450
	secondaryChar := store.getOrCreateMMR("CONMEBOL-PRO-001", "PISTOLERO_UY", "SA-EAST")
	if secondaryChar.LeaguePoints != ContinentalCupFloorLP {
		t.Fatalf("piso anti-smurfing falló al crear personaje secundario: esperado=%d, obtenido=%d",
			ContinentalCupFloorLP, secondaryChar.LeaguePoints)
	}

	// Incluso tras una derrota en el piso de 15,000 LP, no debe caer por debajo de 15,000 LP
	updateGlicko2(secondaryChar, 1500.0, 150.0, 0.0, store.playerHighest["CONMEBOL-PRO-001"])
	if secondaryChar.LeaguePoints < ContinentalCupFloorLP {
		t.Fatalf("piso anti-smurfing violado tras derrota: esperado >= %d, obtenido=%d",
			ContinentalCupFloorLP, secondaryChar.LeaguePoints)
	}
}

func TestInspectAndValidateReplay(t *testing.T) {
	validReplay := buildValidSAFRPayload(240, 0xCAFEBABE)
	if err := inspectAndValidateReplay(validReplay); err != nil {
		t.Fatalf("un replay SAFR válido fue rechazado: %v", err)
	}

	// 1. Payload vacío
	if err := inspectAndValidateReplay(nil); err == nil {
		t.Fatal("se esperaba error con payload vacío")
	}

	// 2. Payload truncado (< 8 bytes)
	if err := inspectAndValidateReplay([]byte{0x52, 0x46, 0x41, 0x53}); err == nil {
		t.Fatal("se esperaba error con cabecera truncada (< 8 bytes)")
	}

	// 3. Prefijo inválido (0x00000000)
	invalidPrefix := make([]byte, 16)
	if err := inspectAndValidateReplay(invalidPrefix); err == nil {
		t.Fatal("se esperaba error con prefijo nulo inválido")
	}

	// 4. Payload que excede el límite estricto de 50 KB
	oversized := make([]byte, MaxReplayPayloadBytes+1)
	binary.LittleEndian.PutUint32(oversized[0:4], ReplayMagicSAFR)
	if err := inspectAndValidateReplay(oversized); err == nil {
		t.Fatal("se esperaba error cuando el replay supera los 50 KB")
	}
}

func TestFletcher32DeterminismAndSingleBitDesync(t *testing.T) {
	payloadA := buildValidSAFRPayload(600, 0x12345678)
	payloadB := buildValidSAFRPayload(600, 0x12345678)

	hashA := computeFletcher32(payloadA)
	hashB := computeFletcher32(payloadB)
	if hashA == 0 || hashA != hashB {
		t.Fatalf("Fletcher-32 no es determinista: hashA=0x%08X, hashB=0x%08X", hashA, hashB)
	}

	// Invertir 1 solo bit en el flujo RLE y comprobar divergencia inmediata de Fletcher-32
	payloadB[len(payloadB)-1] ^= 0x01
	hashCorrupted := computeFletcher32(payloadB)
	if hashA == hashCorrupted {
		t.Fatalf("colisión en Fletcher-32 tras alterar 1 bit: 0x%08X", hashA)
	}
}

func TestHeuristicAntiCheatDetections(t *testing.T) {
	const frames = 240
	inputs := make([]uint16, frames)
	rollbackSpikes := make([]uint8, frames)
	inHitstun := make([]bool, frames)
	facedActiveFrame1 := make([]bool, frames)

	// 1. Inyectar macro perfecto con duración idéntica de 2 frames en cada dirección (varianza = 0.0)
	dirs := []uint16{0x0002, 0x000A, 0x0008, 0x0000} // QCF 2 -> 3 -> 6 -> 5 exacto cada 2 frames
	for i := 0; i < frames; i++ {
		inputs[i] = dirs[(i/2)%len(dirs)]
	}

	// 2. Inyectar Auto-Parry en Frame 1 sin buffering previo en 12 ataques enemigos
	for atk := 0; atk < 12; atk++ {
		frameIdx := 10 + atk*15
		facedActiveFrame1[frameIdx] = true
		inputs[frameIdx-1] &^= InputBitGambeta
		inputs[frameIdx-2] &^= InputBitGambeta
		inputs[frameIdx-3] &^= InputBitGambeta
		inputs[frameIdx] |= InputBitGambeta
	}

	// 3. Inyectar Lag Switch asimétrico: 10 picos de rollback (>= 5 frames) todos durante Hitstun
	for spike := 0; spike < 10; spike++ {
		f := 20 + spike*10
		rollbackSpikes[f] = 7
		inHitstun[f] = true
	}

	report := runHeuristicAntiCheat(inputs, rollbackSpikes, inHitstun, facedActiveFrame1)

	if !report.SuspectedMacroScript {
		t.Fatalf("el motor Anti-Cheat no detectó el script de Macro con varianza=%.6f", report.InputTimingVariance)
	}
	if !report.SuspectedAutoParryBot {
		t.Fatalf("el motor Anti-Cheat no detectó Auto-Parry Bot (rate=%.2f)", report.AutoParryFrame1Rate)
	}
	if !report.SuspectedLagSwitch {
		t.Fatalf("el motor Anti-Cheat no detectó Lag Switch asimétrico (rate=%.2f)", report.LagDuringEnemyComboRate)
	}
	if !report.FlaggedForPenaltyQueue {
		t.Fatal("el jugador infractor debía quedar marcado para FlaggedForPenaltyQueue")
	}
}

func TestHTTPSubmitDesyncDetectionAndRageQuitArbitration(t *testing.T) {
	secret := "UNIT_TEST_CONMEBOL_HMAC_2026"
	store := NewArbitrationStore(secret)
	router := BuildRouter(store)

	replayPayload := buildValidSAFRPayload(300, 0xAABBCCDD)
	actualFletcher := computeFletcher32(replayPayload)
	matchID := "match-uuid-copa-eterna-001"

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(matchID))
	mac.Write(replayPayload)
	validHMAC := hex.EncodeToString(mac.Sum(nil))

	// Caso A: Envío con Checksum Fletcher-32 divergente (Desync detectado)
	submitReq := MatchAuditSubmitRequest{
		MatchUUID:           matchID,
		Region:              "SA-EAST",
		PatchVersion:        104,
		Player1ID:           "P1_TEST",
		Player2ID:           "P2_TEST",
		Player1CharacterID:  "FENOMENO_BR",
		Player2CharacterID:  "CANON_AR",
		StageID:             "STAGE_BOMBONERA",
		WinnerSlot:          1,
		ExpectedFletcher32:  actualFletcher ^ 0x0000FFFF, // Checksum alterado (Desync)
		ClientHMACSignature: validHMAC,
		ReplayPayloadBase64: base64.StdEncoding.EncodeToString(replayPayload),
	}
	bodyBytes, _ := json.Marshal(submitReq)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/matches/audit-and-submit", bytes.NewReader(bodyBytes))
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status inesperado en audit-and-submit: %d (%s)", rec.Code, rec.Body.String())
	}
	var submitResp MatchAuditSubmitResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &submitResp); err != nil {
		t.Fatalf("error decodificando respuesta: %v", err)
	}
	if submitResp.ChecksumValid {
		t.Fatal("se esperaba ChecksumValid=false ante una discrepancia de Fletcher-32 (Desync)")
	}

	// Caso B: Firma HMAC inválida debe ser rechazada con 401 Unauthorized
	submitReq.ClientHMACSignature = "deadbeef00112233445566778899aabbccddeeff00112233445566778899aabb"
	badBody, _ := json.Marshal(submitReq)
	badReq := httptest.NewRequest(http.MethodPost, "/api/v1/matches/audit-and-submit", bytes.NewReader(badBody))
	badRec := httptest.NewRecorder()
	router.ServeHTTP(badRec, badReq)
	if badRec.Code != http.StatusUnauthorized {
		t.Fatalf("se esperaba HTTP 401 ante firma HMAC inválida, obtenido: %d", badRec.Code)
	}

	// Caso C: Descarga del replay desde el Teatro de Repeticiones y verificación de cabecera X-SAF-Fletcher32
	dlReq := httptest.NewRequest(http.MethodGet, "/api/v1/replays/"+matchID, nil)
	dlRec := httptest.NewRecorder()
	router.ServeHTTP(dlRec, dlReq)
	if dlRec.Code != http.StatusOK {
		t.Fatalf("error descargando replay almacenado: HTTP %d", dlRec.Code)
	}
	if !bytes.Equal(dlRec.Body.Bytes(), replayPayload) {
		t.Fatal("el binario descargado del Teatro de Repeticiones no coincide bit a bit con el subido")
	}

	// Caso D: Arbitraje de Rage Quit (2 desconexiones >= 4.0s -> -160 LP acumulados y Cola Restringida)
	hbPayload := HeartbeatRequest{
		MatchUUID:       matchID,
		ReportingPlayer: "P1_TEST",
		OpponentPlayer:  "P2_RAGEQUITTER",
		OpponentCharID:  "LOCO_CO",
		Region:          "SA-EAST",
		CurrentFrame:    1420,
		SilenceSeconds:  4.5,
		OpponentInCombo: true,
	}
	hbBytes, _ := json.Marshal(hbPayload)

	for attempt := 1; attempt <= 2; attempt++ {
		hbReq := httptest.NewRequest(http.MethodPost, "/api/v1/matches/heartbeat", bytes.NewReader(hbBytes))
		hbRec := httptest.NewRecorder()
		router.ServeHTTP(hbRec, hbReq)
		if hbRec.Code != http.StatusOK {
			t.Fatalf("status inesperado en heartbeat: %d", hbRec.Code)
		}
		var hbResp HeartbeatResponse
		_ = json.Unmarshal(hbRec.Body.Bytes(), &hbResp)
		if !hbResp.RageQuitConfirmed || hbResp.AppliedLPPenalty != RageQuitLPPenalty {
			t.Fatalf("el arbitraje de Rage Quit no aplicó la penalización de -80 LP en intento #%d", attempt)
		}
		if attempt == 2 && !hbResp.RestrictedQueueApplied {
			t.Fatal("tras 2 Tarjetas Rojas de Conducta se debía activar RestrictedQueueApplied=true")
		}
	}
}
