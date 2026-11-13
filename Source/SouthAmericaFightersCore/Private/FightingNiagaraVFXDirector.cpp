// FightingNiagaraVFXDirector.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Deterministic Niagara VFX Subsystem, Competitive Hit/Block Encoding & Elemental Ball Trails

#include "FightingNiagaraVFXDirector.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

namespace NiagaraCompetitiveUserParams
{
    static const FName DeterministicSeed(TEXT("User.DeterministicSeed"));
    static const FName PrimaryImpactColor(TEXT("User.PrimaryImpactColor"));
    static const FName SecondaryFlashColor(TEXT("User.SecondaryFlashColor"));
    static const FName HitVelocityVector(TEXT("User.HitVelocityVector"));
    static const FName GrassBladeBurstCount(TEXT("User.GrassBladeBurstCount"));
    static const FName ShockwaveRingScale(TEXT("User.ShockwaveRingScale"));
    static const FName IsPlusOnBlock(TEXT("User.bIsPlusOnBlock"));
    static const FName FrameAdvantageValue(TEXT("User.FrameAdvantageValue"));
    static const FName PlusFrameFlashHz(TEXT("User.PlusFrameFlashFrequencyHz"));

    // Parámetros de NS_SuperBall_Trail
    static const FName BallElementID(TEXT("User.BallElementID"));
    static const FName BallPrimaryColor(TEXT("User.BallPrimaryColor"));
    static const FName BallSecondaryColor(TEXT("User.BallSecondaryColor"));
    static const FName BallVelocity(TEXT("User.BallVelocityCmPerSec"));
    static const FName BallSpinRPM(TEXT("User.BallSpinRPM"));
    static const FName VacuumImplosionStrength(TEXT("User.VacuumImplosionStrength"));
    static const FName LightningBranchCount(TEXT("User.LightningBranchCount"));
}

void UFightingNiagaraVFXDirector::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    SpawnHistoryRingBuffer.Reserve(64);
    ActiveGhostMeshes.Reserve(16);
    StreetInkImpactFramesRemaining = 0;
    CurrentBallElement = ESouthAmericaBallElement::None;
    CurrentBallTrailFade = 0.0f;
}

void UFightingNiagaraVFXDirector::Deinitialize()
{
    if (IsValid(ActiveSuperBallTrailComponent))
    {
        ActiveSuperBallTrailComponent->DeactivateImmediate();
        ActiveSuperBallTrailComponent = nullptr;
    }

    SpawnHistoryRingBuffer.Empty();
    ActiveGhostMeshes.Empty();

    Super::Deinitialize();
}

void UFightingNiagaraVFXDirector::RegisterCombatNiagaraTemplates(
    UNiagaraSystem* InHitSparkSystem,
    UNiagaraSystem* InBlockShieldHexSystem,
    UNiagaraSystem* InGambetaParryRingSystem,
    UNiagaraSystem* InSuperBallTrailSystem,
    UMaterialInterface* InGhostTrailMaterial)
{
    HitSparkTemplate = InHitSparkSystem;
    BlockShieldHexTemplate = InBlockShieldHexSystem;
    GambetaParryRingTemplate = InGambetaParryRingSystem;
    SuperBallTrailTemplate = InSuperBallTrailSystem;
    GhostTrailMaterialTemplate = InGhostTrailMaterial;
}

