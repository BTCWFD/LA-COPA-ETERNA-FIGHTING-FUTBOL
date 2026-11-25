// main_test.go - Suite de Pruebas Unitarias, Seguridad Adversarial y Persistencia del Servidor de Arbitraje eSports
// Cubre: Glicko-2 + Piso Anti-Smurfing, Cabecera mágica exacta "SAFR" + Zlib / Anti-ZipBomb,
// Autenticación HMAC-SHA256 obligatoria, Rechazo de Desync (422 + 0 LP), Veredictos Anti-Cheat (422 + 0 LP gain),
// Idempotencia (409 Conflict), Validación de Límites (400 Bad Request), Rage Quit y Persistencia en Disco (SAF_STATE_FILE).
package main

import (
	"bytes"
	"compress/zlib"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func buildValidSAFRPayload(totalFrames uint32, finalChecksum uint32) []byte {
	buf := new(bytes.Buffer)
	buf.Write([]byte("SAFR"))                                // Exact ASCII magic header "SAFR" (0x53414652)
	_ = binary.Write(buf, binary.LittleEndian, uint16(104))  // BalancePatchVersion
	buf.Write(make([]byte, 16))                              // MatchUUID (16 bytes)
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

func buildZlibCompressedSAFRPayload(totalFrames uint32, finalChecksum uint32) []byte {
	inner := buildValidSAFRPayload(totalFrames, finalChecksum)
	var compressedBuf bytes.Buffer
	zw, _ := zlib.NewWriterLevel(&compressedBuf, zlib.DefaultCompression) // Emite cabecera Zlib 0x78 0x9C
	_, _ = zw.Write(inner)
	_ = zw.Close()

	out := new(bytes.Buffer)
	out.Write([]byte("SAFR"))
	_ = binary.Write(out, binary.LittleEndian, int32(len(inner))) // 4-byte metadata (UncompressedSize)
	out.Write(compressedBuf.Bytes())
	return out.Bytes()
}

func buildCheaterTelemetry(frames int) ([]uint16, []uint8, []bool, []bool) {
	inputs := make([]uint16, frames)
	rollbackSpikes := make([]uint8, frames)
	inHitstun := make([]bool, frames)
	facedActiveFrame1 := make([]bool, frames)

	// 1. Macro perfecto con duración idéntica de 2 frames por dirección (varianza = 0.0)
	dirs := []uint16{0x0002, 0x000A, 0x0008, 0x0000}
	for i := 0; i < frames; i++ {
		inputs[i] = dirs[(i/2)%len(dirs)]
	}
	// 2. Auto-Parry en Frame 1 sin buffering previo en 12 ataques enemigos
	for atk := 0; atk < 12; atk++ {
		frameIdx := 10 + atk*15
		facedActiveFrame1[frameIdx] = true
		inputs[frameIdx-1] &^= InputBitGambeta
		inputs[frameIdx-2] &^= InputBitGambeta
		inputs[frameIdx-3] &^= InputBitGambeta
		inputs[frameIdx] |= InputBitGambeta
	}
	// 3. Lag Switch asimétrico: 10 picos de rollback (>= 5 frames) todos durante Hitstun
	for spike := 0; spike < 10; spike++ {
		f := 20 + spike*10
		rollbackSpikes[f] = 7
		inHitstun[f] = true
	}
	return inputs, rollbackSpikes, inHitstun, facedActiveFrame1
}

func TestGlicko2RatingUpdateAndAntiSmurfFloor(t *testing.T) {
	store := NewArbitrationStoreWithConfig("TEST_SECRET_KEY", "", "")

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

func TestInspectAndValidateReplayStrictMagicAndZlib(t *testing.T) {
	// 1. Replay SAFR sin comprimir válido
	validReplay := buildValidSAFRPayload(240, 0xCAFEBABE)
	if err := InspectAndValidateReplay(validReplay); err != nil {
		t.Fatalf("un replay SAFR válido fue rechazado: %v", err)
	}

	// 2. Replay SAFR comprimido con Zlib válido (cabecera 0x78 tras SAFR + 4B metadata)
	validZlibReplay := buildZlibCompressedSAFRPayload(360, 0x11223344)
	if validZlibReplay[8] != 0x78 {
		t.Fatalf("se esperaba cabecera Zlib 0x78 en byte 8, obtenido 0x%02X", validZlibReplay[8])
	}
	if err := InspectAndValidateReplay(validZlibReplay); err != nil {
		t.Fatalf("un replay SAFR+Zlib válido fue rechazado: %v", err)
	}

	// 3. Payload vacío
	if err := InspectAndValidateReplay(nil); err == nil {
		t.Fatal("se esperaba error con payload vacío")
	}

	// 4. Payload truncado (< 8 bytes)
	if err := InspectAndValidateReplay([]byte("SAFR")); err == nil {
		t.Fatal("se esperaba error con cabecera truncada (< 8 bytes)")
	}

	// 5. Rechazo estricto de 0xDEADBEEF (tanto BigEndian como LittleEndian) y nulos
	deadbeefBE := []byte{0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}
	if err := InspectAndValidateReplay(deadbeefBE); err == nil {
		t.Fatal("se esperaba rechazo estricto ante prefijo 0xDEADBEEF BigEndian")
	}
	deadbeefLE := []byte{0xEF, 0xBE, 0xAD, 0xDE, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}
	if err := InspectAndValidateReplay(deadbeefLE); err == nil {
		t.Fatal("se esperaba rechazo estricto ante prefijo 0xDEADBEEF LittleEndian")
	}
	if err := InspectAndValidateReplay(make([]byte, 16)); err == nil {
		t.Fatal("se esperaba error con prefijo nulo inválido")
	}

	// 6. Stream Zlib corrupto tras SAFR + 4B metadata
	corruptZlib := []byte{'S', 'A', 'F', 'R', 0x40, 0x00, 0x00, 0x00, 0x78, 0x9C, 0xFF, 0xFF, 0x00, 0x01}
	if err := InspectAndValidateReplay(corruptZlib); err == nil {
		t.Fatal("se esperaba rechazo ante stream Zlib corrupto")
	}

	// 7. Protección Anti Zip-Bomb (> 2 MB descomprimidos dentro de un paquete comprimido < 50 KB)
	var bombCompressed bytes.Buffer
	zw, _ := zlib.NewWriterLevel(&bombCompressed, zlib.BestCompression)
	_, _ = zw.Write(make([]byte, MaxDecompressedReplayBytes+64*1024)) // ~2.06 MB de ceros -> ~2.1 KB en Zlib
	_ = zw.Close()

	var bombPayload bytes.Buffer
	bombPayload.Write([]byte("SAFR"))
	_ = binary.Write(&bombPayload, binary.LittleEndian, int32(MaxDecompressedReplayBytes+64*1024))
	bombPayload.Write(bombCompressed.Bytes())
	if bombPayload.Len() >= MaxReplayPayloadBytes {
		t.Fatalf("el zip-bomb de prueba debía medir < 50 KB comprimido, midió %d bytes", bombPayload.Len())
	}
	if err := InspectAndValidateReplay(bombPayload.Bytes()); err == nil {
		t.Fatal("se esperaba rechazo anti zip-bomb cuando el stream Zlib supera 2 MB")
	}

	// 8. Payload comprimido que excede el límite estricto de 50 KB en tránsito
	oversized := make([]byte, MaxReplayPayloadBytes+1)
	copy(oversized[0:4], []byte("SAFR"))
	if err := InspectAndValidateReplay(oversized); err == nil {
		t.Fatal("se esperaba error cuando el replay supera los 50 KB")
	}
}

func TestFletcher32DeterminismAndSingleBitDesync(t *testing.T) {
	payloadA := buildValidSAFRPayload(600, 0x12345678)
	payloadB := buildValidSAFRPayload(600, 0x12345678)

	hashA := ComputeFletcher32(payloadA)
	hashB := ComputeFletcher32(payloadB)
	if hashA == 0 || hashA != hashB {
		t.Fatalf("Fletcher-32 no es determinista: hashA=0x%08X, hashB=0x%08X", hashA, hashB)
	}

	// Invertir 1 solo bit en el flujo RLE y comprobar divergencia inmediata de Fletcher-32
	payloadB[len(payloadB)-1] ^= 0x01
	hashCorrupted := ComputeFletcher32(payloadB)
	if hashA == hashCorrupted {
		t.Fatalf("colisión en Fletcher-32 tras alterar 1 bit: 0x%08X", hashA)
	}
}

func TestHeuristicAntiCheatDetections(t *testing.T) {
	inputs, rollbackSpikes, inHitstun, facedActiveFrame1 := buildCheaterTelemetry(240)
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

func postJSON(router http.Handler, path string, body any) *httptest.ResponseRecorder {
	raw, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, path, bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	return rec
}

func TestHappyPathSubmitReplayDownloadAndLeaderboard(t *testing.T) {
	secret := "UNIT_TEST_CONMEBOL_HMAC_2026"
	store := NewArbitrationStoreWithConfig(secret, "", "")
	router := BuildRouter(store)

	replayPayload := buildZlibCompressedSAFRPayload(360, 0xAABBCCDD)
	fletcher := ComputeFletcher32(replayPayload)
	matchID := "match-happy-path-001"
	sig := ComputeMatchHMACSignature([]byte(secret), matchID, replayPayload)

	submitReq := MatchAuditSubmitRequest{
		MatchUUID:           matchID,
		Region:              "SA-EAST",
		PatchVersion:        104,
		Player1ID:           "P1_CLEAN",
		Player2ID:           "P2_CLEAN",
		Player1CharacterID:  "FENOMENO_BR",
		Player2CharacterID:  "CANON_AR",
		StageID:             "STAGE_BOMBONERA",
		WinnerSlot:          1,
		ExpectedFletcher32:  fletcher,
		ClientHMACSignature: sig,
		ReplayPayloadBase64: base64.StdEncoding.EncodeToString(replayPayload),
	}

	rec := postJSON(router, "/api/v1/matches/audit-and-submit", submitReq)
	if rec.Code != http.StatusOK {
		t.Fatalf("se esperaba HTTP 200 en partida limpia, obtenido %d: %s", rec.Code, rec.Body.String())
	}

	var resp MatchAuditSubmitResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("error decodificando respuesta: %v", err)
	}
	if !resp.ChecksumValid || resp.Status != "ACCEPTED" {
		t.Fatalf("respuesta inesperada en partida limpia: %+v", resp)
	}
	if resp.P1UpdatedMMR.LeaguePoints <= 1000 {
		t.Fatalf("P1 ganador debía ganar LP (> 1000), obtuvo %d", resp.P1UpdatedMMR.LeaguePoints)
	}
	if resp.P2UpdatedMMR.LeaguePoints >= 1000 {
		t.Fatalf("P2 perdedor debía perder LP (< 1000), obtuvo %d", resp.P2UpdatedMMR.LeaguePoints)
	}

	// Descarga del replay verificado desde el Teatro de Repeticiones
	dlReq := httptest.NewRequest(http.MethodGet, "/api/v1/replays/"+matchID, nil)
	dlRec := httptest.NewRecorder()
	router.ServeHTTP(dlRec, dlReq)
	if dlRec.Code != http.StatusOK {
		t.Fatalf("error descargando replay válido: HTTP %d", dlRec.Code)
	}
	if !bytes.Equal(dlRec.Body.Bytes(), replayPayload) {
		t.Fatal("el binario descargado no coincide bit a bit con el subido")
	}
}

func TestAdversarialSecurityAndIntegrityCases(t *testing.T) {
	secret := "ADVERSARIAL_CONMEBOL_SECRET_2026"
	store := NewArbitrationStoreWithConfig(secret, "", "")
	router := BuildRouter(store)

	validReplay := buildValidSAFRPayload(300, 0xCAFE1234)
	validFletcher := ComputeFletcher32(validReplay)
	validB64 := base64.StdEncoding.EncodeToString(validReplay)

	// -------------------------------------------------------------------------
	// Caso 1: HMAC vacío -> HTTP 401 Unauthorized (sin bypass!)
	// -------------------------------------------------------------------------
	t.Run("EmptyHMAC_Returns401", func(t *testing.T) {
		rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           "match-empty-hmac",
			Player1ID:           "P1_AUTH",
			Player2ID:           "P2_AUTH",
			WinnerSlot:          1,
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: "", // Bypass eliminado
			ReplayPayloadBase64: validB64,
		})
		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("HMAC vacío debía retornar HTTP 401, obtenido %d (%s)", rec.Code, rec.Body.String())
		}
	})

	// -------------------------------------------------------------------------
	// Caso 2: HMAC inválido -> HTTP 401 Unauthorized
	// -------------------------------------------------------------------------
	t.Run("InvalidHMAC_Returns401", func(t *testing.T) {
		rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           "match-bad-hmac",
			Player1ID:           "P1_AUTH",
			Player2ID:           "P2_AUTH",
			WinnerSlot:          1,
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: strings.Repeat("ab", 32),
			ReplayPayloadBase64: validB64,
		})
		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("HMAC inválido debía retornar HTTP 401, obtenido %d", rec.Code)
		}
	})

	// -------------------------------------------------------------------------
	// Caso 3: Payload 0xDEADBEEF (sin cabecera SAFR) -> HTTP 400 Bad Request
	// -------------------------------------------------------------------------
	t.Run("DeadbeefMagicHeader_Returns400", func(t *testing.T) {
		deadbeef := []byte{0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07}
		matchID := "match-deadbeef-001"
		sig := ComputeMatchHMACSignature([]byte(secret), matchID, deadbeef)

		rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "P1_MAGIC",
			Player2ID:           "P2_MAGIC",
			WinnerSlot:          1,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: base64.StdEncoding.EncodeToString(deadbeef),
		})
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("payload 0xDEADBEEF debía retornar HTTP 400, obtenido %d (%s)", rec.Code, rec.Body.String())
		}
	})

	// -------------------------------------------------------------------------
	// Caso 4: Desync Fletcher-32 -> HTTP 422, checksum_valid=false, 0 LP y replay no almacenado
	// -------------------------------------------------------------------------
	t.Run("Fletcher32Desync_Returns422AndZeroLPChange", func(t *testing.T) {
		matchID := "match-desync-422"
		sig := ComputeMatchHMACSignature([]byte(secret), matchID, validReplay)

		rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "P1_DESYNC",
			Player2ID:           "P2_DESYNC",
			Player1CharacterID:  "CHR_EL_DIEZ",
			Player2CharacterID:  "CHR_O_REI",
			WinnerSlot:          1,
			ExpectedFletcher32:  validFletcher ^ 0x0000FFFF,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: validB64,
		})
		if rec.Code != http.StatusUnprocessableEntity {
			t.Fatalf("desync Fletcher-32 debía retornar HTTP 422, obtenido %d (%s)", rec.Code, rec.Body.String())
		}

		var resp MatchAuditSubmitResponse
		if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
			t.Fatalf("error decodificando respuesta 422 de desync: %v", err)
		}
		if resp.ChecksumValid {
			t.Fatal("se esperaba checksum_valid=false en desync")
		}
		if resp.P1UpdatedMMR.LeaguePoints != 1000 || resp.P2UpdatedMMR.LeaguePoints != 1000 {
			t.Fatalf("no se debía modificar LP ante desync: P1=%d, P2=%d", resp.P1UpdatedMMR.LeaguePoints, resp.P2UpdatedMMR.LeaguePoints)
		}

		// Verificar que el replay corrupto NO fue publicado en el Teatro de Repeticiones
		dlReq := httptest.NewRequest(http.MethodGet, "/api/v1/replays/"+matchID, nil)
		dlRec := httptest.NewRecorder()
		router.ServeHTTP(dlRec, dlReq)
		if dlRec.Code != http.StatusNotFound {
			t.Fatalf("el replay con desync no debía guardarse como válido (esperado 404, obtenido %d)", dlRec.Code)
		}
	})

	// -------------------------------------------------------------------------
	// Caso 5: Jugador Tramposo -> HTTP 422, cuarentena + tarjeta roja, 0 LP gain al tramposo y rival intacto
	// -------------------------------------------------------------------------
	t.Run("CheaterFlagged_Returns422ZeroLPGainAndCleanOpponentUnpenalized", func(t *testing.T) {
		matchID := "match-cheater-422"
		sig := ComputeMatchHMACSignature([]byte(secret), matchID, validReplay)
		cheatInputs, cheatSpikes, cheatHitstun, cheatFrame1 := buildCheaterTelemetry(240)

		rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "P1_CHEATER",
			Player2ID:           "P2_HONEST_VICTIM",
			Player1CharacterID:  "CHR_EL_DIEZ",
			Player2CharacterID:  "CHR_O_REI",
			WinnerSlot:          1, // Tramposo reclama victoria
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: validB64,
			P1RawInputs:         cheatInputs,
			P1RollbackSpikes:    cheatSpikes,
			P1InHitstunPerFrame: cheatHitstun,
			P1FacedActiveFrame1: cheatFrame1,
		})
		if rec.Code != http.StatusUnprocessableEntity {
			t.Fatalf("partida con trampa detectada debía retornar HTTP 422, obtenido %d (%s)", rec.Code, rec.Body.String())
		}

		var resp MatchAuditSubmitResponse
		if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
			t.Fatalf("error decodificando respuesta 422 anti-cheat: %v", err)
		}
		if resp.Status != "ANTICHEAT_QUARANTINED" {
			t.Fatalf("se esperaba status ANTICHEAT_QUARANTINED, obtenido %q", resp.Status)
		}
		if !resp.P1AntiCheat.FlaggedForPenaltyQueue {
			t.Fatal("P1 debía estar marcado con FlaggedForPenaltyQueue=true")
		}
		if resp.P1UpdatedMMR.LeaguePoints != 1000 {
			t.Fatalf("tramposo debía obtener 0 LP de ganancia (permanecer en 1000), obtuvo %d", resp.P1UpdatedMMR.LeaguePoints)
		}
		if resp.P1UpdatedMMR.ConductRedCards < 1 || !resp.P1UpdatedMMR.PenaltyQueue {
			t.Fatalf("tramposo debía recibir tarjeta roja y penalty_queue=true: %+v", resp.P1UpdatedMMR)
		}
		if resp.P2UpdatedMMR.LeaguePoints != 1000 {
			t.Fatalf("el rival limpio no debía sufrir pérdida de LP (esperado 1000, obtenido %d)", resp.P2UpdatedMMR.LeaguePoints)
		}
	})

	// -------------------------------------------------------------------------
	// Caso 6: Idempotencia — match_uuid duplicado -> HTTP 409 Conflict
	// -------------------------------------------------------------------------
	t.Run("DuplicateMatchUUID_Returns409Conflict", func(t *testing.T) {
		matchID := "match-idempotent-001"
		sig := ComputeMatchHMACSignature([]byte(secret), matchID, validReplay)
		payload := MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "P1_IDEM",
			Player2ID:           "P2_IDEM",
			WinnerSlot:          2,
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: validB64,
		}

		firstRec := postJSON(router, "/api/v1/matches/audit-and-submit", payload)
		if firstRec.Code != http.StatusOK {
			t.Fatalf("primer envío válido debía retornar HTTP 200, obtenido %d", firstRec.Code)
		}

		secondRec := postJSON(router, "/api/v1/matches/audit-and-submit", payload)
		if secondRec.Code != http.StatusConflict {
			t.Fatalf("reenvío duplicado de match_uuid debía retornar HTTP 409 Conflict, obtenido %d (%s)", secondRec.Code, secondRec.Body.String())
		}
	})

	// -------------------------------------------------------------------------
	// Caso 7: winner_slot fuera de rango (winner_slot=99 y -1) -> HTTP 400 Bad Request
	// -------------------------------------------------------------------------
	t.Run("InvalidWinnerSlot_Returns400", func(t *testing.T) {
		for _, invalidSlot := range []int{99, -1, 3} {
			matchID := "match-bad-slot"
			sig := ComputeMatchHMACSignature([]byte(secret), matchID, validReplay)
			rec := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
				MatchUUID:           matchID,
				Player1ID:           "P1_BOUNDS",
				Player2ID:           "P2_BOUNDS",
				WinnerSlot:          invalidSlot,
				ExpectedFletcher32:  validFletcher,
				ClientHMACSignature: sig,
				ReplayPayloadBase64: validB64,
			})
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("winner_slot=%d debía retornar HTTP 400, obtenido %d", invalidSlot, rec.Code)
			}
		}
	})

	// -------------------------------------------------------------------------
	// Caso 8: player1_id == player2_id (y vacío) -> HTTP 400 Bad Request
	// -------------------------------------------------------------------------
	t.Run("SameOrEmptyPlayers_Returns400", func(t *testing.T) {
		matchID := "match-self-play"
		sig := ComputeMatchHMACSignature([]byte(secret), matchID, validReplay)
		recSame := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "SAME_PLAYER_ID",
			Player2ID:           "same_player_id",
			WinnerSlot:          1,
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: validB64,
		})
		if recSame.Code != http.StatusBadRequest {
			t.Fatalf("player1_id == player2_id debía retornar HTTP 400, obtenido %d", recSame.Code)
		}

		recEmpty := postJSON(router, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
			MatchUUID:           matchID,
			Player1ID:           "",
			Player2ID:           "P2_ONLY",
			WinnerSlot:          1,
			ExpectedFletcher32:  validFletcher,
			ClientHMACSignature: sig,
			ReplayPayloadBase64: validB64,
		})
		if recEmpty.Code != http.StatusBadRequest {
			t.Fatalf("player1_id vacío debía retornar HTTP 400, obtenido %d", recEmpty.Code)
		}
	})

	// -------------------------------------------------------------------------
	// Caso 9: Arbitraje de Rage Quit (2 desconexiones >= 4.0s -> -160 LP y Cola Restringida)
	// -------------------------------------------------------------------------
	t.Run("RageQuitArbitration_AppliesPenaltyAndRestrictedQueue", func(t *testing.T) {
		hbPayload := HeartbeatRequest{
			MatchUUID:       "match-ragequit-001",
			ReportingPlayer: "P1_CLEAN",
			OpponentPlayer:  "P2_RAGEQUITTER",
			OpponentCharID:  "LOCO_CO",
			Region:          "SA-EAST",
			CurrentFrame:    1420,
			SilenceSeconds:  4.5,
			OpponentInCombo: true,
		}
		for attempt := 1; attempt <= 2; attempt++ {
			hbRec := postJSON(router, "/api/v1/matches/heartbeat", hbPayload)
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
	})
}

