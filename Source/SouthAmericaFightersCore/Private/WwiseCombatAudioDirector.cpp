// WwiseCombatAudioDirector.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Wwise Interactive Music, Stadium Crowd RTPCs & South American Broadcast Commentary

#include "WwiseCombatAudioDirector.h"

#if WITH_WWISE
#include "AkAudioDevice.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogCombatAudioDirector, Log, All);

namespace CombatAudioConstants
{
    // Altitud canónica del Estadio Hernando Siles (La Paz - 3600m), alineada con DT_StagesCONMEBOL.json y GDD.
    static constexpr float LaPazAltitudeMeters = 3600.0f;
}

void UWwiseCombatAudioDirector::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    CurrentMatchExcitement = 15.0f;
    CurrentCrowdMomentum = 0.0f;
    ConsecutiveOleCount = 0;
    LastOleFrame = 0;
    RecentlyTriggeredEventFrames.Reset();
}

void UWwiseCombatAudioDirector::Deinitialize()
{
    RecentlyTriggeredEventFrames.Reset();
    Super::Deinitialize();
}

void UWwiseCombatAudioDirector::InitializeMatchAudioEnvironment(
    FName StageAcousticSwitch,
    FName LocalHomeFighterID,
    float AltitudeMeters)
{
    CurrentStageSwitch = StageAcousticSwitch;
    HomeFighterID = LocalHomeFighterID;

    const FString StageNameStr = StageAcousticSwitch.ToString();
    const bool bIsLaPazStage =
        StageAcousticSwitch == TEXT("STAGE_HERNANDO_SILES") ||
        StageAcousticSwitch == TEXT("Stage_LaPaz_3600m") ||
        StageNameStr.Contains(TEXT("HERNANDO_SILES")) ||
        StageNameStr.Contains(TEXT("LaPaz"));

    if (bIsLaPazStage && (AltitudeMeters <= 0.0f || FMath::IsNearlyEqual(AltitudeMeters, 3640.0f, 1.0f)))
    {
        StageAltitudeMeters = CombatAudioConstants::LaPazAltitudeMeters; // 3600m
    }
    else
    {
        StageAltitudeMeters = FMath::Max(0.0f, AltitudeMeters);
    }

    CurrentMatchExcitement = 20.0f;
    CurrentCrowdMomentum = 0.0f;
    ConsecutiveOleCount = 0;
    LastOleFrame = 0;
    CurrentActiveCommentary = FActiveCommentaryLine();
    RecentlyTriggeredEventFrames.Reset();

    SetWwiseSwitch(TEXT("Stage_Venue"), *StageAcousticSwitch.ToString());
    SetWwiseState(TEXT("Acoustic_Environment"), TEXT("Pitch_OpenAir"));
    SetWwiseState(TEXT("Music_Combat_State"), TEXT("Round_Intro_Percussion"));

    SetWwiseGlobalRTPC(TEXT("RTPC_Stage_Altitude_Meters"), StageAltitudeMeters, 0);
    SetWwiseGlobalRTPC(TEXT("RTPC_Match_Excitement"), CurrentMatchExcitement, 0);
    SetWwiseGlobalRTPC(TEXT("RTPC_Crowd_Momentum"), CurrentCrowdMomentum, 0);
    SetWwiseGlobalRTPC(TEXT("RTPC_Ole_Combo_Pitch"), 0.0f, 0);

    PostWwiseGlobalEvent(TEXT("Play_Stadium_Ambience_Master"));
    PostWwiseGlobalEvent(TEXT("Play_Interactive_Match_Music"));
}

