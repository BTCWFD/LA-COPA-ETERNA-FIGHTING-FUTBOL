// CombatHUDAndHapticsSubsystem.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - CommonUI Zero-Binding HUD & DualSense/Xbox Impulse Haptics
#pragma once

#include "CoreMinimal.h"
#include "CommonActivatableWidget.h"
#include "Subsystems/LocalPlayerSubsystem.h"
#include "CombatHUDAndHapticsSubsystem.generated.h"

class UImage;
class UCommonTextBlock;
class UMaterialInstanceDynamic;

/**
 * Eventos hápticos de baja latencia sincronizados con el frame exacto de impacto o carga de tiro.
 */
UENUM(BlueprintType)
enum class ECombatHapticEvent : uint8
{
    LightImpact             UMETA(DisplayName = "Light Impact / Jab / Low Kick"),
    HeavyCounterHit         UMETA(DisplayName = "Heavy Counter-Hit / Trancazo"),
    ChargingShotTension     UMETA(DisplayName = "Charging Shot / Chilena Tension"),
    StaminaBurnoutPulse     UMETA(DisplayName = "Stamina Burnout / Ahogo"),
    CrowdGoalExplosion      UMETA(DisplayName = "Ultimate Goal KO / Estallido de Tribuna"),
    ReleaseAllTriggers      UMETA(DisplayName = "Release Adaptive Triggers Immediately")
};

/**
 * Estado telemétrico por jugador enviado por Push Determinista al HUD cada frame (60Hz).
 * Cero Property Bindings de Slate para garantizar < 0.08ms en el hilo de UI.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFighterHUDTelemetry
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 CurrentHealth = 10000;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 MaxHealth = 10000;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 RecoverableRedHealth = 10000;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 SuperMeter = 0; // 0..3000 (3 Barras de "Grito Sagrado")

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 GambetaStamina = 1000; // 0..1000

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 YellowCardRisk = 0; // 0..1000 (Al llegar a 1000 -> Penalización / Guard Crush)

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 ActiveComboHits = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 ActiveComboDamage = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 LastMoveFrameAdvantage = 0;
};

/**
 * Paquete completo de actualización de HUD en el frame actual.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FDeterministicHUDFramePacket
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    uint32 SimulationFrame = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 RemainingMatchSeconds = 99;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 CurrentRoundIndex = 1;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    FFighterHUDTelemetry Player1;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    FFighterHUDTelemetry Player2;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 RollbackFramesTelemetry = 0;

    UPROPERTY(BlueprintReadOnly, Category = "HUD")
    int32 PingMilliseconds = 18;
};

/**
 * Widget principal de combate basado en CommonUI (UCommonActivatableWidget).
 * Implementa arquitectura Zero-Binding Fast Path: ninguna propiedad usa TAttribute/Delegate Tick.
 * Todo cambio se inyecta explícitamente desde el paso visual determinista vía PushDeterministicHUDUpdate.
 */
UCLASS(Abstract, Blueprintable, meta = (DisableNativeTick))
class SOUTHAMERICAFIGHTERSCORE_API UCombatMainHUDWidget : public UCommonActivatableWidget
{
    GENERATED_BODY()

public:
    UCombatMainHUDWidget(const FObjectInitializer& ObjectInitializer);

    virtual void NativeOnInitialized() override;

    /**
     * Fast-path de actualización determinista a 60Hz.
     * Actualiza únicamente los MaterialInstanceDynamic y textos cuyos valores enteros hayan cambiado respecto al frame previo.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|HUD")
    void PushDeterministicHUDUpdate(const FDeterministicHUDFramePacket& FramePacket);

    /**
     * Notificación instantánea de evento especial en pantalla (Counter Hit, Punish, Guard Crush, ¡OLÉ!).
     */
    UFUNCTION(BlueprintImplementableEvent, Category = "Combat|HUD")
    void OnCombatCalloutTriggered(int32 PlayerIndex, FName CalloutTag, int32 FrameAdvantage);

protected:
    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UImage> P1_HealthBarImage = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UImage> P2_HealthBarImage = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UImage> P1_SuperMeterImage = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UImage> P2_SuperMeterImage = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UCommonTextBlock> MatchTimerText = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UCommonTextBlock> P1_ComboCounterText = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UCommonTextBlock> P2_ComboCounterText = nullptr;

    UPROPERTY(BlueprintReadWrite, meta = (BindWidgetOptional), Category = "Combat|HUD")
    TObjectPtr<UCommonTextBlock> NetcodeTelemetryText = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> P1_HealthBarMID = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> P2_HealthBarMID = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> P1_SuperMeterMID = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> P2_SuperMeterMID = nullptr;

private:
    FDeterministicHUDFramePacket CachedPreviousPacket;
    bool bHasInitializedCache = false;

    void UpdateFighterBarsMID(
        UMaterialInstanceDynamic* HealthMID,
        UMaterialInstanceDynamic* MeterMID,
        const FFighterHUDTelemetry& Current,
        const FFighterHUDTelemetry& Previous,
        bool bForceUpdate);
};

/**
 * Subsistema por Jugador Local para Háptica Competitiva (PS5 DualSense Adaptive Triggers + Audio-to-Haptics & Xbox Impulse Triggers).
 * Incluye el modo "Tournament Trigger Safe Mode" exigido en torneos presenciales para desactivar resistencia mecánica en L2/R2.
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UCombatHapticsSubsystem : public ULocalPlayerSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    /**
     * Activa o desactiva la resistencia mecánica de los gatillos adaptativos L2/R2 (Modo Torneo EVO/CONMEBOL).
     * Cuando bDisableAdaptiveResistance == true, limpia de inmediato los registros de tensión de DualSense.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Haptics")
    void SetTournamentTriggerMode(bool bDisableAdaptiveResistance);

    UFUNCTION(BlueprintPure, Category = "Combat|Haptics")
    bool IsTournamentTriggerModeEnabled() const { return bTournamentTriggerSafeMode; }

    /**
     * Dispara un patrón háptico determinista sobre el controlador del jugador local.
     * @param Event Tipo de evento de combate.
     * @paramNormalizedIntensity Escala 0.0 a 1.0 de fuerza del evento.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Haptics")
    void TriggerCombatHapticEvent(ECombatHapticEvent Event, float NormalizedIntensity = 1.0f);

    /**
     * Modula continuamente los gatillos adaptativos según la fatiga (Gambeta Stamina) y la carga de disparo especial.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Haptics")
    void UpdateContinuousTriggerFeedback(float GambetaStaminaRatio, float ShotChargeRatio);

private:
    bool bTournamentTriggerSafeMode = false;
    float LastAppliedStaminaResistance = -1.0f;
    float LastAppliedShotTension = -1.0f;

    void ApplyDualSenseTriggerEffect(float StartPosition, float EndPosition, float Strength, float FrequencyHz);
    void ClearAllHardwareTriggers();
    void SendForceFeedbackEnvelope(float LeftLarge, float RightSmall, float LeftTriggerImpulse, float RightTriggerImpulse, float DurationSeconds);
};
