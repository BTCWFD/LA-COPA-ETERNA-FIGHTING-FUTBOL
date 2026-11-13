// CombatHUDAndHapticsSubsystem.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - CommonUI Zero-Binding HUD & DualSense/Xbox Impulse Haptics

#include "CombatHUDAndHapticsSubsystem.h"
#include "Components/Image.h"
#include "CommonTextBlock.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/PlayerController.h"

namespace CombatHUDShaderParams
{
    static const FName HealthPercentParam(TEXT("HealthPercent"));
    static const FName RedHealthPercentParam(TEXT("RedHealthPercent"));
    static const FName GambetaPercentParam(TEXT("GambetaPercent"));
    static const FName SuperMeterPercentParam(TEXT("SuperMeterPercent"));
    static const FName SuperStocksCountParam(TEXT("SuperStocksCount"));
    static const FName YellowCardRiskParam(TEXT("YellowCardRisk"));
}

UCombatMainHUDWidget::UCombatMainHUDWidget(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
}

void UCombatMainHUDWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();

    if (IsValid(P1_HealthBarImage))
    {
        P1_HealthBarMID = P1_HealthBarImage->GetDynamicMaterial();
    }
    if (IsValid(P2_HealthBarImage))
    {
        P2_HealthBarMID = P2_HealthBarImage->GetDynamicMaterial();
    }
    if (IsValid(P1_SuperMeterImage))
    {
        P1_SuperMeterMID = P1_SuperMeterImage->GetDynamicMaterial();
    }
    if (IsValid(P2_SuperMeterImage))
    {
        P2_SuperMeterMID = P2_SuperMeterImage->GetDynamicMaterial();
    }

    bHasInitializedCache = false;
}

void UCombatMainHUDWidget::PushDeterministicHUDUpdate(const FDeterministicHUDFramePacket& FramePacket)
{
    const bool bForceUpdate = !bHasInitializedCache;

    UpdateFighterBarsMID(
        P1_HealthBarMID,
        P1_SuperMeterMID,
        FramePacket.Player1,
        CachedPreviousPacket.Player1,
        bForceUpdate);

    UpdateFighterBarsMID(
        P2_HealthBarMID,
        P2_SuperMeterMID,
        FramePacket.Player2,
        CachedPreviousPacket.Player2,
        bForceUpdate);

    // Reloj de Round (solo invalida el layout de texto si cambia el segundo entero)
    if (bForceUpdate || FramePacket.RemainingMatchSeconds != CachedPreviousPacket.RemainingMatchSeconds)
    {
        if (IsValid(MatchTimerText))
        {
            const int32 ClampedSeconds = FMath::Clamp(FramePacket.RemainingMatchSeconds, 0, 99);
            MatchTimerText->SetText(FText::AsNumber(ClampedSeconds));
        }
    }

    // Contador de Combo P1
    if (bForceUpdate ||
        FramePacket.Player1.ActiveComboHits != CachedPreviousPacket.Player1.ActiveComboHits ||
        FramePacket.Player1.ActiveComboDamage != CachedPreviousPacket.Player1.ActiveComboDamage)
    {
        if (IsValid(P1_ComboCounterText))
        {
            if (FramePacket.Player1.ActiveComboHits >= 2)
            {
                P1_ComboCounterText->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
                P1_ComboCounterText->SetText(FText::FromString(
                    FString::Printf(TEXT("%d HITS (%d DMG)"), FramePacket.Player1.ActiveComboHits, FramePacket.Player1.ActiveComboDamage)));
            }
            else
            {
                P1_ComboCounterText->SetVisibility(ESlateVisibility::Collapsed);
            }
        }
    }

    // Contador de Combo P2
    if (bForceUpdate ||
        FramePacket.Player2.ActiveComboHits != CachedPreviousPacket.Player2.ActiveComboHits ||
        FramePacket.Player2.ActiveComboDamage != CachedPreviousPacket.Player2.ActiveComboDamage)
    {
        if (IsValid(P2_ComboCounterText))
        {
            if (FramePacket.Player2.ActiveComboHits >= 2)
            {
                P2_ComboCounterText->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
                P2_ComboCounterText->SetText(FText::FromString(
                    FString::Printf(TEXT("%d HITS (%d DMG)"), FramePacket.Player2.ActiveComboHits, FramePacket.Player2.ActiveComboDamage)));
            }
            else
            {
                P2_ComboCounterText->SetVisibility(ESlateVisibility::Collapsed);
            }
        }
    }

    // Telemetría de Netcode Rollback (Ping + Rollback Frames)
    if (bForceUpdate ||
        FramePacket.RollbackFramesTelemetry != CachedPreviousPacket.RollbackFramesTelemetry ||
        FramePacket.PingMilliseconds != CachedPreviousPacket.PingMilliseconds)
    {
        if (IsValid(NetcodeTelemetryText))
        {
            NetcodeTelemetryText->SetText(FText::FromString(
                FString::Printf(TEXT("PING: %dms | RB: %dF"), FramePacket.PingMilliseconds, FramePacket.RollbackFramesTelemetry)));
        }
    }

    CachedPreviousPacket = FramePacket;
    bHasInitializedCache = true;
}