UNiagaraComponent* UFightingNiagaraVFXDirector::SpawnDeterministicImpactVFX(
    uint32 CurrentFrame,
    ECombatImpactVFXType ImpactType,
    const FVector& ImpactLocationCm,
    const FVector& HitVelocityVectorCmPerSec,
    int32 FrameAdvantageOnBlock,
    bool bIsRollbackReSimulation)
{
    UWorld* World = GetWorld();
    if (!IsValid(World))
    {
        return nullptr;
    }

    // Regla Competitiva: Si es un bloqueo estándar pero el ataque tiene ventaja positiva (ej. Bati-Cañonazo Cargado +4),
    // forzar automáticamente el estado visual BlockPlusFrameAdvantage (Escudo Cian con parpadeo Amarillo/Naranja)
    ECombatImpactVFXType EffectiveType = ImpactType;
    if (EffectiveType == ECombatImpactVFXType::BlockStandard && FrameAdvantageOnBlock > 0)
    {
        EffectiveType = ECombatImpactVFXType::BlockPlusFrameAdvantage;
    }

    // 1. Deduplicación determinista para Rollback: si este impacto exacto ya está activo, no re-instanciarlo
    const uint32 EventHash = ComputeImpactEventHash(EffectiveType, ImpactLocationCm, CurrentFrame);
    for (const FSpawnedVFXRollbackRecord& Record : SpawnHistoryRingBuffer)
    {
        if (Record.EventHash == EventHash && Record.ActiveComponent.IsValid())
        {
            return Record.ActiveComponent.Get();
        }
    }

    // 2. Selección del template Niagara según el tipo de evento
    UNiagaraSystem* SelectedTemplate = nullptr;
    switch (EffectiveType)
    {
    case ECombatImpactVFXType::HitNormal:
    case ECombatImpactVFXType::CounterHit:
        SelectedTemplate = HitSparkTemplate;
        break;

    case ECombatImpactVFXType::BlockStandard:
    case ECombatImpactVFXType::BlockPlusFrameAdvantage:
        SelectedTemplate = BlockShieldHexTemplate;
        break;

    case ECombatImpactVFXType::GambetaParryPerfect:
        SelectedTemplate = GambetaParryRingTemplate;
        break;
    }

    const FVector SafeDirection = HitVelocityVectorCmPerSec.IsNearlyZero()
        ? FVector::ForwardVector
        : HitVelocityVectorCmPerSec.GetSafeNormal();
    const FRotator ImpactOrientation = SafeDirection.Rotation();

    UNiagaraComponent* SpawnedComp = nullptr;
    if (IsValid(SelectedTemplate))
    {
        SpawnedComp = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
            World,
            SelectedTemplate,
            ImpactLocationCm,
            ImpactOrientation,
            FVector::OneVector,
            true,
            false,
            ENCPoolMethod::AutoRelease,
            true);
    }

    // Si estamos en Counter-Hit o Gambeta Parry Perfecto, activar el pulso de 3 frames PP_StreetInk_Impact
    if (!bIsRollbackReSimulation &&
        (EffectiveType == ECombatImpactVFXType::CounterHit || EffectiveType == ECombatImpactVFXType::GambetaParryPerfect))
    {
        StreetInkImpactFramesRemaining = 3;
        if (APlayerController* PC = World->GetFirstPlayerController())
        {
            FVector2D ScreenPos = FVector2D::ZeroVector;
            int32 ViewportX = 1920, ViewportY = 1080;
            PC->GetViewportSize(ViewportX, ViewportY);
            if (PC->ProjectWorldLocationToScreen(ImpactLocationCm, ScreenPos) && ViewportX > 0 && ViewportY > 0)
            {
                LastHeavyImpactScreenUV = FVector2D(
                    FMath::Clamp(ScreenPos.X / static_cast<float>(ViewportX), 0.0f, 1.0f),
                    FMath::Clamp(ScreenPos.Y / static_cast<float>(ViewportY), 0.0f, 1.0f));
            }
        }
    }

    if (!IsValid(SpawnedComp))
    {
        return nullptr;
    }

    // 3. Inyección de Semilla Determinista (`RandomSeed = CurrentFrame`) y Codificación Cromática Competitiva
    SpawnedComp->SetIntParameter(NiagaraCompetitiveUserParams::DeterministicSeed, static_cast<int32>(CurrentFrame));
    SpawnedComp->SetVectorParameter(NiagaraCompetitiveUserParams::HitVelocityVector, HitVelocityVectorCmPerSec);

    switch (EffectiveType)
    {
    case ECombatImpactVFXType::HitNormal:
        // Chispa dorada cálida + 18 briznas de césped orientadas según el vector de golpe
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::PrimaryImpactColor, FLinearColor(1.00f, 0.78f, 0.12f, 1.0f));
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::SecondaryFlashColor, FLinearColor(0.24f, 0.65f, 0.14f, 1.0f));
        SpawnedComp->SetIntParameter(NiagaraCompetitiveUserParams::GrassBladeBurstCount, 18);
        SpawnedComp->SetFloatParameter(NiagaraCompetitiveUserParams::ShockwaveRingScale, 1.0f);
        break;

    case ECombatImpactVFXType::CounterHit:
        // Estallido carmesí violento + onda de choque expansiva + 32 briznas de pasto/tierra arrancadas
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::PrimaryImpactColor, FLinearColor(0.98f, 0.03f, 0.08f, 1.0f));
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::SecondaryFlashColor, FLinearColor(1.00f, 0.85f, 0.20f, 1.0f));
        SpawnedComp->SetIntParameter(NiagaraCompetitiveUserParams::GrassBladeBurstCount, 32);
        SpawnedComp->SetFloatParameter(NiagaraCompetitiveUserParams::ShockwaveRingScale, 1.85f);
        break;

    case ECombatImpactVFXType::BlockStandard:
        // Escudo hexagonal azul cian estable (el defensor tiene turno o ventaja favorable)
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::PrimaryImpactColor, FLinearColor(0.04f, 0.82f, 1.00f, 1.0f));
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::SecondaryFlashColor, FLinearColor(0.02f, 0.45f, 0.88f, 1.0f));
        SpawnedComp->SetBoolParameter(NiagaraCompetitiveUserParams::IsPlusOnBlock, false);
        SpawnedComp->SetIntParameter(NiagaraCompetitiveUserParams::FrameAdvantageValue, FrameAdvantageOnBlock);
        SpawnedComp->SetFloatParameter(NiagaraCompetitiveUserParams::PlusFrameFlashHz, 0.0f);
        break;

    case ECombatImpactVFXType::BlockPlusFrameAdvantage:
        // Escudo hexagonal azul cian que parpadea agresivamente en Amarillo/Naranja (Plus on Block: ej. Bati-Cañonazo Cargado +4)
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::PrimaryImpactColor, FLinearColor(0.04f, 0.82f, 1.00f, 1.0f));
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::SecondaryFlashColor, FLinearColor(1.00f, 0.58f, 0.02f, 1.0f));
        SpawnedComp->SetBoolParameter(NiagaraCompetitiveUserParams::IsPlusOnBlock, true);
        SpawnedComp->SetIntParameter(NiagaraCompetitiveUserParams::FrameAdvantageValue, FrameAdvantageOnBlock);
        SpawnedComp->SetFloatParameter(NiagaraCompetitiveUserParams::PlusFrameFlashHz, 30.0f);
        break;

    case ECombatImpactVFXType::GambetaParryPerfect:
        // Anillo blanco puro / oro solar de Parry Perfecto
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::PrimaryImpactColor, FLinearColor(1.00f, 1.00f, 1.00f, 1.0f));
        SpawnedComp->SetColorParameter(NiagaraCompetitiveUserParams::SecondaryFlashColor, FLinearColor(1.00f, 0.76f, 0.10f, 1.0f));
        SpawnedComp->SetFloatParameter(NiagaraCompetitiveUserParams::ShockwaveRingScale, 2.10f);
        break;
    }

    SpawnedComp->Activate(true);

    FSpawnedVFXRollbackRecord NewRecord;
    NewRecord.SpawnFrame = CurrentFrame;
    NewRecord.EventHash = EventHash;
    NewRecord.ActiveComponent = SpawnedComp;

    if (SpawnHistoryRingBuffer.Num() >= 64)
    {
        SpawnHistoryRingBuffer.RemoveAt(0, 1, EAllowShrinking::No);
    }
    SpawnHistoryRingBuffer.Add(NewRecord);

    return SpawnedComp;
}