void UWwiseCombatAudioDirector::UpdateDeterministicAudioFrame(
    uint32 CurrentFrame,
    bool bIsRollbackReSimulation,
    float P1HealthRatio,
    float P2HealthRatio,
    int32 RemainingSeconds,
    int32 ActiveComboHits,
    int32 MomentumBiasP1vsP2)
{
    // Durante re-simulación de Rollback no re-modulamos buses RTPC para evitar jitter en el thread de audio
    if (bIsRollbackReSimulation)
    {
        return;
    }

    const float ClampedP1HP = FMath::Clamp(P1HealthRatio, 0.0f, 1.0f);
    const float ClampedP2HP = FMath::Clamp(P2HealthRatio, 0.0f, 1.0f);

    // 1. Cálculo de RTPC_Match_Excitement (0.0 a 100.0)
    // Sube conforme baja la vida de ambos peleadores, aumenta el combo actual o se agota el reloj (<15s)
    const float MissingHealthFactor = (1.0f - (ClampedP1HP * 0.5f + ClampedP2HP * 0.5f)) * 55.0f;
    const float CriticalClutchBonus = (ClampedP1HP < 0.22f || ClampedP2HP < 0.22f) ? 20.0f : 0.0f;
    const float ComboBonus = FMath::Min(static_cast<float>(ActiveComboHits) * 3.5f, 25.0f);
    const float TimePressureBonus = (RemainingSeconds <= 15) ? 15.0f : 0.0f;

    const float TargetExcitement = FMath::Clamp(
        15.0f + MissingHealthFactor + CriticalClutchBonus + ComboBonus + TimePressureBonus,
        0.0f,
        100.0f);

    // Suavizado determinista por frame (60Hz)
    CurrentMatchExcitement = FMath::FInterpTo(CurrentMatchExcitement, TargetExcitement, 1.0f / 60.0f, 4.5f);
    SetWwiseGlobalRTPC(TEXT("RTPC_Match_Excitement"), CurrentMatchExcitement, 16);

    // Transición automática de capas musicales según la tensión del partido
    if (CurrentMatchExcitement >= 82.0f)
    {
        SetWwiseState(TEXT("Music_Combat_State"), TEXT("Climax_Final_Minutes"));
    }
    else if (CurrentMatchExcitement >= 45.0f)
    {
        SetWwiseState(TEXT("Music_Combat_State"), TEXT("MidMatch_Brass_And_Chants"));
    }

    // 2. Cálculo de RTPC_Crowd_Momentum (-100.0 a +100.0)
    const float HealthAdvantageBias = (ClampedP1HP - ClampedP2HP) * 65.0f;
    const float TargetMomentum = FMath::Clamp(
        HealthAdvantageBias + static_cast<float>(MomentumBiasP1vsP2),
        -100.0f,
        100.0f);

    CurrentCrowdMomentum = FMath::FInterpTo(CurrentCrowdMomentum, TargetMomentum, 1.0f / 60.0f, 3.0f);
    SetWwiseGlobalRTPC(TEXT("RTPC_Crowd_Momentum"), CurrentCrowdMomentum, 32);

    // 3. Expiración de la ventana de "¡OOOO-LÉ!" tras 240 frames (4.0 segundos sin nueva gambeta)
    if (ConsecutiveOleCount > 0 && CurrentFrame > LastOleFrame && (CurrentFrame - LastOleFrame) > 240U)
    {
        ConsecutiveOleCount = 0;
        SetWwiseGlobalRTPC(TEXT("RTPC_Ole_Combo_Pitch"), 0.0f, 250);
    }

    // 4. Liberación del canal de relato cuando finaliza la duración estimada de la locución activa
    if (CurrentActiveCommentary.Priority != ECommentaryPriority::None)
    {
        const uint32 ElapsedFrames = (CurrentFrame >= CurrentActiveCommentary.TriggerFrame)
            ? (CurrentFrame - CurrentActiveCommentary.TriggerFrame)
            : 0U;

        if (ElapsedFrames >= static_cast<uint32>(CurrentActiveCommentary.EstimatedDurationFrames))
        {
            CurrentActiveCommentary = FActiveCommentaryLine();
        }
    }
}

bool UWwiseCombatAudioDirector::TriggerLiveCommentaryEvent(
    FName WwiseEventName,
    ECommentaryPriority Priority,
    uint32 CurrentFrame,
    int32 DurationFrames,
    bool bIsRollbackReSimulation)
{
    if (WwiseEventName.IsNone() || Priority == ECommentaryPriority::None)
    {
        return false;
    }

    // Filtro anti-duplicación de Rollback: si este mismo evento ya se disparó en los últimos 8 frames, lo ignoramos
    if (const uint32* LastTriggeredFrame = RecentlyTriggeredEventFrames.Find(WwiseEventName))
    {
        const uint32 FrameDiff = (CurrentFrame >= *LastTriggeredFrame)
            ? (CurrentFrame - *LastTriggeredFrame)
            : (*LastTriggeredFrame - CurrentFrame);

        if (FrameDiff <= 8U)
        {
            return false;
        }
    }

    if (bIsRollbackReSimulation && Priority < ECommentaryPriority::CriticalMoment)
    {
        return false;
    }

    // Resolución de Prioridad de Relatores
    if (CurrentActiveCommentary.Priority != ECommentaryPriority::None)
    {
        if (static_cast<uint8>(Priority) <= static_cast<uint8>(CurrentActiveCommentary.Priority))
        {
            // Una línea de igual o mayor jerarquía sigue sonando: descartamos la nueva para no pisar al relator
            return false;
        }

        // Interrupción legítima por un evento de mayor prioridad (ej. NeutralChatter -> CriticalMoment / UltimateGoalKO)
        // Disparamos el Interrupt Stinger ("¡PERO CUIDADO EN EL ÁREA!", "¡ATENCIÓN QUE LE PEGA!") antes del nuevo evento
        PostWwiseGlobalEvent(TEXT("Stop_Active_Commentary_Immediate"));

        if (Priority == ECommentaryPriority::UltimateGoalKO)
        {
            PostWwiseGlobalEvent(TEXT("Play_Commentary_Stinger_GoalInterrupt"));
        }
        else
        {
            PostWwiseGlobalEvent(TEXT("Play_Commentary_Stinger_ActionInterrupt"));
        }
    }

    CurrentActiveCommentary.EventName = WwiseEventName;
    CurrentActiveCommentary.Priority = Priority;
    CurrentActiveCommentary.TriggerFrame = CurrentFrame;
    CurrentActiveCommentary.EstimatedDurationFrames = FMath::Max(15, DurationFrames);

    RecentlyTriggeredEventFrames.Add(WwiseEventName, CurrentFrame);
    PostWwiseGlobalEvent(*WwiseEventName.ToString());

    return true;
}

