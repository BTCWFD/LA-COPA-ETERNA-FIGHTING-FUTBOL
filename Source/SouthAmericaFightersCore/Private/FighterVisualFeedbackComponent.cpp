// FighterVisualFeedbackComponent.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - AAA Technical Art & Deterministic Visual Feedback Pipeline

#include "FighterVisualFeedbackComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"

UFighterVisualFeedbackComponent::UFighterVisualFeedbackComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    bWantsInitializeComponent = true;
}

void UFighterVisualFeedbackComponent::BeginPlay()
{
    Super::BeginPlay();

    if (!MainBodyMesh && GetOwner())
    {
        MainBodyMesh = GetOwner()->FindComponentByClass<USkeletalMeshComponent>();
        if (MainBodyMesh)
        {
            BaseRelativeLocation = MainBodyMesh->GetRelativeLocation();
        }
    }

    SetCompetitiveAuraState(EVisualCombatAura::None, 0.0f, 1.0f);
}

void UFighterVisualFeedbackComponent::RegisterFighterMeshes(
    USkeletalMeshComponent* InMainBodyMesh,
    const TArray<USkeletalMeshComponent*>& InClothApparelMeshes)
{
    MainBodyMesh = InMainBodyMesh;
    if (MainBodyMesh)
    {
        BaseRelativeLocation = MainBodyMesh->GetRelativeLocation();
    }

    ClothApparelMeshes.Empty(InClothApparelMeshes.Num());
    for (USkeletalMeshComponent* ClothMesh : InClothApparelMeshes)
    {
        if (IsValid(ClothMesh))
        {
            ClothApparelMeshes.Add(ClothMesh);
        }
    }

    SetCompetitiveAuraState(CurrentAura, CurrentAuraIntensity, CurrentInkThicknessScale);
}

void UFighterVisualFeedbackComponent::DeterministicVisualStep(uint32 CurrentFrame)
{
    // 1. Gestión de estabilización de Chaos Cloth tras Rollback o Teleport
    if (ClothTeleportStabilizationFrames > 0)
    {
        --ClothTeleportStabilizationFrames;
        if (ClothTeleportStabilizationFrames == 0)
        {
            if (IsValid(MainBodyMesh))
            {
                MainBodyMesh->ResumeClothingSimulation();
                MainBodyMesh->ForceClothNextUpdateTeleportAndReset();
            }
            for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
            {
                if (IsValid(ClothMesh))
                {
                    ClothMesh->ResumeClothingSimulation();
                    ClothMesh->ForceClothNextUpdateTeleportAndReset();
                }
            }
        }
    }

    // 2. Resolución determinista de Hitstop y Sacudida del Defensor (60Hz)
    if (RemainingHitstopFrames > 0)
    {
        --RemainingHitstopFrames;

        if (IsValid(MainBodyMesh))
        {
            if (RemainingHitstopFrames > 0)
            {
                SetMeshesAnimationPauseState(true);

                if (bCurrentHitstopIsDefender && CurrentShakeAmplitudeCm > KINDA_SMALL_NUMBER)
                {
                    // Alternancia determinista de fase par/impar con amortiguación lineal hacia el final del hitstop
                    const float ParitySign = ((CurrentFrame & 1U) == 0U) ? 1.0f : -1.0f;
                    const float DampingRatio = FMath::Clamp(static_cast<float>(RemainingHitstopFrames) / 14.0f, 0.25f, 1.0f);
                    const float HorizontalOffsetCm = ParitySign * CurrentShakeAmplitudeCm * DampingRatio;
                    const float VerticalMicroJitterCm = (((CurrentFrame >> 1U) & 1U) == 0U ? 0.35f : -0.35f) * DampingRatio;

                    FVector ShakenLocation = BaseRelativeLocation;
                    ShakenLocation.X += HorizontalOffsetCm;
                    ShakenLocation.Z += VerticalMicroJitterCm;
                    MainBodyMesh->SetRelativeLocation(ShakenLocation, false, nullptr, ETeleportType::TeleportPhysics);
                }
            }
            else
            {
                // Fin del Hitstop: restaurar ubicación exacta del Mesh y reanudar evaluación de UAnimInstance
                SetMeshesAnimationPauseState(false);
                MainBodyMesh->SetRelativeLocation(BaseRelativeLocation, false, nullptr, ETeleportType::TeleportPhysics);
                bCurrentHitstopIsDefender = false;
                CurrentShakeAmplitudeCm = 0.0f;
            }
        }
    }
}