void UFightingNiagaraVFXDirector::SpawnGambetaGhostMeshTrail(
    uint32 CurrentFrame,
    USkeletalMeshComponent* SourceFighterMesh,
    const FLinearColor& GhostTint,
    float LifetimeSeconds)
{
    if (!IsValid(SourceFighterMesh) || !IsValid(SourceFighterMesh->GetSkeletalMeshAsset()))
    {
        return;
    }

    AActor* OwnerActor = SourceFighterMesh->GetOwner();
    if (!IsValid(OwnerActor))
    {
        return;
    }

    UPoseableMeshComponent* GhostPoseMesh = NewObject<UPoseableMeshComponent>(OwnerActor);
    if (!IsValid(GhostPoseMesh))
    {
        return;
    }

    GhostPoseMesh->SetSkinnedAssetAndUpdate(SourceFighterMesh->GetSkeletalMeshAsset());
    GhostPoseMesh->SetWorldTransform(SourceFighterMesh->GetComponentTransform());
    GhostPoseMesh->CopyPoseFromSkeletalComponent(SourceFighterMesh);
    GhostPoseMesh->SetCastShadow(false);
    GhostPoseMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    if (IsValid(GhostTrailMaterialTemplate))
    {
        UMaterialInstanceDynamic* GhostMID = UMaterialInstanceDynamic::Create(GhostTrailMaterialTemplate, GhostPoseMesh);
        if (IsValid(GhostMID))
        {
            GhostMID->SetVectorParameterValue(TEXT("GhostColorTint"), GhostTint);
            GhostMID->SetScalarParameterValue(TEXT("GhostOpacity"), GhostTint.A);

            const int32 NumMats = GhostPoseMesh->GetNumMaterials();
            for (int32 MatIdx = 0; MatIdx < NumMats; ++MatIdx)
            {
                GhostPoseMesh->SetMaterial(MatIdx, GhostMID);
            }
        }
    }

    GhostPoseMesh->RegisterComponentWithWorld(GetWorld());

    FActiveGhostMeshEntry Entry;
    Entry.PoseableMesh = GhostPoseMesh;
    Entry.SpawnFrame = CurrentFrame;
    Entry.DurationFrames = static_cast<uint32>(FMath::Max(4, FMath::RoundToInt(LifetimeSeconds * 60.0f)));
    ActiveGhostMeshes.Add(Entry);
}