void UCombatMainHUDWidget::UpdateFighterBarsMID(
    UMaterialInstanceDynamic* HealthMID,
    UMaterialInstanceDynamic* MeterMID,
    const FFighterHUDTelemetry& Current,
    const FFighterHUDTelemetry& Previous,
    bool bForceUpdate)
{
    const float SafeMaxHealth = static_cast<float>(FMath::Max(1, Current.MaxHealth));

    if (IsValid(HealthMID))
    {
        if (bForceUpdate || Current.CurrentHealth != Previous.CurrentHealth || Current.MaxHealth != Previous.MaxHealth)
        {
            const float HealthRatio = FMath::Clamp(static_cast<float>(Current.CurrentHealth) / SafeMaxHealth, 0.0f, 1.0f);
            HealthMID->SetScalarParameterValue(CombatHUDShaderParams::HealthPercentParam, HealthRatio);
        }

        if (bForceUpdate || Current.RecoverableRedHealth != Previous.RecoverableRedHealth)
        {
            const float RedHealthRatio = FMath::Clamp(static_cast<float>(Current.RecoverableRedHealth) / SafeMaxHealth, 0.0f, 1.0f);
            HealthMID->SetScalarParameterValue(CombatHUDShaderParams::RedHealthPercentParam, RedHealthRatio);
        }

        if (bForceUpdate || Current.GambetaStamina != Previous.GambetaStamina)
        {
            const float GambetaRatio = FMath::Clamp(static_cast<float>(Current.GambetaStamina) / 1000.0f, 0.0f, 1.0f);
            HealthMID->SetScalarParameterValue(CombatHUDShaderParams::GambetaPercentParam, GambetaRatio);
        }

        if (bForceUpdate || Current.YellowCardRisk != Previous.YellowCardRisk)
        {
            const float RiskRatio = FMath::Clamp(static_cast<float>(Current.YellowCardRisk) / 1000.0f, 0.0f, 1.0f);
            HealthMID->SetScalarParameterValue(CombatHUDShaderParams::YellowCardRiskParam, RiskRatio);
        }
    }

    if (IsValid(MeterMID))
    {
        if (bForceUpdate || Current.SuperMeter != Previous.SuperMeter)
        {
            const float TotalMeterRatio = FMath::Clamp(static_cast<float>(Current.SuperMeter) / 3000.0f, 0.0f, 1.0f);
            const int32 FullStocks = FMath::Clamp(Current.SuperMeter / 1000, 0, 3);
            MeterMID->SetScalarParameterValue(CombatHUDShaderParams::SuperMeterPercentParam, TotalMeterRatio);
            MeterMID->SetScalarParameterValue(CombatHUDShaderParams::SuperStocksCountParam, static_cast<float>(FullStocks));
        }
    }
}

