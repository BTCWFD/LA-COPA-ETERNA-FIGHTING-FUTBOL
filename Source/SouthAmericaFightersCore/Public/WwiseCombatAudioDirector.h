// WwiseCombatAudioDirector.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Wwise Interactive Music, Stadium Crowd RTPCs & South American Broadcast Commentary
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WwiseCombatAudioDirector.generated.h"

#ifndef WITH_WWISE
#define WITH_WWISE 0
#endif

/**
 * Niveles de prioridad de relato sudamericano en tiempo real.
 * Un evento de mayor prioridad corta inmediatamente la línea activa disparando un Interrupt Stinger ("¡PERO CUIDADO!", "¡ATENCIÓN EN EL ÁREA!").
 */
UENUM(BlueprintType)
enum class ECommentaryPriority : uint8
{
    None            = 0   UMETA(Hidden),
    NeutralChatter  = 20  UMETA(DisplayName = "Neutral Chatter / Datos Históricos (20)"),
    ComboAction     = 50  UMETA(DisplayName = "Combo Action / Gambeta y Presión (50)"),
    CriticalMoment  = 80  UMETA(DisplayName = "Critical Moment / Counter-Hit / Wall Break (80)"),
    UltimateGoalKO  = 100 UMETA(DisplayName = "Ultimate Goal KO / Grito Sagrado de Gol (100)")
};

/**
 * Registro de un evento de relato deportivo en cola o reproducción activa.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FActiveCommentaryLine
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Audio|Commentary")
    FName EventName = NAME_None;

    UPROPERTY(BlueprintReadOnly, Category = "Audio|Commentary")
    ECommentaryPriority Priority = ECommentaryPriority::None;

    UPROPERTY()
    uint32 TriggerFrame = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Audio|Commentary")
    int32 EstimatedDurationFrames = 90;
};

/**
 * Subsistema de Dirección de Audio Reactivo (Wwise + Rollback Safe Audio Filter).
 * Gestiona:
 * 1. Mezcla vertical/horizontal de música interactiva (Murga, Batucada, Cumbia Villera, Cajón Peruano) y cánticos de hinchada.
 * 2. Cálculo determinista de RTPC_Match_Excitement (0..100) y RTPC_Crowd_Momentum (-100..+100).
 * 3. Sistema de Relatores Sudamericanos con interrupción limpia (Interrupt Stingers) y anti-repetición.
 * 4. Efecto coral "¡OOOO-LÉ!" ascendente en pitch (+100 cents por gambeta consecutiva).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UWwiseCombatAudioDirector : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    /**
     * Configura el ambiente acústico del estadio al iniciar la pelea.
     * @param StageAcousticSwitch Identificador de estadio (ej. "Stage_Bombonera", "Stage_Maracana", "Stage_LaPaz_3640m").
     * @param LocalHomeFighterID Personaje favorito del público local para ponderar RTPC_Crowd_Momentum.
     * @param AltitudeMeters Altitud sobre el nivel del mar (afecta filtro paso-alto de aire y reverbs).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Audio")
    void InitializeMatchAudioEnvironment(FName StageAcousticSwitch, FName LocalHomeFighterID, float AltitudeMeters);

    /**
     * Llamado una vez por frame confirmado/visual (60Hz).
     * Evalúa RTPC_Match_Excitement, RTPC_Crowd_Momentum, decaimiento de combo de "Olé" y expiración de líneas de relato.
     */
    void UpdateDeterministicAudioFrame(
        uint32 CurrentFrame,
        bool bIsRollbackReSimulation,
        float P1HealthRatio,
        float P2HealthRatio,
        int32 RemainingSeconds,
        int32 ActiveComboHits,
        int32 MomentumBiasP1vsP2);

    /**
     * Solicita reproducir una línea de relato deportivo con resolución de prioridad e Interrupt Stingers.
     * Ignora duplicados durante un re-simulate de Rollback si el evento ya fue emitido en una ventana de 6 frames.
     */
    bool TriggerLiveCommentaryEvent(
        FName WwiseEventName,
        ECommentaryPriority Priority,
        uint32 CurrentFrame,
        int32 DurationFrames = 120,
        bool bIsRollbackReSimulation = false);

    /**
     * Dispara la transición acústica de Ruptura de Alambrado / Túnel de Vestuarios (Wall Break).
     * Cambia el State Group `Acoustic_Environment` y empuja el bus de subgraves LFE.
     */
    void NotifyStageWallBreakTransition(FName NewZoneStateName, uint32 CurrentFrame);

    /**
     * Registra una esquiva/Gambeta exitosa para disparar el rugido "¡OOOO-LÉ!" de la hinchada.
     * Incrementa `RTPC_Ole_Combo_Pitch` en +100 cents por cada esquiva consecutiva dentro de la ventana activa.
     */
    void RegisterSuccessfulGambetaForCrowd(uint32 CurrentFrame, int32 PerformingPlayerIndex);

    UFUNCTION(BlueprintPure, Category = "Combat|Audio")
    float GetCurrentMatchExcitementRTPC() const { return CurrentMatchExcitement; }

    UFUNCTION(BlueprintPure, Category = "Combat|Audio")
    float GetCurrentCrowdMomentumRTPC() const { return CurrentCrowdMomentum; }

    UFUNCTION(BlueprintPure, Category = "Combat|Audio")
    int32 GetConsecutiveOleCount() const { return ConsecutiveOleCount; }

private:
    FName CurrentStageSwitch = NAME_None;
    FName HomeFighterID = NAME_None;
    float StageAltitudeMeters = 0.0f;

    float CurrentMatchExcitement = 15.0f; // 0.0 a 100.0
    float CurrentCrowdMomentum = 0.0f;    // -100.0 (P2 Domina) a +100.0 (P1 Domina)

    int32 ConsecutiveOleCount = 0;
    uint32 LastOleFrame = 0;

    FActiveCommentaryLine CurrentActiveCommentary;

    /** Historial corto de eventos emitidos para evitar flanging/doble disparo durante Rollbacks de hasta 8 frames */
    TMap<FName, uint32> RecentlyTriggeredEventFrames;

    // Puente limpio hacia el SoundEngine de Wwise (compila con o sin el plugin AkAudio instalado)
    void SetWwiseGlobalRTPC(const TCHAR* RTPCName, float Value, int32 InterpolationMs = 0);
    void SetWwiseState(const TCHAR* StateGroup, const TCHAR* StateValue);
    void SetWwiseSwitch(const TCHAR* SwitchGroup, const TCHAR* SwitchValue);
    void PostWwiseGlobalEvent(const TCHAR* EventName);
};