void UFightingNiagaraVFXDirector::UpdateSuperBallElementalTrail(
    uint32 CurrentFrame,
    ESouthAmericaBallElement BallElement,
    const FVector& BallPositionCm,
    const FVector& BallVelocityCmPerSec,
    float SpinRateRPM)
{
    PreviousBallPosCm = CurrentBallPosCm.IsZero() ? BallPositionCm : CurrentBallPosCm;
    CurrentBallPosCm = BallPositionCm;
    CurrentBallElement = BallElement;

    if (BallElement == ESouthAmericaBallElement::None)
    {
        CurrentBallTrailFade = FMath::Max(0.0f, CurrentBallTrailFade - 0.08f);
        if (IsValid(ActiveSuperBallTrailComponent))
        {
            ActiveSuperBallTrailComponent->Deactivate();
        }
        return;
    }

    CurrentBallTrailFade = 1.0f;
    CurrentBallCavityRadiusCm = 145.0f;

    UWorld* World = GetWorld();
    if (IsValid(World) && IsValid(SuperBallTrailTemplate) && !IsValid(ActiveSuperBallTrailComponent))
    {
        ActiveSuperBallTrailComponent = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
            World,
            SuperBallTrailTemplate,
            BallPositionCm,
            BallVelocityCmPerSec.Rotation(),
            FVector::OneVector,
            false,
            true,
            ENCPoolMethod::None,
            true);
    }

    FLinearColor PrimaryColor = FLinearColor::White;
    FLinearColor SecondaryColor = FLinearColor::White;
    float VacuumImplosion = 0.0f;
    int32 LightningBranches = 0;

    switch (BallElement)
    {
    case ESouthAmericaBallElement::Brazil_CanarinhaSpinRibbons:
        // Brasil: Cintas Verde-Amarela con alto efecto Magnus rotacional
        PrimaryColor = FLinearColor(1.00f, 0.84f, 0.00f, 1.0f);   // Amarelo Ouro
        SecondaryColor = FLinearColor(0.00f, 0.68f, 0.24f, 1.0f); // Verde Bandeira
        break;

    case ESouthAmericaBallElement::Argentina_AlbicelesteSupersonicFire:
        // Argentina: Fuego Azul Celeste Supersónico con núcleo solar blanco
        PrimaryColor = FLinearColor(0.22f, 0.76f, 1.00f, 1.0f);   // Celeste Solar HDR
        SecondaryColor = FLinearColor(1.00f, 0.98f, 0.88f, 1.0f); // Sol de Mayo
        CurrentBallCavityRadiusCm = 175.0f;
        break;

    case ESouthAmericaBallElement::Bolivia_AltiplanoEmeraldVacuum:
        // Bolivia: Distorsión de Vacío Verde Esmeralda (3600m de altitud)
        PrimaryColor = FLinearColor(0.06f, 0.94f, 0.38f, 1.0f);   // Esmeralda Andino
        SecondaryColor = FLinearColor(0.01f, 0.14f, 0.08f, 1.0f); // Vacío Hipóxico
        VacuumImplosion = -420.0f;
        CurrentBallCavityRadiusCm = 190.0f;
        break;

    case ESouthAmericaBallElement::Venezuela_VinotintoLightning:
        // Venezuela: Relámpago Vinotinto y arcos voltaicos dorados
        PrimaryColor = FLinearColor(0.58f, 0.04f, 0.16f, 1.0f);   // Vinotinto Eléctrico
        SecondaryColor = FLinearColor(1.00f, 0.78f, 0.15f, 1.0f); // Arco Voltaico Dorado
        LightningBranches = 14;
        break;

    case ESouthAmericaBallElement::Uruguay_CharruaObsidianMeteor:
        // Uruguay: Meteoro Celeste y Obsidiana
        PrimaryColor = FLinearColor(0.18f, 0.62f, 0.96f, 1.0f);
        SecondaryColor = FLinearColor(0.04f, 0.05f, 0.08f, 1.0f);
        break;

    case ESouthAmericaBallElement::Colombia_CafeteroSolarVortex:
    default:
        // Colombia: Vórtice Solar Tricolor
        PrimaryColor = FLinearColor(1.00f, 0.76f, 0.02f, 1.0f);
        SecondaryColor = FLinearColor(0.92f, 0.08f, 0.12f, 1.0f);
        break;
    }

    CurrentBallGlowColor = PrimaryColor;

    if (IsValid(ActiveSuperBallTrailComponent))
    {
        ActiveSuperBallTrailComponent->SetWorldLocationAndRotation(BallPositionCm, BallVelocityCmPerSec.Rotation());
        ActiveSuperBallTrailComponent->SetIntParameter(NiagaraCompetitiveUserParams::DeterministicSeed, static_cast<int32>(CurrentFrame));
        ActiveSuperBallTrailComponent->SetIntParameter(NiagaraCompetitiveUserParams::BallElementID, static_cast<int32>(BallElement));
        ActiveSuperBallTrailComponent->SetColorParameter(NiagaraCompetitiveUserParams::BallPrimaryColor, PrimaryColor);
        ActiveSuperBallTrailComponent->SetColorParameter(NiagaraCompetitiveUserParams::BallSecondaryColor, SecondaryColor);
        ActiveSuperBallTrailComponent->SetVectorParameter(NiagaraCompetitiveUserParams::BallVelocity, BallVelocityCmPerSec);
        ActiveSuperBallTrailComponent->SetFloatParameter(NiagaraCompetitiveUserParams::BallSpinRPM, SpinRateRPM);
        ActiveSuperBallTrailComponent->SetFloatParameter(NiagaraCompetitiveUserParams::VacuumImplosionStrength, VacuumImplosion);
        ActiveSuperBallTrailComponent->SetIntParameter(NiagaraCompetitiveUserParams::LightningBranchCount, LightningBranches);

        if (!ActiveSuperBallTrailComponent->IsActive())
        {
            ActiveSuperBallTrailComponent->Activate(true);
        }
    }
}

