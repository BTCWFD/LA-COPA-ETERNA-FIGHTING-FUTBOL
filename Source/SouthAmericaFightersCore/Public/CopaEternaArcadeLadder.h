// CopaEternaArcadeLadder.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ C++20 - Deterministic 5-Match CONMEBOL Arcade Ladder & Post-Match Telemetry Evaluator
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "FixedPointTypes.h"
#include "CopaEternaArcadeLadder.generated.h"

/**
 * Etapas oficiales de la escalera Arcade "La Copa Eterna" (5 encuentros deterministas).
 */
UENUM(BlueprintType)
enum class ECopaLadderStage : uint8
{
    OctavosDeFinal          = 0 UMETA(DisplayName = "Match 1: Octavos de Final"),
    CuartosDeFinal          = 1 UMETA(DisplayName = "Match 2: Cuartos de Final"),
    Semifinal               = 2 UMETA(DisplayName = "Match 3: Semifinal Continental"),
    GranFinalCONMEBOL       = 3 UMETA(DisplayName = "Match 4: Gran Final Clásica"),
    DesafioSupremo_VARZero  = 4 UMETA(DisplayName = "Match 5: Desafío Supremo - V.A.R. ZERO"),
    ChampionCrowned         = 5 UMETA(DisplayName = "Campeón de La Copa Eterna")
};

/**
 * Calificación competitiva determinista del desempeño post-partido ("Nota de Potrero").
 */
UENUM(BlueprintType)
enum class ECombatStyleRank : uint8
{
    Rank_C = 0 UMETA(DisplayName = "C - Titular de Emergencia"),
    Rank_B = 1 UMETA(DisplayName = "B - Caudillo de Cancha"),
    Rank_A = 2 UMETA(DisplayName = "A - Crack Continental"),
    Rank_S = 3 UMETA(DisplayName = "S - Leyenda Eterna del Potrero")
};

/**
 * Telemetría determinista post-partido (100% aritmética entera y punto fijo Q32.32).
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FPostMatchTelemetry
{
    GENERATED_BODY()

    /** Daño total infligido por el Jugador 1 (escala base: 10000 HP por ronda). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 P1DamageDealt = 0;

    /** Daño total recibido desde el oponente (Jugador 2 / IA). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 P2DamageDealt = 0;

    /** Mayor cantidad de impactos encadenados en un solo combo. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 MaxCombo = 0;

    /** Cantidad de Gambetas Perfectas / Parries ejecutados con éxito (ventana de 2 frames). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 PerfectParries = 0;

    /** Cantidad de rupturas de alambrado / vallas publicitarias (Wall Breaks) logradas. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 WallBreaks = 0;

    /** Frames restantes en el reloj de partida al finalizar (máximo 99s * 60Hz = 5940 frames). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 RemainingFrames = 0;

    /** Rondas perdidas por el jugador en este encuentro (0 = Victoria limpia 2-0). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Arcade|Telemetry")
    int32 RoundsLostByPlayer = 0;

    /** Rango de estilo calculado determinísticamente (S / A / B / C). */
    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Telemetry")
    ECombatStyleRank StyleRank = ECombatStyleRank::Rank_C;

    /** Puntaje exacto en punto fijo Q32.32 usado para auditoría de replays y leaderboards. */
    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Telemetry")
    FFixedPoint ComputedPerformanceScore = FFixedPoint(0);
};

/**
 * Nodo individual dentro de la llave de 5 partidos del Modo Arcade.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FArcadeLadderMatchNode
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    ECopaLadderStage Stage = ECopaLadderStage::OctavosDeFinal;

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    FName OpponentFighterID = NAME_None;

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    FName StageArenaID = NAME_None;

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    bool bIsClassicRivalryMatch = false;

    /** Si es true en el Match 5, V.A.R. - ZERO inicia con su Fase 2 secreta ("Tiempo de Descuento Infinito" + Rewind 90f) habilitada. */
    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    bool bSecretBossPhase2Unlocked = false;

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    bool bIsCompleted = false;

    UPROPERTY(BlueprintReadOnly, Category = "Arcade|Ladder")
    FPostMatchTelemetry RecordedTelemetry;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnArcadeStageAdvanced, ECopaLadderStage, NewStage, const FArcadeLadderMatchNode&, NextMatchNode);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnArcadeTournamentCompleted, ECombatStyleRank, OverallTournamentRank);