void UFighterVisualFeedbackComponent::TriggerHitstopAndShake(int32 FreezeFrames, bool bIsDefender, float ShakeAmplitudeCm)
{
    if (FreezeFrames <= 0)
    {
        return;
    }

    RemainingHitstopFrames = FMath::Max(RemainingHitstopFrames, FreezeFrames);
    bCurrentHitstopIsDefender = bIsDefender;
    CurrentShakeAmplitudeCm = bIsDefender ? FMath::Clamp(ShakeAmplitudeCm, 0.0f, 15.0f) : 0.0f;

    SetMeshesAnimationPauseState(true);

    // En impactos pesados (Counter-Hit / Crush >= 10 frames), impulsar momentáneamente el grosor de tinta Street-Ink
    if (FreezeFrames >= 10)
    {
        SetCompetitiveAuraState(CurrentAura, CurrentAuraIntensity, 1.45f);
    }
}

void UFighterVisualFeedbackComponent::SetCompetitiveAuraState(
    EVisualCombatAura NewAura,
    float Intensity,
    float InkThicknessMultiplier)
{
    CurrentAura = NewAura;
    CurrentAuraIntensity = FMath::Clamp(Intensity, 0.0f, 4.0f);
    CurrentInkThicknessScale = FMath::Clamp(InkThicknessMultiplier, 0.5f, 2.5f);

    FLinearColor TargetRimColor = FLinearColor::Black;
    float EffectiveIntensity = CurrentAuraIntensity;

    switch (NewAura)
    {
    case EVisualCombatAura::Invulnerable_White:
        // Blanco Puro HDR: Reversal / Gambeta Invulnerable Frame 1
        TargetRimColor = FLinearColor(1.00f, 1.00f, 1.00f, 1.0f);
        EffectiveIntensity = FMath::Max(EffectiveIntensity, 1.85f);
        break;

    case EVisualCombatAura::SuperArmor_Gold:
        // Oro Intenso: Hiperarmadura / Garra Charrúa
        TargetRimColor = FLinearColor(1.00f, 0.72f, 0.05f, 1.0f);
        EffectiveIntensity = FMath::Max(EffectiveIntensity, 1.65f);
        break;

    case EVisualCombatAura::GuardCrush_Crimson:
        // Carmesí Violento: Ruptura de Guardia / Tarjeta Roja / Inminente Punish Counter
        TargetRimColor = FLinearColor(0.96f, 0.04f, 0.08f, 1.0f);
        EffectiveIntensity = FMath::Max(EffectiveIntensity, 2.10f);
        break;

    case EVisualCombatAura::AltitudeDebuff_Green:
        // Verde Tóxico / Soroche (Hipoxia de La Paz 3640m)
        TargetRimColor = FLinearColor(0.18f, 0.92f, 0.32f, 1.0f);
        EffectiveIntensity = FMath::Max(EffectiveIntensity, 1.25f);
        break;

    case EVisualCombatAura::None:
    default:
        TargetRimColor = FLinearColor(0.0f, 0.0f, 0.0f, 0.0f);
        EffectiveIntensity = 0.0f;
        break;
    }

    ApplyCustomPrimitiveDataToMeshes(TargetRimColor, EffectiveIntensity, CurrentInkThicknessScale);
}

void UFighterVisualFeedbackComponent::NotifyRollbackOrTeleportSnap(float PositionDeltaSqCm)
{
    // Si la corrección de Rollback o el cambio de posición supera 4.0 cm (16.0 cm^2), congelar Chaos Cloth por 2 frames
    constexpr float TeleportThresholdSqCm = 16.0f;
    if (PositionDeltaSqCm < TeleportThresholdSqCm)
    {
        return;
    }

    ClothTeleportStabilizationFrames = 2;

    if (IsValid(MainBodyMesh))
    {
        MainBodyMesh->ForceClothNextUpdateTeleportAndReset();
        MainBodyMesh->SuspendClothingSimulation();
    }

    for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
    {
        if (IsValid(ClothMesh))
        {
            ClothMesh->ForceClothNextUpdateTeleportAndReset();
            ClothMesh->SuspendClothingSimulation();
        }
    }
}

void UFighterVisualFeedbackComponent::UpdateSweatAndPitchDirt(
    float StaminaRatio,
    bool bTriggeredSlideOrKnockdown,
    float MudIncrement)
{
    const float ClampedStamina = FMath::Clamp(StaminaRatio, 0.0f, 1.0f);

    // El sudor aumenta a medida que el jugador consume Gambeta/Stamina, y nunca retrocede bruscamente durante el round
    const float TargetSweatByExertion = 1.0f - ClampedStamina;
    CurrentSweatAmount = FMath::Max(CurrentSweatAmount, TargetSweatByExertion * 0.85f);
    if (ClampedStamina < 0.35f)
    {
        CurrentSweatAmount = FMath::Clamp(CurrentSweatAmount + 0.015f, 0.0f, 1.0f);
    }

    if (bTriggeredSlideOrKnockdown)
    {
        CurrentPitchMudAmount = FMath::Clamp(CurrentPitchMudAmount + FMath::Max(0.0f, MudIncrement), 0.0f, 1.0f);
    }

    auto WriteWearData = [this](USkeletalMeshComponent* MeshComp)
    {
        if (!IsValid(MeshComp))
        {
            return;
        }
        // CPD[5] = Acumulación de Sudor (0..1), CPD[6] = Acumulación de Barro/Césped (0..1)
        MeshComp->SetCustomPrimitiveDataFloat(5, CurrentSweatAmount);
        MeshComp->SetCustomPrimitiveDataFloat(6, CurrentPitchMudAmount);
    };

    WriteWearData(MainBodyMesh);
    for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
    {
        WriteWearData(ClothMesh);
    }
}