void UFightingNiagaraVFXDirector::PruneSpeculativeVFXFromRollback(uint32 RollbackTargetFrame)
{
    for (int32 Idx = SpawnHistoryRingBuffer.Num() - 1; Idx >= 0; --Idx)
    {
        if (SpawnHistoryRingBuffer[Idx].SpawnFrame >= RollbackTargetFrame)
        {
            if (SpawnHistoryRingBuffer[Idx].ActiveComponent.IsValid())
            {
                SpawnHistoryRingBuffer[Idx].ActiveComponent->DeactivateImmediate();
            }
            SpawnHistoryRingBuffer.RemoveAt(Idx, 1, EAllowShrinking::No);
        }
    }
}

void UFightingNiagaraVFXDirector::TickDeterministicVFXFrame(uint32 CurrentFrame)
{
    if (StreetInkImpactFramesRemaining > 0)
    {
        --StreetInkImpactFramesRemaining;
    }

    // Actualizar opacidad y expiración de los Ghost Mesh Trails de Gambeta Parry
    for (int32 Idx = ActiveGhostMeshes.Num() - 1; Idx >= 0; --Idx)
    {
        FActiveGhostMeshEntry& Entry = ActiveGhostMeshes[Idx];
        if (!Entry.PoseableMesh.IsValid())
        {
            ActiveGhostMeshes.RemoveAt(Idx);
            continue;
        }

        const uint32 Elapsed = (CurrentFrame >= Entry.SpawnFrame) ? (CurrentFrame - Entry.SpawnFrame) : Entry.DurationFrames;
        if (Elapsed >= Entry.DurationFrames)
        {
            Entry.PoseableMesh->DestroyComponent();
            ActiveGhostMeshes.RemoveAt(Idx);
        }
    }
}

