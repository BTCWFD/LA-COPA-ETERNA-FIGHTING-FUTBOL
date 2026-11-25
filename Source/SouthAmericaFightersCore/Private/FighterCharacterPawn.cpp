// FighterCharacterPawn.cpp - SouthAmericaFightersCore
#include "FighterCharacterPawn.h"
#include "Animation/AnimSequence.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"

namespace FighterVisualAssetPaths
{
    static constexpr const TCHAR* BallStaticMeshPackage = TEXT("/Game/Props/SM_Ball_TruncatedIcosahedron_32Panels");
    static constexpr const TCHAR* BallStaticMeshObject  = TEXT("/Game/Props/SM_Ball_TruncatedIcosahedron_32Panels.SM_Ball_TruncatedIcosahedron_32Panels");

    template <typename TAsset>
    static TAsset* LoadAssetIfPackageExists(const FString& PackagePath)
    {
        if (PackagePath.IsEmpty() || !FPackageName::DoesPackageExist(PackagePath))
        {
            return nullptr;
        }
        return LoadObject<TAsset>(nullptr, *PackagePath);
    }
}

// ============================================================================
// ADeterministicBallProjectile
// ============================================================================

ADeterministicBallProjectile::ADeterministicBallProjectile()
{
    PrimaryActorTick.bCanEverTick = false; // Gobernado a 60 Hz por AFightingMatchGameMode

    BallMeshComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BallMeshComponent"));
    SetRootComponent(BallMeshComponent);
    BallMeshComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetActorHiddenInGame(true);
}

void ADeterministicBallProjectile::BeginPlay()
{
    Super::BeginPlay();
    LoadBallVisualMesh();
}

void ADeterministicBallProjectile::LoadBallVisualMesh()
{
    if (!BallMeshComponent || BallMeshComponent->GetStaticMesh() != nullptr || IsRunningDedicatedServer())
    {
        return;
    }

    if (FPackageName::DoesPackageExist(FighterVisualAssetPaths::BallStaticMeshPackage))
    {
        if (UStaticMesh* LoadedBallMesh = Cast<UStaticMesh>(StaticLoadObject(
            UStaticMesh::StaticClass(),
            nullptr,
            FighterVisualAssetPaths::BallStaticMeshObject)))
        {
            BallMeshComponent->SetStaticMesh(LoadedBallMesh);
        }
    }
}

void ADeterministicBallProjectile::SpawnDeterministicBall(
    int32 InOwnerPlayerIndex,
    const FFixedVector2D& SpawnPos,
    const FFixedVector2D& LaunchVelocity,
    int32 InClashHitPoints,
    int32 InBaseDamage,
    int32 InAdvBlock,
    int32 InAdvHit)
{
    BallState.bIsActive = true;
    BallState.OwnerPlayerIndex = InOwnerPlayerIndex;
    BallState.Position = SpawnPos;
    BallState.Velocity = LaunchVelocity;
    BallState.RemainingClashHitPoints = FMath::Max(1, InClashHitPoints);
    BallState.BaseDamage = InBaseDamage;
    BallState.AdvantageOnBlock = InAdvBlock;
    BallState.AdvantageOnHit = InAdvHit;
    BallState.RemainingLifetimeFrames = 150;
    BallState.bReflectedByScorpion = false;

    SetActorHiddenInGame(false);
    SyncBallVisualTransform(false);
}

void ADeterministicBallProjectile::StepDeterministicBallFrame()
{
    if (!BallState.bIsActive)
    {
        return;
    }

    BallState.Position.X += BallState.Velocity.X;
    BallState.Position.Y += BallState.Velocity.Y;

    if (BallState.Position.Y < FFixedPoint::FromMillimeters(220))
    {
        BallState.Position.Y = FFixedPoint::FromMillimeters(220);
        BallState.Velocity.Y = -BallState.Velocity.Y * FFixedPoint::FromMillimeters(750);
    }

    --BallState.RemainingLifetimeFrames;
    if (BallState.RemainingLifetimeFrames <= 0)
    {
        DeactivateBall();
    }
}

