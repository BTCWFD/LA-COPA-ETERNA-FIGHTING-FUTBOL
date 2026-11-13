-- ============================================================================
-- schema.sql — Base de Datos Competitiva PostgreSQL 16 ("La Copa Eterna")
-- Soporta MMR Individual por Personaje (Glicko-2), Historial de Partidas,
-- Teatro de Repeticiones (.safreplay) y Brackets de Copa Fin de Semana.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Tabla Maestra de Jugadores (Cross-Progression vía Epic Online Services ProductUserId)
CREATE TABLE IF NOT EXISTS players (
    player_id           VARCHAR(64) PRIMARY KEY, -- EOS ProductUserId
    display_name        VARCHAR(64) NOT NULL,
    platform_origin     VARCHAR(24) NOT NULL CHECK (platform_origin IN ('STEAM', 'PS5', 'XBOX_SERIES', 'PC_EPIC')),
    country_iso         CHAR(2) NOT NULL DEFAULT 'AR',
    region_bucket       VARCHAR(16) NOT NULL DEFAULT 'SA-EAST',
    highest_account_lp  INTEGER NOT NULL DEFAULT 1000,
    conduct_red_cards   INTEGER NOT NULL DEFAULT 0,
    is_penalty_queue    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. MMR Independiente por Personaje (Liga / División + Master Rating Glicko-2)
CREATE TABLE IF NOT EXISTS character_mmr_ratings (
    rating_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id           VARCHAR(64) NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    character_id        VARCHAR(32) NOT NULL, -- Ej. CHR_EL_DIEZ, CHR_O_REI, CHR_EL_PISTOLERO
    region_bucket       VARCHAR(16) NOT NULL DEFAULT 'SA-EAST',
    league_points       INTEGER NOT NULL DEFAULT 1000 CHECK (league_points >= 0),
    division_tier       VARCHAR(32) NOT NULL DEFAULT 'POTRERO_BARRIAL',
    glicko_rating       DOUBLE PRECISION NOT NULL DEFAULT 1500.0,
    glicko_rd           DOUBLE PRECISION NOT NULL DEFAULT 350.0 CHECK (glicko_rd BETWEEN 30.0 AND 350.0),
    glicko_volatility   DOUBLE PRECISION NOT NULL DEFAULT 0.060 CHECK (glicko_volatility BETWEEN 0.030 AND 0.120),
    wins_count          INTEGER NOT NULL DEFAULT 0,
    losses_count        INTEGER NOT NULL DEFAULT 0,
    streak_count        INTEGER NOT NULL DEFAULT 0,
    conduct_red_cards   INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_character_mmr_leaderboard
    ON character_mmr_ratings (region_bucket, league_points DESC, glicko_rating DESC);

-- 3. Historial Auditado de Partidas Competitivas y Telemetría de Red
CREATE TABLE IF NOT EXISTS matches_history (
    match_uuid              UUID PRIMARY KEY,
    patch_version           SMALLINT NOT NULL DEFAULT 104,
    region_bucket           VARCHAR(16) NOT NULL,
    stage_id                VARCHAR(32) NOT NULL,
    player1_id              VARCHAR(64) NOT NULL REFERENCES players(player_id),
    player2_id              VARCHAR(64) NOT NULL REFERENCES players(player_id),
    player1_character_id    VARCHAR(32) NOT NULL,
    player2_character_id    VARCHAR(32) NOT NULL,
    winner_slot             SMALLINT NOT NULL CHECK (winner_slot IN (0, 1, 2)),
    termination_type        VARCHAR(24) NOT NULL DEFAULT 'KO_NORMAL'
                            CHECK (termination_type IN ('KO_NORMAL', 'GRITO_SAGRADO_KO', 'TIME_OVER', 'RAGE_QUIT_FORFEIT')),
    simulated_frames        INTEGER NOT NULL CHECK (simulated_frames > 0),
    final_fletcher32        BIGINT NOT NULL,
    avg_rtt_ms              REAL NOT NULL DEFAULT 0.0,
    max_rollback_frames     SMALLINT NOT NULL DEFAULT 0,
    p1_macro_flagged        BOOLEAN NOT NULL DEFAULT FALSE,
    p2_macro_flagged        BOOLEAN NOT NULL DEFAULT FALSE,
    p1_lagswitch_flagged    BOOLEAN NOT NULL DEFAULT FALSE,
    p2_lagswitch_flagged    BOOLEAN NOT NULL DEFAULT FALSE,
    played_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_history_players
    ON matches_history (player1_id, player2_id, played_at DESC);

-- 4. Metadatos del Teatro de Repeticiones Deterministas (.safreplay en S3/MinIO/R2)
CREATE TABLE IF NOT EXISTS replays_metadata (
    match_uuid              UUID PRIMARY KEY REFERENCES matches_history(match_uuid) ON DELETE CASCADE,
    s3_object_key            VARCHAR(255) NOT NULL UNIQUE,
    payload_size_bytes      INTEGER NOT NULL CHECK (payload_size_bytes > 0 AND payload_size_bytes <= 51200),
    fletcher32_checksum     BIGINT NOT NULL,
    patch_version           SMALLINT NOT NULL,
    p1_character_id         VARCHAR(32) NOT NULL,
    p2_character_id         VARCHAR(32) NOT NULL,
    downloads_count         INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_replays_by_matchup
    ON replays_metadata (patch_version, p1_character_id, p2_character_id, created_at DESC);

-- 5. Automatización de Brackets del "Modo Copa Fin de Semana" (32 / 64 Jugadores)
CREATE TABLE IF NOT EXISTS weekend_cup_brackets (
    tournament_id           VARCHAR(64) NOT NULL,
    match_slot              SMALLINT NOT NULL,
    round_number            SMALLINT NOT NULL CHECK (round_number BETWEEN 1 AND 6),
    bracket_size            SMALLINT NOT NULL CHECK (bracket_size IN (32, 64)),
    region_bucket           VARCHAR(16) NOT NULL DEFAULT 'SA-EAST',
    player_a_id             VARCHAR(64) REFERENCES players(player_id),
    player_b_id             VARCHAR(64) REFERENCES players(player_id),
    checked_in_a            BOOLEAN NOT NULL DEFAULT FALSE,
    checked_in_b            BOOLEAN NOT NULL DEFAULT FALSE,
    winner_player_id        VARCHAR(64) REFERENCES players(player_id),
    match_uuid              UUID REFERENCES matches_history(match_uuid),
    check_in_deadline_utc   TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tournament_id, match_slot)
);
