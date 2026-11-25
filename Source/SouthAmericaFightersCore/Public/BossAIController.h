// BossAIController.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "AIController.h"
#include "FixedPointTypes.h"
#include "DeterministicFighterStateMachine.h"
#include "BossAIController.generated.h"

/**
 * Fases del Jefe Final "El Juez Supremo" (V.A.R. - ZERO).
 */
UENUM(BlueprintType)
enum class EBossPhase : uint8
{
    Phase1_IronRule          UMETA(DisplayName = "Phase 1: Iron Rule (Offside Lasers & Zoning)"),
    Phase2_InfiniteStoppage  UMETA(DisplayName = "Phase 2: Infinite Stoppage (V.A.R. Rewind & Unblockables)")
};

/**
 * Snapshot determinista de un frame de combate almacenado en el Ring Buffer de 120 frames del jefe.
 * Permite ejecutar la mecánica "V.A.R. Rewind" rebobinando 90 frames (1.5s a 60 Hz) sin desincronizar GGPO.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FCombatFrameSnapshot
{
    GENERATED_BODY()

    UPROPERTY(SaveGame)
    uint32 FrameNumber = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    FFixedPoint P1PosX;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    FFixedPoint P1PosY;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    FFixedPoint P2PosX;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    FFixedPoint P2PosY;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    int32 P1Health = 10000;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    int32 P2Health = 13000;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    int32 P1SuperMeter = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    int32 P2SuperMeter = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    uint8 P1StateID = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "VAR|Snapshot")
    uint8 P2StateID = 0;

    UPROPERTY(SaveGame)
    uint16 P1StateFrame = 0;

    UPROPERTY(SaveGame)
    uint16 P2StateFrame = 0;

    /** Checksum determinista Fletcher-32 sobre el estado de este frame. */
    UPROPERTY(SaveGame)
    uint32 Checksum = 0;

    uint32 ComputeFletcher32Checksum() const;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnVARRewindExecuted, const FCombatFrameSnapshot&, RestoredSnapshot);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnBossPhaseChanged, EBossPhase, NewPhase);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnBossSystemOverload);

/**
 * Controlador de IA determinista a 60 Hz para el Jefe Final "V.A.R. - ZERO".
 * Implementa lectura diferida (ReactionDelayFrames) para evitar input-reading injusto,
 * Ring Buffer estático de 120 frames para V.A.R. Rewind y vulnerabilidad al "Potrero" (Gambetas Perfectas).
 */
UCLASS(BlueprintType, Blueprintable)
class SOUTHAMERICAFIGHTERSCORE_API ABossAIController : public AAIController
{
    GENERATED_BODY()

public:
    static constexpr int32 HistoryCapacityFrames = 120; // 2.0 segundos exactos a 60 Hz
    static constexpr int32 DefaultRewindFrames = 90;    // 1.5 segundos exactos a 60 Hz
    static constexpr int32 OutplaysRequiredForOverload = 3;
    static constexpr int32 DefaultBossMaxHealth = 13000;

    /** Reconoce ambos identificadores canónicos del Jefe Final ("BOSS_VAR_ZERO" en DataTables/Arcade y "VAR_ZERO_BOSS" en UI/Roster). */
    UFUNCTION(BlueprintPure, Category = "BossAI|Identity")
    static bool IsBossFighterID(FName FighterID)
    {
        return FighterID == TEXT("BOSS_VAR_ZERO") || FighterID == TEXT("VAR_ZERO_BOSS");
    }

    ABossAIController();

    /**vincula las máquinas de estado deterministas de P1 (Jugador) y P2 (Jefe V.A.R. - ZERO). */
    UFUNCTION(BlueprintCallable, Category = "BossAI|Deterministic")
    void BindFighterStateMachines(UDeterministicFighterStateMachine* InPlayerFighter, UDeterministicFighterStateMachine* InBossFighter);

    /** Paso de simulación determinista invocado a 60 Hz por el bucle principal de combate. */
    void DeterministicStep(uint32 CurrentFrame);

    /**
     * Registra una Gambeta Perfecta / jugadas de potrero imprevistas del jugador.
     * Al acumular 3 outplays, provoca System Overload en V.A.R. - ZERO y habilita el Ultimate Cooperativo CONMEBOL.
     */
    UFUNCTION(BlueprintCallable, Category = "BossAI|Mechanics")
    void RegisterStreetFootballOutplay();