void ADeterministicBallProjectile::ReflectByScorpionKick(int32 NewOwnerPlayerIndex)
{
    if (!BallState.bIsActive)
    {
        return;
    }

    BallState.OwnerPlayerIndex = NewOwnerPlayerIndex;
    // Invierte la velocidad horizontal y la incrementa un 35% (1350 mm = 1.35x en Q32.32)
    BallState.Velocity.X = -BallState.Velocity.X * FFixedPoint::FromMillimeters(1350);
    BallState.BaseDamage = (BallState.BaseDamage * 125) / 100;
    BallState.bReflectedByScorpion = true;
    BallState.RemainingLifetimeFrames = 120;
}

FFixedAABB ADeterministicBallProjectile::GetBallHitboxAABB() const
{
    FFixedAABB Box;
    const FFixedPoint Radius = FFixedPoint::FromMillimeters(220); // 22 cm de radio oficial de balón
    Box.MinX = BallState.Position.X - Radius;
    Box.MaxX = BallState.Position.X + Radius;
    Box.MinY = BallState.Position.Y - Radius;
    Box.MaxY = BallState.Position.Y + Radius;
    return Box;
}

void ADeterministicBallProjectile::ConsumeClashHitPoints(int32 Amount)
{
    BallState.RemainingClashHitPoints -= Amount;
    if (BallState.RemainingClashHitPoints <= 0)
    {
        DeactivateBall();
    }
}

void ADeterministicBallProjectile::SyncBallVisualTransform(bool bDrawGreyboxAABB)
{
    if (!BallState.bIsActive)
    {
        SetActorHiddenInGame(true);
        return;
    }

    SetActorHiddenInGame(false);
    const float VisualXCm = BallState.Position.X.ToFloatVisualOnly() * 100.0f;
    const float VisualZCm = BallState.Position.Y.ToFloatVisualOnly() * 100.0f;
    SetActorLocation(FVector(VisualXCm, 0.0f, VisualZCm));

    if (bDrawGreyboxAABB && GetWorld())
    {
        const FFixedAABB Box = GetBallHitboxAABB();
        const FVector MinPt(Box.MinX.ToFloatVisualOnly() * 100.0f, -22.0f, Box.MinY.ToFloatVisualOnly() * 100.0f);
        const FVector MaxPt(Box.MaxX.ToFloatVisualOnly() * 100.0f,  22.0f, Box.MaxY.ToFloatVisualOnly() * 100.0f);
        const FVector Center = (MinPt + MaxPt) * 0.5f;
        const FVector Extent = (MaxPt - MinPt) * 0.5f;

        const FColor DebugColor = BallState.bReflectedByScorpion ? FColor::Magenta : FColor(255, 140, 0);
        DrawDebugBox(GetWorld(), Center, Extent, DebugColor, false, 0.02f, 0, 2.5f);
    }
}

// ============================================================================
// AFighterCharacterPawn
// ============================================================================

AFighterCharacterPawn::AFighterCharacterPawn()
{
    PrimaryActorTick.bCanEverTick = false; // Gobernado a 60 Hz por AFightingMatchGameMode

    RootPivotComponent = CreateDefaultSubobject<USceneComponent>(TEXT("RootPivotComponent"));
    SetRootComponent(RootPivotComponent);

    MainSkeletalMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("MainSkeletalMesh"));
    MainSkeletalMesh->SetupAttachment(RootPivotComponent);
    MainSkeletalMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    VisualFeedbackComponent = CreateDefaultSubobject<UFighterVisualFeedbackComponent>(TEXT("VisualFeedbackComponent"));
}

