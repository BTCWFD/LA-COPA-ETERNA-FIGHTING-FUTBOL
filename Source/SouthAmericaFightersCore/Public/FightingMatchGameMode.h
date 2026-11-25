// FightingMatchGameMode.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Master 60Hz Deterministic Combat Referee, Collision Solver & Subsystem Orchestrator
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/GameStateBase.h"
#include "FixedPointTypes.h"
#include "StageDefinition.h"
#include "FighterCharacterPawn.h"
#include "FightingCameraAndReplayDirector.h"
#include "CombatHUDAndHapticsSubsystem.h"
#include "WwiseCombatAudioDirector.h"
#include "TrainingModeSubsystem.h"
#include "BossAIController.h"
#include "EOSGGPONetworkBridge.h"
#include "FightingMatchGameMode.generated.h"

/**
 * Estado global determinista de la ronda y del escenario (serializable en el Ring Buffer de Rollback).
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FMatchGlobalStatePOD
{
    GENERATED_BODY()

    UPROPERTY(SaveGame)
    uint32 CurrentSimulationFrame = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 RemainingTimerFrames = 99 * 60; // 99 segundos a 60 Hz

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 CurrentRoundNumber = 1;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P1RoundsWon = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P2RoundsWon = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    bool bIsInStageZoneB = false;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 LeftWallRemainingHealth = 3;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 RightWallRemainingHealth = 3;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P1ActiveComboHits = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P1ActiveComboDamage = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P2ActiveComboHits = 0;

    UPROPERTY(SaveGame, BlueprintReadOnly, Category = "MatchState")
    int32 P2ActiveComboDamage = 0;
};

/**
 * GameState replicado/determinista de la partida ("La Copa Eterna").
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API AFightingMatchGameState : public AGameStateBase
{
    GENERATED_BODY()

public:
    UPROPERTY(BlueprintReadOnly, Category = "Match|State")
    FMatchGlobalStatePOD MatchState;

    UFUNCTION(BlueprintPure, Category = "Match|State")
    int32 GetRemainingMatchSeconds() const
    {
        return FMath::CeilToInt(static_cast<float>(MatchState.RemainingTimerFrames) / 60.0f);
    }
};

/**
 * Árbitro Maestro de Partida a 60 Hz (AFightingMatchGameMode).
 * Orquesta en orden determinista estricto:
 * 1. Captura de inputs de 16 bits (Local, GGPO P2P, Training Dummy o Jefe V.A.R. - ZERO).
 * 2. Simulación de máquinas de estado de P1 y P2 (Q32.32).
 * 3. Resolución de colisión Pushbox-vs-Pushbox y límites de muro con soporte de Wall Break.
 * 4. Simulación y choque de proyectiles de balón (Bati-Cañonazo de 2 impactos y reflejo de El Escorpión).
 * 5. Evaluación simétrica de Hitbox-vs-Hurtbox (con soporte de Trade, Block, Hitstop y telemetría de ventaja).
 * 6. Sincronización de Cámara 2.5D, Audio Wwise, HUD CommonUI Zero-Binding y grabación de Replay.
 */
UCLASS(BlueprintType, Blueprintable)
class SOUTHAMERICAFIGHTERSCORE_API AFightingMatchGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    AFightingMatchGameMode();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    /** Ejecuta exactamente 1 tick maestro determinista de combate (1/60s). */
    void StepDeterministicMatchTick(uint16 P1InputMask, uint16 P2InputMask, bool bIsRollbackReSimulation = false);

    /** Dispara un proyectil de balón determinista en la cancha. */
    UFUNCTION(BlueprintCallable, Category = "Match|Projectiles")
    ADeterministicBallProjectile* SpawnBallProjectileForFighter(
        int32 OwnerPlayerIndex,
        bool bIsHeavyChargedCanonShot);

    UFUNCTION(BlueprintPure, Category = "Match|Actors")
    AFighterCharacterPawn* GetPlayer1Pawn() const { return Player1Pawn; }

    UFUNCTION(BlueprintPure, Category = "Match|Actors")
    AFighterCharacterPawn* GetPlayer2Pawn() const { return Player2Pawn; }

    UFUNCTION(BlueprintPure, Category = "Match|Camera")
    UFightingCameraDirector* GetCameraDirector() const { return CameraDirector; }

    UFUNCTION(BlueprintPure, Category = "Match|Netcode")
    UEOSGGPONetworkBridge* GetNetworkBridge() const { return NetworkBridge; }

public:
    /** Configuración activa del estadio CONMEBOL (límites Q32.32 Zona A/B, salud de muros y switches Wwise). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadWrite, Category = "Match|Stage")
    FStageDataRow ActiveStageData;

    /** Si es true, P2 es controlado por el subsistema de Modo Entrenamiento ("El Potrero"). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match|Mode")
    bool bIsTrainingModeMatch = false;

    /** Referencia opcional al widget principal de HUD CommonUI para inyección Zero-Binding a 60 Hz. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match|UI")
    TObjectPtr<UCombatMainHUDWidget> ActiveCombatHUDWidget = nullptr;

    /** Referencia opcional al controlador de IA del Jefe Final V.A.R. - ZERO. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Match|AI")
    TObjectPtr<ABossAIController> ActiveBossAIController = nullptr;

protected:
    UPROPERTY(Transient)
    TObjectPtr<AFighterCharacterPawn> Player1Pawn = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<AFighterCharacterPawn> Player2Pawn = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<ADeterministicBallProjectile> Player1BallProjectile = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<ADeterministicBallProjectile> Player2BallProjectile = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UFightingCameraDirector> CameraDirector = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UEOSGGPONetworkBridge> NetworkBridge = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UReplayPlaybackSubsystem> ReplayDirector = nullptr;

private:
    void ResolvePushboxAndStageWallCollision();
    void StepAndResolveBallProjectiles(bool bIsRollbackReSimulation);
    void ResolveMeleeHitboxes(bool bIsRollbackReSimulation);
    void CheckAndTriggerStageWallBreak(int32 KnockedPlayerIndex, int32 WallDirectionSign);
    bool IsDefenderBlockingAttack(const FFighterDeterministicStatePOD& Attacker, const FFighterDeterministicStatePOD& Defender, uint16 DefenderInputMask) const;
    void BroadcastVisualAndHUDState(bool bIsRollbackReSimulation);

    uint16 CachedP1InputMask = 0;
    uint16 CachedP2InputMask = 0;
};