// ============================================================================
// UCombatHapticsSubsystem - DualSense Adaptive Triggers & Xbox Impulse Haptics
// ============================================================================

void UCombatHapticsSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    bTournamentTriggerSafeMode = false;
    LastAppliedStaminaResistance = -1.0f;
    LastAppliedShotTension = -1.0f;
}

void UCombatHapticsSubsystem::Deinitialize()
{
    ClearAllHardwareTriggers();
    Super::Deinitialize();
}

void UCombatHapticsSubsystem::SetTournamentTriggerMode(bool bDisableAdaptiveResistance)
{
    bTournamentTriggerSafeMode = bDisableAdaptiveResistance;
    if (bTournamentTriggerSafeMode)
    {
        ClearAllHardwareTriggers();
    }
}

void UCombatHapticsSubsystem::TriggerCombatHapticEvent(ECombatHapticEvent Event, float NormalizedIntensity)
{
    const float ClampedIntensity = FMath::Clamp(NormalizedIntensity, 0.0f, 1.0f);

    switch (Event)
    {
    case ECombatHapticEvent::LightImpact:
        // Transiente agudo en el motor derecho (Voice Coil / High Frequency)
        SendForceFeedbackEnvelope(0.15f * ClampedIntensity, 0.65f * ClampedIntensity, 0.0f, 0.25f * ClampedIntensity, 0.045f);
        break;

    case ECombatHapticEvent::HeavyCounterHit:
        // Golpe seco asimétrico + impulso de gatillo en Xbox/DualSense
        SendForceFeedbackEnvelope(1.00f * ClampedIntensity, 0.90f * ClampedIntensity, 0.70f * ClampedIntensity, 0.85f * ClampedIntensity, 0.140f);
        if (!bTournamentTriggerSafeMode)
        {
            ApplyDualSenseTriggerEffect(0.10f, 0.85f, 0.90f * ClampedIntensity, 45.0f);
        }
        break;

    case ECombatHapticEvent::ChargingShotTension:
        // Tensión progresiva tipo cuerda de arco al cargar un tiro especial o chilena
        SendForceFeedbackEnvelope(0.35f * ClampedIntensity, 0.55f * ClampedIntensity, 0.40f * ClampedIntensity, 0.60f * ClampedIntensity, 0.080f);
        if (!bTournamentTriggerSafeMode)
        {
            ApplyDualSenseTriggerEffect(0.15f, 0.95f, ClampedIntensity, 28.0f);
        }
        break;

    case ECombatHapticEvent::StaminaBurnoutPulse:
        // Latido cardíaco de baja frecuencia (Burnout / Falta de Oxígeno en Altura)
        SendForceFeedbackEnvelope(0.75f * ClampedIntensity, 0.15f * ClampedIntensity, 0.30f * ClampedIntensity, 0.30f * ClampedIntensity, 0.180f);
        break;

    case ECombatHapticEvent::CrowdGoalExplosion:
        // Rugido sísmico de estadio sudamericano tras KO de Gol Definitivo
        SendForceFeedbackEnvelope(1.00f, 1.00f, 0.90f, 0.90f, 0.450f);
        break;

    case ECombatHapticEvent::ReleaseAllTriggers:
    default:
        ClearAllHardwareTriggers();
        break;
    }
}