float UFightingNiagaraVFXDirector::GetStreetInkImpactNormalizedWeight(FVector2D& OutScreenImpactUV) const
{
    OutScreenImpactUV = LastHeavyImpactScreenUV;
    if (StreetInkImpactFramesRemaining <= 0)
    {
        return 0.0f;
    }
    return FMath::Clamp(static_cast<float>(StreetInkImpactFramesRemaining) / 3.0f, 0.0f, 1.0f);
}

void UFightingNiagaraVFXDirector::GetActiveBallFogCarvingData(
    FVector& OutBallCurrentPosCm,
    FVector& OutBallPrevPosCm,
    float& OutCavityRadiusCm,
    float& OutTrailFadeFactor,
    FLinearColor& OutElementalGlowColor) const
{
    OutBallCurrentPosCm = CurrentBallPosCm;
    OutBallPrevPosCm = PreviousBallPosCm;
    OutCavityRadiusCm = CurrentBallCavityRadiusCm;
    OutTrailFadeFactor = CurrentBallTrailFade;
    OutElementalGlowColor = CurrentBallGlowColor;
}

uint32 UFightingNiagaraVFXDirector::ComputeImpactEventHash(
    ECombatImpactVFXType Type,
    const FVector& LocationCm,
    uint32 Frame) const
{
    const uint32 QuantizedX = static_cast<uint32>(FMath::RoundToInt(LocationCm.X * 0.5f));
    const uint32 QuantizedZ = static_cast<uint32>(FMath::RoundToInt(LocationCm.Z * 0.5f));
    uint32 Hash = HashCombineFast(Frame, static_cast<uint32>(Type));
    Hash = HashCombineFast(Hash, QuantizedX);
    Hash = HashCombineFast(Hash, QuantizedZ);
    return Hash;
}