void UWwiseCombatAudioDirector::NotifyStageWallBreakTransition(FName NewZoneStateName, uint32 CurrentFrame)
{
    // Dispara el estallido metálico del alambrado / vallas publicitarias y cambia la respuesta de impulso (IR Reverb)
    PostWwiseGlobalEvent(TEXT("Play_Stage_WallBreak_FenceShatter_LFE"));

    if (!NewZoneStateName.IsNone())
    {
        SetWwiseState(TEXT("Acoustic_Environment"), *NewZoneStateName.ToString());
    }

    TriggerLiveCommentaryEvent(
        FName(TEXT("Play_VO_Commentary_WallBreak_Shatter")),
        ECommentaryPriority::CriticalMoment,
        CurrentFrame,
        110,
        false);
}

void UWwiseCombatAudioDirector::RegisterSuccessfulGambetaForCrowd(
    uint32 CurrentFrame,
    int32 PerformingPlayerIndex)
{
    if (CurrentFrame > LastOleFrame && (CurrentFrame - LastOleFrame) <= 240U)
    {
        ConsecutiveOleCount = FMath::Min(ConsecutiveOleCount + 1, 8);
    }
    else
    {
        ConsecutiveOleCount = 1;
    }

    LastOleFrame = CurrentFrame;

    // Cada "¡OOOO-LÉ!" consecutivo sube +100 cents (1 semitono, hasta +700 cents) y aumenta la euforia del estadio
    const float OlePitchCents = static_cast<float>((ConsecutiveOleCount - 1) * 100);
    SetWwiseGlobalRTPC(TEXT("RTPC_Ole_Combo_Pitch"), OlePitchCents, 10);
    PostWwiseGlobalEvent(TEXT("Play_Crowd_Chant_Ole_Swell"));

    const float MomentumStep = (PerformingPlayerIndex == 0) ? 14.0f : -14.0f;
    CurrentCrowdMomentum = FMath::Clamp(CurrentCrowdMomentum + MomentumStep, -100.0f, 100.0f);
    SetWwiseGlobalRTPC(TEXT("RTPC_Crowd_Momentum"), CurrentCrowdMomentum, 20);
}

void UWwiseCombatAudioDirector::SetWwiseGlobalRTPC(const TCHAR* RTPCName, float Value, int32 InterpolationMs)
{
#if WITH_WWISE
    if (FAkAudioDevice* AkDevice = FAkAudioDevice::Get())
    {
        AkDevice->SetRTPCValue(RTPCName, Value, InterpolationMs, nullptr);
    }
#else
    UE_LOG(LogCombatAudioDirector, VeryVerbose, TEXT("[WwiseBridge] RTPC %s = %.2f (Interp %dms)"), RTPCName, Value, InterpolationMs);
#endif
}

void UWwiseCombatAudioDirector::SetWwiseState(const TCHAR* StateGroup, const TCHAR* StateValue)
{
#if WITH_WWISE
    if (FAkAudioDevice* AkDevice = FAkAudioDevice::Get())
    {
        AkDevice->SetState(StateGroup, StateValue);
    }
#else
    UE_LOG(LogCombatAudioDirector, Verbose, TEXT("[WwiseBridge] State %s -> %s"), StateGroup, StateValue);
#endif
}

void UWwiseCombatAudioDirector::SetWwiseSwitch(const TCHAR* SwitchGroup, const TCHAR* SwitchValue)
{
#if WITH_WWISE
    if (FAkAudioDevice* AkDevice = FAkAudioDevice::Get())
    {
        AkDevice->SetSwitch(SwitchGroup, SwitchValue, nullptr);
    }
#else
    UE_LOG(LogCombatAudioDirector, Verbose, TEXT("[WwiseBridge] Switch %s -> %s"), SwitchGroup, SwitchValue);
#endif
}

void UWwiseCombatAudioDirector::PostWwiseGlobalEvent(const TCHAR* EventName)
{
#if WITH_WWISE
    if (FAkAudioDevice* AkDevice = FAkAudioDevice::Get())
    {
        AkDevice->PostEvent(EventName, nullptr);
    }
#else
    UE_LOG(LogCombatAudioDirector, Verbose, TEXT("[WwiseBridge] PostEvent: %s"), EventName);
#endif
}