void AFighterCharacterPawn::BeginPlay()
{
    Super::BeginPlay();

    if (!StateMachine)
    {
        StateMachine = NewObject<UDeterministicFighterStateMachine>(this, TEXT("DeterministicStateMachine"));
        const FFixedPoint DefaultSpawnX = (PlayerIndex == 0)
            ? FFixedPoint::FromMillimeters(-2500)
            : FFixedPoint::FromMillimeters(2500);
        StateMachine->InitializeFighter(DefaultSpawnX, PlayerIndex == 0, MaxHealth);
    }

    if (!CachedSkeletalMesh)
    {
        LoadVisualAssetsForFighter(FighterRosterID);
    }

    if (VisualFeedbackComponent && MainSkeletalMesh)
    {
        TArray<USkeletalMeshComponent*> EmptyClothArray;
        VisualFeedbackComponent->RegisterFighterMeshes(MainSkeletalMesh, EmptyClothArray);
    }
}

void AFighterCharacterPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    if (!PlayerInputComponent || bHasBoundInputActions)
    {
        return;
    }
    bHasBoundInputActions = true;

    PlayerInputComponent->BindAction(TEXT("Combat_Up"), IE_Pressed, this, &AFighterCharacterPawn::OnInputUpPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_Up"), IE_Released, this, &AFighterCharacterPawn::OnInputUpReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_Down"), IE_Pressed, this, &AFighterCharacterPawn::OnInputDownPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_Down"), IE_Released, this, &AFighterCharacterPawn::OnInputDownReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_Left"), IE_Pressed, this, &AFighterCharacterPawn::OnInputLeftPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_Left"), IE_Released, this, &AFighterCharacterPawn::OnInputLeftReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_Right"), IE_Pressed, this, &AFighterCharacterPawn::OnInputRightPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_Right"), IE_Released, this, &AFighterCharacterPawn::OnInputRightReleased);

    PlayerInputComponent->BindAction(TEXT("Combat_LP"), IE_Pressed, this, &AFighterCharacterPawn::OnInputLPPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_LP"), IE_Released, this, &AFighterCharacterPawn::OnInputLPReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_MP"), IE_Pressed, this, &AFighterCharacterPawn::OnInputMPPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_MP"), IE_Released, this, &AFighterCharacterPawn::OnInputMPReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_HP"), IE_Pressed, this, &AFighterCharacterPawn::OnInputHPPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_HP"), IE_Released, this, &AFighterCharacterPawn::OnInputHPReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_SK"), IE_Pressed, this, &AFighterCharacterPawn::OnInputSKPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_SK"), IE_Released, this, &AFighterCharacterPawn::OnInputSKReleased);
    PlayerInputComponent->BindAction(TEXT("Combat_GB"), IE_Pressed, this, &AFighterCharacterPawn::OnInputGBPressed);
    PlayerInputComponent->BindAction(TEXT("Combat_GB"), IE_Released, this, &AFighterCharacterPawn::OnInputGBReleased);
}

void AFighterCharacterPawn::InitializeFighterForRound(
    int32 InPlayerIndex,
    FName InFighterRosterID,
    FFixedPoint SpawnX,
    bool bStartFacingRight,
    int32 InMaxHealth)
{
    PlayerIndex = InPlayerIndex;
    FighterRosterID = InFighterRosterID.IsNone() ? FName(TEXT("FENOMENO_BR")) : InFighterRosterID;
    MaxHealth = FMath::Max(1, InMaxHealth);
    bVictoryPoseActive = false;
    bHasInitializedVisualAnimState = false;
    LastVisualAnimState = EFighterActionState::Idle;
    LastVisualAnimMoveID = NAME_None;
    LastPlayedAnimSequence = nullptr;

    if (!StateMachine)
    {
        StateMachine = NewObject<UDeterministicFighterStateMachine>(this, TEXT("DeterministicStateMachine"));
    }

    StateMachine->InitializeFighter(SpawnX, bStartFacingRight, MaxHealth);
    LoadVisualAssetsForFighter(FighterRosterID);
    SyncVisualTransformFromFixedPoint(0, bEnableLiveAABBDebugDraw);
}