/**
 * Subsistema de Escalera Arcade y Torneo "La Copa Eterna" (UCopaEternaArcadeLadderSubsystem).
 * Genera llaves de 5 partidos 100% deterministas a partir de un uint32 DeterministicSeed
 * y evalúa el rango competitivo S/A/B/C y el desbloqueo secreto de Fase 2 de V.A.R. - ZERO sin usar floats.
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UCopaEternaArcadeLadderSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    static constexpr int32 TotalLadderMatches = 5;

    // Umbrales deterministas de puntaje para ECombatStyleRank
    static constexpr int32 ThresholdRankS = 18000;
    static constexpr int32 ThresholdRankA = 13500;
    static constexpr int32 ThresholdRankB = 9000;

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

    /**
     * Construye de forma puramente determinista la llave de 5 encuentros:
     * Match 1: Octavos -> Match 2: Cuartos -> Match 3: Semifinal -> Match 4: Gran Final (Rival Clásico) -> Match 5: Desafío Supremo V.A.R.-ZERO.
     */
    void InitializeDeterministicLadder(FName InPlayerFighterID, uint32 InDeterministicSeed);

    /**
     * Calcula el rango de estilo (S / A / B / C) usando únicamente aritmética entera y FFixedPoint Q32.32.
     */
    UFUNCTION(BlueprintPure, Category = "Arcade|Telemetry")
    static ECombatStyleRank CalculateStyleRank(const FPostMatchTelemetry& Telemetry);

    /**
     * Calcula el puntaje exacto en punto fijo Q32.32 para una estructura de telemetría dada.
     */
    static FFixedPoint ComputeFixedPointPerformanceScore(const FPostMatchTelemetry& Telemetry);

    /**
     * Registra el resultado del partido actual y avanza en la llave del torneo.
     * Desbloquea la Fase 2 secreta de V.A.R. - ZERO en el 5to encuentro si el jugador llega y supera la Gran Final
     * sin haber perdido ninguna ronda en todo el torneo O habiendo obtenido Rango S en la Gran Final.
     * @return true si el jugador avanzó de ronda o coronó campeón; false si fue derrotado (Continue requerido).
     */
    UFUNCTION(BlueprintCallable, Category = "Arcade|Ladder")
    bool AdvanceLadder(bool bPlayerWon, const FPostMatchTelemetry& Telemetry);

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    ECopaLadderStage GetCurrentStage() const { return CurrentStage; }

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    int32 GetCurrentMatchIndex() const { return CurrentMatchIndex; }

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    bool GetCurrentMatchNode(FArcadeLadderMatchNode& OutNode) const;

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    const TArray<FArcadeLadderMatchNode>& GetLadderNodes() const { return LadderNodes; }

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    bool IsSecretBossPhase2Unlocked() const { return bSecretBossPhase2Unlocked; }

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    int32 GetTotalRoundsLostInRun() const { return TotalRoundsLostInTournament; }

    UFUNCTION(BlueprintPure, Category = "Arcade|Ladder")
    int32 GetTotalRankSCountInRun() const { return TotalRankSCount; }

    uint32 GetDeterministicSeed() const { return ActiveDeterministicSeed; }

public:
    UPROPERTY(BlueprintAssignable, Category = "Arcade|Events")
    FOnArcadeStageAdvanced OnArcadeStageAdvanced;

    UPROPERTY(BlueprintAssignable, Category = "Arcade|Events")
    FOnArcadeTournamentCompleted OnArcadeTournamentCompleted;

private:
    UPROPERTY()
    TArray<FArcadeLadderMatchNode> LadderNodes;

    FName SelectedPlayerFighterID = TEXT("FENOMENO_BR");
    uint32 ActiveDeterministicSeed = 19301950U;
    int32 CurrentMatchIndex = 0;
    ECopaLadderStage CurrentStage = ECopaLadderStage::OctavosDeFinal;

    int32 TotalRoundsLostInTournament = 0;
    int32 TotalRankSCount = 0;
    int32 ContinuesUsed = 0;
    bool bSecretBossPhase2Unlocked = false;

    /** PRNG entero determinista Xorshift32 (libre de discrepancias entre MSVC, Clang PS5 y Xbox). */
    static uint32 NextDeterministicRandom(uint32& InOutState);

    /** Devuelve el rival histórico canónico para la Gran Final (Match 4) y su estadio emblemático. */
    static FName ResolveCanonicalRivalForFighter(FName PlayerFighterID);
    static FName ResolveHomeStageForFighter(FName FighterID);
};