    /**
     * Activa la mecánica insignia de Fase 2: rebobina N frames del Ring Buffer (por defecto 90 frames)
     * para anular un combo en curso del jugador y restaurar la posición/salud previa.
     */
    UFUNCTION(BlueprintCallable, Category = "BossAI|Mechanics")
    bool TriggerVARRewind(int32 FramesToRewind = 90);

    /** Verifica si la salud del jefe cayó por debajo del umbral (50%) y dispara la transición a Fase 2. */
    UFUNCTION(BlueprintCallable, Category = "BossAI|Mechanics")
    bool CheckAndTriggerPhaseTwoTransition();

    /** Devuelve la máscara de bits de entrada (ECombatInputBits) decidida por el jefe en este frame. */
    uint16 GetCurrentBossInputBitmask() const { return CurrentBossInputBitmask; }

    UFUNCTION(BlueprintPure, Category = "BossAI|State")
    EBossPhase GetCurrentPhase() const { return CurrentPhase; }

    UFUNCTION(BlueprintPure, Category = "BossAI|State")
    bool IsSystemOverloaded() const { return bIsSystemOverloaded; }

    UFUNCTION(BlueprintPure, Category = "BossAI|State")
    int32 GetStreetFootballOutplayCount() const { return StreetFootballOutplayCount; }

    /** Obtiene el snapshot percibido por la IA respetando ReactionDelayFrames (evita input reading de 0ms). */
    bool GetDelayedPerceivedSnapshot(FCombatFrameSnapshot& OutPerceivedSnapshot) const;

public:
    /** Retardo de reacción humana simulada en frames (16 frames = ~266ms a 60 Hz) para impedir lectura instantánea de inputs. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "BossAI|Fairness", meta = (ClampMin = "8", ClampMax = "30"))
    int32 ReactionDelayFrames = 16;

    /**Salud máxima canónica del Jefe Final V.A.R. - ZERO (13,000 HP). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "BossAI|Config")
    int32 BossMaxHealth = DefaultBossMaxHealth;

    /** Umbral de salud en el que V.A.R. - ZERO activa Fase 2 (50% de 13,000 HP = 6,500 HP). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "BossAI|Config")
    int32 PhaseTwoHealthThreshold = 6500;

    /** Cooldown mínimo en frames entre activaciones de V.A.R. Rewind (600 frames = 10 segundos). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "BossAI|Config")
    int32 VARRewindCooldownFrames = 600;

    /** Duración del estado de vulnerabilidad System Overload tras recibir 3 Gambetas Perfectas (240 frames = 4s). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "BossAI|Config")
    int32 SystemOverloadDurationFrames = 240;

    UPROPERTY(BlueprintAssignable, Category = "BossAI|Events")
    FOnVARRewindExecuted OnVARRewindExecuted;

    UPROPERTY(BlueprintAssignable, Category = "BossAI|Events")
    FOnBossPhaseChanged OnBossPhaseChanged;

    UPROPERTY(BlueprintAssignable, Category = "BossAI|Events")
    FOnBossSystemOverload OnBossSystemOverload;

private:
    /** Ring Buffer estático de 120 frames libre de asignaciones dinámicas en caliente. */
    TStaticArray<FCombatFrameSnapshot, HistoryCapacityFrames> FrameHistoryBuffer;

    int32 HistoryWriteIndex = 0;
    int32 ValidHistoryFrames = 0;

    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> PlayerFighterSM;

    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> BossFighterSM;

    EBossPhase CurrentPhase = EBossPhase::Phase1_IronRule;
    uint16 CurrentBossInputBitmask = 0;

    int32 StreetFootballOutplayCount = 0;
    int32 RewindCooldownRemaining = 0;
    int32 OverloadFramesRemaining = 0;
    bool bIsSystemOverloaded = false;
    bool bCooperativeUltimateReady = false;

    void RecordCurrentFrameSnapshot(uint32 CurrentFrame);
    void ApplySnapshotToFighters(const FCombatFrameSnapshot& Snapshot);
    uint16 DecideTacticalAction(uint32 CurrentFrame, const FCombatFrameSnapshot& PerceivedState);
};