FString AFighterCharacterPawn::ResolveVisualAssetStemForFighter(FName InFighterRosterID)
{
    if (InFighterRosterID.IsNone())
    {
        return TEXT("FENOMENO_BR");
    }

    if (InFighterRosterID == TEXT("VAR_ZERO_BOSS") ||
        InFighterRosterID == TEXT("BOSS_VAR_ZERO") ||
        InFighterRosterID == TEXT("SUPREME_JUDGE_BOSS"))
    {
        return TEXT("SUPREME_JUDGE_BOSS");
    }

    FString Stem = InFighterRosterID.ToString();
    if (Stem.StartsWith(TEXT("SK_")))
    {
        Stem.RightChopInline(3);
    }
    return Stem.IsEmpty() ? TEXT("FENOMENO_BR") : Stem;
}

void AFighterCharacterPawn::LoadVisualAssetsForFighter(FName InFighterRosterID)
{
    if (!MainSkeletalMesh || IsRunningDedicatedServer())
    {
        return;
    }

    const FString AssetStem = ResolveVisualAssetStemForFighter(InFighterRosterID);
    const FString BaseMeshDir = FString::Printf(
        TEXT("/Game/Characters/SouthAmericaRoster/Meshes/SK_%s/SkeletalMeshes"),
        *AssetStem);

    const FString SkeletalMeshPath   = FString::Printf(TEXT("%s/SK_%s"), *BaseMeshDir, *AssetStem);
    const FString IdleBreathPath     = FString::Printf(TEXT("%s/SK_%sIdle_Breath"), *BaseMeshDir, *AssetStem);
    const FString DashForwardPath    = FString::Printf(TEXT("%s/SK_%sDash_Forward"), *BaseMeshDir, *AssetStem);
    const FString KickHighPath       = FString::Printf(TEXT("%s/SK_%sKick_High"), *BaseMeshDir, *AssetStem);
    const FString SpecialChilenaPath = FString::Printf(TEXT("%s/SK_%sSpecial_Chilena"), *BaseMeshDir, *AssetStem);
    const FString VictoryPosePath    = FString::Printf(TEXT("%s/SK_%sVictory_Pose"), *BaseMeshDir, *AssetStem);

    CachedSkeletalMesh       = FighterVisualAssetPaths::LoadAssetIfPackageExists<USkeletalMesh>(SkeletalMeshPath);
    CachedAnimIdleBreath     = FighterVisualAssetPaths::LoadAssetIfPackageExists<UAnimSequence>(IdleBreathPath);
    CachedAnimDashForward    = FighterVisualAssetPaths::LoadAssetIfPackageExists<UAnimSequence>(DashForwardPath);
    CachedAnimKickHigh       = FighterVisualAssetPaths::LoadAssetIfPackageExists<UAnimSequence>(KickHighPath);
    CachedAnimSpecialChilena = FighterVisualAssetPaths::LoadAssetIfPackageExists<UAnimSequence>(SpecialChilenaPath);
    CachedAnimVictoryPose    = FighterVisualAssetPaths::LoadAssetIfPackageExists<UAnimSequence>(VictoryPosePath);

    if (CachedSkeletalMesh)
    {
        MainSkeletalMesh->SetSkeletalMeshAsset(CachedSkeletalMesh);
        MainSkeletalMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);

        if (CachedAnimIdleBreath)
        {
            MainSkeletalMesh->PlayAnimation(CachedAnimIdleBreath, true);
            LastPlayedAnimSequence = CachedAnimIdleBreath;
        }
    }
}

void AFighterCharacterPawn::PlayVictoryPoseAnimation()
{
    bVictoryPoseActive = true;
    if (MainSkeletalMesh && CachedAnimVictoryPose && LastPlayedAnimSequence != CachedAnimVictoryPose)
    {
        MainSkeletalMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        MainSkeletalMesh->PlayAnimation(CachedAnimVictoryPose, false);
        LastPlayedAnimSequence = CachedAnimVictoryPose;
    }
}