void UCombatHapticsSubsystem::UpdateContinuousTriggerFeedback(float GambetaStaminaRatio, float ShotChargeRatio)
{
    if (bTournamentTriggerSafeMode)
    {
        return;
    }

    const float ClampedStamina = FMath::Clamp(GambetaStaminaRatio, 0.0f, 1.0f);
    const float ClampedCharge = FMath::Clamp(ShotChargeRatio, 0.0f, 1.0f);

    // Solo enviamos actualización al bus HID del control si el cambio supera el umbral del 4%
    const float FatigueResistance = (ClampedStamina < 0.30f) ? ((0.30f - ClampedStamina) / 0.30f) : 0.0f;

    if (FMath::Abs(FatigueResistance - LastAppliedStaminaResistance) < 0.04f &&
        FMath::Abs(ClampedCharge - LastAppliedShotTension) < 0.04f)
    {
        return;
    }

    LastAppliedStaminaResistance = FatigueResistance;
    LastAppliedShotTension = ClampedCharge;

    const float CombinedStrength = FMath::Clamp(FMath::Max(FatigueResistance * 0.75f, ClampedCharge), 0.0f, 1.0f);
    if (CombinedStrength <= 0.02f)
    {
        ClearAllHardwareTriggers();
    }
    else
    {
        const float VibrationHz = (ClampedCharge > 0.1f) ? FMath::Lerp(20.0f, 65.0f, ClampedCharge) : 14.0f;
        ApplyDualSenseTriggerEffect(0.20f, 0.90f, CombinedStrength, VibrationHz);
    }
}

void UCombatHapticsSubsystem::ApplyDualSenseTriggerEffect(
    float StartPosition,
    float EndPosition,
    float Strength,
    float FrequencyHz)
{
    if (bTournamentTriggerSafeMode)
    {
        return;
    }

    ULocalPlayer* LP = GetLocalPlayer();
    if (!IsValid(LP))
    {
        return;
    }

    APlayerController* PC = LP->GetPlayerController(GetWorld());
    if (!IsValid(PC))
    {
        return;
    }

    // Modulación de ForceFeedback dinámica compatible con el InputDeviceSubsystem de UE 5.4
    FDynamicForceFeedbackAction::Type ActionType = (Strength > KINDA_SMALL_NUMBER)
        ? FDynamicForceFeedbackAction::Update
        : FDynamicForceFeedbackAction::Stop;

    FDynamicForceFeedbackDetails Details;
    Details.bAffectsLeftLarge = false;
    Details.bAffectsRightLarge = false;
    Details.bAffectsLeftSmall = true;
    Details.bAffectsRightSmall = true;
    Details.Intensity = FMath::Clamp(Strength * (EndPosition - StartPosition) * (FrequencyHz / 60.0f), 0.0f, 1.0f);

    PC->PlayDynamicForceFeedback(Details.Intensity, 0.10f, false, true, false, true, ActionType);
}

void UCombatHapticsSubsystem::ClearAllHardwareTriggers()
{
    LastAppliedStaminaResistance = 0.0f;
    LastAppliedShotTension = 0.0f;

    ULocalPlayer* LP = GetLocalPlayer();
    if (!IsValid(LP))
    {
        return;
    }

    APlayerController* PC = LP->GetPlayerController(GetWorld());
    if (IsValid(PC))
    {
        PC->PlayDynamicForceFeedback(0.0f, 0.0f, true, true, true, true, FDynamicForceFeedbackAction::Stop);
    }
}

void UCombatHapticsSubsystem::SendForceFeedbackEnvelope(
    float LeftLarge,
    float RightSmall,
    float LeftTriggerImpulse,
    float RightTriggerImpulse,
    float DurationSeconds)
{
    ULocalPlayer* LP = GetLocalPlayer();
    if (!IsValid(LP))
    {
        return;
    }

    APlayerController* PC = LP->GetPlayerController(GetWorld());
    if (!IsValid(PC))
    {
        return;
    }

    const float CombinedIntensity = FMath::Clamp(
        FMath::Max4(LeftLarge, RightSmall, LeftTriggerImpulse, RightTriggerImpulse),
        0.0f,
        1.0f);

    PC->PlayDynamicForceFeedback(
        CombinedIntensity,
        FMath::Max(0.016f, DurationSeconds),
        LeftLarge > 0.05f,
        LeftTriggerImpulse > 0.05f,
        RightSmall > 0.05f,
        RightTriggerImpulse > 0.05f,
        FDynamicForceFeedbackAction::Start);
}