void UFighterVisualFeedbackComponent::CaptureVisualSnapshot(
    uint32 FrameNumber,
    FFighterVisualStateSnapshot& OutSnapshot) const
{
    OutSnapshot.FrameNumber = FrameNumber;
    OutSnapshot.HitstopFramesRemaining = RemainingHitstopFrames;
    OutSnapshot.bIsDefenderInHitstop = bCurrentHitstopIsDefender;
    OutSnapshot.ShakeAmplitudeCm = CurrentShakeAmplitudeCm;
    OutSnapshot.ActiveAura = CurrentAura;
    OutSnapshot.AuraIntensity = CurrentAuraIntensity;
    OutSnapshot.AccumulatedSweat = CurrentSweatAmount;
    OutSnapshot.AccumulatedPitchMud = CurrentPitchMudAmount;
}

void UFighterVisualFeedbackComponent::RestoreVisualSnapshot(const FFighterVisualStateSnapshot& InSnapshot)
{
    RemainingHitstopFrames = InSnapshot.HitstopFramesRemaining;
    bCurrentHitstopIsDefender = InSnapshot.bIsDefenderInHitstop;
    CurrentShakeAmplitudeCm = InSnapshot.ShakeAmplitudeCm;
    CurrentSweatAmount = InSnapshot.AccumulatedSweat;
    CurrentPitchMudAmount = InSnapshot.AccumulatedPitchMud;

    SetCompetitiveAuraState(InSnapshot.ActiveAura, InSnapshot.AuraIntensity, CurrentInkThicknessScale);
    UpdateSweatAndPitchDirt(1.0f - CurrentSweatAmount, false, 0.0f);
    SetMeshesAnimationPauseState(RemainingHitstopFrames > 0);

    if (RemainingHitstopFrames <= 0 && IsValid(MainBodyMesh))
    {
        MainBodyMesh->SetRelativeLocation(BaseRelativeLocation, false, nullptr, ETeleportType::TeleportPhysics);
    }
}

void UFighterVisualFeedbackComponent::SetArtStyleMode(ECombatArtStyleMode NewArtStyleMode)
{
    CurrentArtStyleMode = NewArtStyleMode;
    const float StyleValue = (CurrentArtStyleMode == ECombatArtStyleMode::RenaissanceSfumato) ? 1.0f : 0.0f;

    if (IsValid(MainBodyMesh))
    {
        MainBodyMesh->SetCustomPrimitiveDataFloat(7, StyleValue);
    }
    for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
    {
        if (IsValid(ClothMesh))
        {
            ClothMesh->SetCustomPrimitiveDataFloat(7, StyleValue);
        }
    }
}

void UFighterVisualFeedbackComponent::ApplyCustomPrimitiveDataToMeshes(
    const FLinearColor& RimColor,
    float RimIntensity,
    float InkScale)
{
    auto WriteShaderCPD = [&](USkeletalMeshComponent* MeshComp)
    {
        if (!IsValid(MeshComp))
        {
            return;
        }
        // Índices 0, 1, 2: Color RGB del Rim Competitivo
        // Índice 3: Intensidad del Rim Competitivo
        // Índice 4: Escala dinámica de grosor de tinta (Ink Outline Multiplier)
        // Índice 7: ArtStyleMode (0.0 = Street-Ink, 1.0 = Renaissance Sfumato Da Vinci)
        MeshComp->SetCustomPrimitiveDataVector3(0, FVector(RimColor.R, RimColor.G, RimColor.B));
        MeshComp->SetCustomPrimitiveDataFloat(3, RimIntensity);
        MeshComp->SetCustomPrimitiveDataFloat(4, InkScale);
        MeshComp->SetCustomPrimitiveDataFloat(7, (CurrentArtStyleMode == ECombatArtStyleMode::RenaissanceSfumato) ? 1.0f : 0.0f);
    };

    WriteShaderCPD(MainBodyMesh);
    for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
    {
        WriteShaderCPD(ClothMesh);
    }
}

void UFighterVisualFeedbackComponent::SetMeshesAnimationPauseState(bool bPaused)
{
    if (IsValid(MainBodyMesh))
    {
        MainBodyMesh->bPauseAnims = bPaused;
    }
    for (const TObjectPtr<USkeletalMeshComponent>& ClothMesh : ClothApparelMeshes)
    {
        if (IsValid(ClothMesh))
        {
            ClothMesh->bPauseAnims = bPaused;
        }
    }
}