void AFighterCharacterPawn::BindFighterPlayerControllerInput(APlayerController* InPlayerController)
{
    if (!InPlayerController)
    {
        return;
    }

    bIsPlayerControlled = true;
    if (InPlayerController->GetPawn() != this)
    {
        InPlayerController->Possess(this);
    }
    else if (InputComponent && !bHasBoundInputActions)
    {
        SetupPlayerInputComponent(InputComponent);
    }
}

uint16 AFighterCharacterPawn::PollLocalRawInputBitmask() const
{
    if (bUseInjectedInputOverride)
    {
        return InjectedOverrideMask;
    }

    // Resolución SOCD Neutral (Hitbox / Leverless Standard: Left + Right = Neutral, Down + Up = Up)
    uint16 CleanedMask = LiveHardwareInputMask;
    const uint16 HorizMask = ECombatInputBits::Left | ECombatInputBits::Right;
    if ((CleanedMask & HorizMask) == HorizMask)
    {
        CleanedMask &= ~HorizMask;
    }
    if ((CleanedMask & ECombatInputBits::Down) && (CleanedMask & ECombatInputBits::Up))
    {
        CleanedMask &= ~ECombatInputBits::Down;
    }
    return CleanedMask;
}

void AFighterCharacterPawn::SetInjectedInputBitmask(uint16 InMask, bool bEnableOverride)
{
    InjectedOverrideMask = InMask;
    bUseInjectedInputOverride = bEnableOverride;
}

void AFighterCharacterPawn::SyncVisualTransformFromFixedPoint(uint32 CurrentFrame, bool bDrawGreyboxAABBs)
{
    if (!StateMachine)
    {
        return;
    }

    const FFighterDeterministicStatePOD& SimState = StateMachine->GetState();

    // Conversión Q32.32 (metros) -> Centímetros de Unreal (Eje X horizontal, Eje Z altura vertical)
    const float VisualXCm = SimState.Position.X.ToFloatVisualOnly() * 100.0f;
    const float VisualZCm = SimState.Position.Y.ToFloatVisualOnly() * 100.0f;
    const FRotator FacingRot = SimState.bIsFacingRight ? FRotator(0.0f, 0.0f, 0.0f) : FRotator(0.0f, 180.0f, 0.0f);

    SetActorLocationAndRotation(FVector(VisualXCm, 0.0f, VisualZCm), FacingRot);

    UpdateVisualAnimationForState(SimState);

    if (VisualFeedbackComponent)
    {
        VisualFeedbackComponent->DeterministicVisualStep(CurrentFrame);
    }

    if (bDrawGreyboxAABBs && bEnableLiveAABBDebugDraw)
    {
        // 1. Pushbox (Amarillo: colisión cuerpo a cuerpo)
        DrawFixedAABBDebugBox(StateMachine->GetCurrentPushbox(), FColor::Yellow, 2.0f);

        // 2. Hurtbox (Verde en neutro, Azul Cian en Blockstun, Naranja en Hitstun)
        FColor HurtboxColor = FColor::Green;
        if (SimState.CurrentState == EFighterActionState::Blockstun)
        {
            HurtboxColor = FColor::Cyan;
        }
        else if (SimState.CurrentState == EFighterActionState::Hitstun)
        {
            HurtboxColor = FColor::Orange;
        }
        DrawFixedAABBDebugBox(StateMachine->GetCurrentHurtbox(), HurtboxColor, 1.75f);

        // 3. Hitbox Activa (Rojo Intenso en frames activos de ataque)
        FFixedAABB ActiveHitbox;
        FMoveFrameDataRow ActiveMoveData;
        if (StateMachine->GetCurrentActiveHitbox(ActiveHitbox, ActiveMoveData))
        {
            DrawFixedAABBDebugBox(ActiveHitbox, FColor::Red, 3.0f);
        }
    }
}