func TestDiskSnapshotPersistenceAndReload(t *testing.T) {
	secret := "PERSISTENCE_SECRET_2026"
	stateFile := filepath.Join(t.TempDir(), "saf_state_snapshot.json")
	t.Setenv("SAF_STATE_FILE", stateFile)
	t.Setenv("DATABASE_URL", "postgres://saf_admin:secret@localhost:5432/saf_esports?sslmode=disable")

	store1 := NewArbitrationStore(secret)
	if store1.PersistenceMode() != "postgres_hook+disk_snapshot" {
		t.Fatalf("modo de persistencia inesperado: %s", store1.PersistenceMode())
	}
	router1 := BuildRouter(store1)

	replayPayload := buildValidSAFRPayload(180, 0x55667788)
	fletcher := ComputeFletcher32(replayPayload)
	matchID := "match-persisted-001"
	sig := ComputeMatchHMACSignature([]byte(secret), matchID, replayPayload)

	rec := postJSON(router1, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
		MatchUUID:           matchID,
		Region:              "SA-EAST",
		PatchVersion:        104,
		Player1ID:           "PERSIST_WINNER",
		Player2ID:           "PERSIST_LOSER",
		Player1CharacterID:  "CHR_EL_DIEZ",
		Player2CharacterID:  "CHR_O_REI",
		WinnerSlot:          1,
		ExpectedFletcher32:  fletcher,
		ClientHMACSignature: sig,
		ReplayPayloadBase64: base64.StdEncoding.EncodeToString(replayPayload),
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("envío inicial falló: HTTP %d (%s)", rec.Code, rec.Body.String())
	}
	var initialResp MatchAuditSubmitResponse
	_ = json.Unmarshal(rec.Body.Bytes(), &initialResp)

	// Recrear una segunda instancia desde el archivo SAF_STATE_FILE (simulando reinicio de proceso)
	store2 := NewArbitrationStore(secret)
	router2 := BuildRouter(store2)

	// 1. Verificar que el replay persiste tras reinicio
	dlReq := httptest.NewRequest(http.MethodGet, "/api/v1/replays/"+matchID, nil)
	dlRec := httptest.NewRecorder()
	router2.ServeHTTP(dlRec, dlReq)
	if dlRec.Code != http.StatusOK || !bytes.Equal(dlRec.Body.Bytes(), replayPayload) {
		t.Fatalf("el replay no se restauró correctamente desde el snapshot en disco (HTTP %d)", dlRec.Code)
	}

	// 2. Verificar que la protección de idempotencia (409) persiste tras reinicio
	dupRec := postJSON(router2, "/api/v1/matches/audit-and-submit", MatchAuditSubmitRequest{
		MatchUUID:           matchID,
		Player1ID:           "PERSIST_WINNER",
		Player2ID:           "PERSIST_LOSER",
		WinnerSlot:          1,
		ExpectedFletcher32:  fletcher,
		ClientHMACSignature: sig,
		ReplayPayloadBase64: base64.StdEncoding.EncodeToString(replayPayload),
	})
	if dupRec.Code != http.StatusConflict {
		t.Fatalf("se esperaba HTTP 409 Conflict tras recargar snapshot, obtenido %d", dupRec.Code)
	}

	// 3. Verificar que el LP actualizado persiste en memoria recargada
	persistedMMR := store2.getOrCreateMMR("PERSIST_WINNER", "CHR_EL_DIEZ", "SA-EAST")
	if persistedMMR.LeaguePoints != initialResp.P1UpdatedMMR.LeaguePoints {
		t.Fatalf("LP restaurado no coincide: esperado=%d, obtenido=%d",
			initialResp.P1UpdatedMMR.LeaguePoints, persistedMMR.LeaguePoints)
	}
}