void AFighterCharacterPawn::UpdateVisualAnimationForState(const FFighterDeterministicStatePOD& SimState)
{
    if (!MainSkeletalMesh || !CachedSkeletalMesh)
    {
        return;
    }

    if (bVictoryPoseActive)
    {
        if (CachedAnimVictoryPose && LastPlayedAnimSequence != CachedAnimVictoryPose)
        {
            MainSkeletalMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
            MainSkeletalMesh->PlayAnimation(CachedAnimVictoryPose, false);
            LastPlayedAnimSequence = CachedAnimVictoryPose;
        }
        return;
    }

    UAnimSequence* TargetAnim = CachedAnimIdleBreath;
    bool bLoop = true;

    switch (SimState.CurrentState)
    {
    case EFighterActionState::WalkForward:
    case EFighterActionState::WalkBackward:
    case EFighterActionState::DashForward:
    case EFighterActionState::DashBackward:
    case EFighterActionState::JumpStartup:
    case EFighterActionState::Airborne:
        TargetAnim = CachedAnimDashForward ? CachedAnimDashForward : CachedAnimIdleBreath;
        bLoop = true;
        break;

    case EFighterActionState::AttackStartup:
    case EFighterActionState::AttackActive:
    case EFighterActionState::AttackRecovery:
    {
        const FString MoveStr = SimState.ActiveMoveID.ToString();
        const bool bIsSpecialOrSuper =
            MoveStr.Contains(TEXT("Special"), ESearchCase::IgnoreCase) ||
            MoveStr.Contains(TEXT("Super"), ESearchCase::IgnoreCase) ||
            MoveStr.Contains(TEXT("Ultimate"), ESearchCase::IgnoreCase) ||
            MoveStr.Contains(TEXT("Chilena"), ESearchCase::IgnoreCase) ||
            MoveStr.Contains(TEXT("Scorpion"), ESearchCase::IgnoreCase);

        if (bIsSpecialOrSuper && CachedAnimSpecialChilena)
        {
            TargetAnim = CachedAnimSpecialChilena;
        }
        else
        {
            TargetAnim = CachedAnimKickHigh ? CachedAnimKickHigh : CachedAnimSpecialChilena;
        }
        bLoop = false;
        break;
    }

    case EFighterActionState::Idle:
    case EFighterActionState::Crouch:
    case EFighterActionState::Blockstun:
    case EFighterActionState::Hitstun:
    case EFighterActionState::HardKnockdown:
    default:
        TargetAnim = CachedAnimIdleBreath;
        bLoop = true;
        break;
    }

    if (!TargetAnim)
    {
        TargetAnim = CachedAnimIdleBreath;
    }

    const bool bEnteredNewAttack =
        (SimState.CurrentState == EFighterActionState::AttackStartup) &&
        (LastVisualAnimState != EFighterActionState::AttackStartup || SimState.ActiveMoveID != LastVisualAnimMoveID);

    if (TargetAnim && (!bHasInitializedVisualAnimState || TargetAnim != LastPlayedAnimSequence || bEnteredNewAttack))
    {
        MainSkeletalMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        MainSkeletalMesh->PlayAnimation(TargetAnim, bLoop);
        LastPlayedAnimSequence = TargetAnim;
    }

    LastVisualAnimState = SimState.CurrentState;
    LastVisualAnimMoveID = SimState.ActiveMoveID;
    bHasInitializedVisualAnimState = true;
}

void AFighterCharacterPawn::DrawFixedAABBDebugBox(const FFixedAABB& Box, const FColor& Color, float Thickness) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    const FVector MinPt(Box.MinX.ToFloatVisualOnly() * 100.0f, -15.0f, Box.MinY.ToFloatVisualOnly() * 100.0f);
    const FVector MaxPt(Box.MaxX.ToFloatVisualOnly() * 100.0f,  15.0f, Box.MaxY.ToFloatVisualOnly() * 100.0f);
    const FVector Center = (MinPt + MaxPt) * 0.5f;
    const FVector Extent = (MaxPt - MinPt) * 0.5f;

    DrawDebugBox(World, Center, Extent, Color, false, 0.02f, 0, Thickness);
}
