// FightingCameraAndReplayDirector.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Deterministic Q32.32 2.5D Camera Rig & Replay Theater with Live Takeover

#include "FightingCameraAndReplayDirector.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"

namespace ReplayBinaryFormat
{
    static constexpr uint32 MagicHeader = 0x52464153U; // 'SAFR' en Little-Endian
    static constexpr uint32 FormatVersion = 1U;
}

UFightingCameraDirector::UFightingCameraDirector()
{
    StageLeftBoundMeters = FFixedPoint(-10);
    StageRightBoundMeters = FFixedPoint(10);
}

void UFightingCameraDirector::InitializeStageBounds(
    FFixedPoint InLeftBoundaryMeters,
    FFixedPoint InRightBoundaryMeters)
{
    StageLeftBoundMeters = InLeftBoundaryMeters;
    StageRightBoundMeters = InRightBoundaryMeters;

    CameraState = FCameraTransformPOD();
    CameraState.FocusX = (StageLeftBoundMeters + StageRightBoundMeters) * FFixedPoint::FromMillimeters(500);
    CameraState.FocusZ = FFixedPoint::FromMillimeters(1150);
    CameraState.ZoomRatio = FFixedPoint(1);
    CameraState.ArmDistanceMeters = FFixedPoint::FromMillimeters(4800);
    CameraState.FieldOfViewDegrees = FFixedPoint(54);
}

void UFightingCameraDirector::StepDeterministicCamera(
    const FFighterDeterministicStatePOD& P1State,
    const FFighterDeterministicStatePOD& P2State)
{
    // Si estamos dentro de la secuencia cinemática de 85 frames de Ruptura de Alambrado (Wall Break), usar su curva dedicada
    if (CameraState.WallBreakSequenceFrame > 0)
    {
        StepWallBreakCinematic85Frames(P1State, P2State);
        return;
    }

    // 1. Cálculo del Centro de Gravedad Dinámico (Ponderación 60% Atacante / 40% Defensor)
    const bool bP1IsAttacking =
        P1State.CurrentState == EFighterActionState::AttackStartup ||
        P1State.CurrentState == EFighterActionState::AttackActive ||
        P2State.CurrentState == EFighterActionState::Hitstun ||
        P2State.CurrentState == EFighterActionState::Blockstun;

    const bool bP2IsAttacking =
        P2State.CurrentState == EFighterActionState::AttackStartup ||
        P2State.CurrentState == EFighterActionState::AttackActive ||
        P1State.CurrentState == EFighterActionState::Hitstun ||
        P1State.CurrentState == EFighterActionState::Blockstun;

    FFixedPoint WeightP1 = FFixedPoint::FromMillimeters(500); // 0.50
    FFixedPoint WeightP2 = FFixedPoint::FromMillimeters(500); // 0.50

    if (bP1IsAttacking && !bP2IsAttacking)
    {
        WeightP1 = FFixedPoint::FromMillimeters(600); // 0.60 hacia P1
        WeightP2 = FFixedPoint::FromMillimeters(400); // 0.40 hacia P2
    }
    else if (bP2IsAttacking && !bP1IsAttacking)
    {
        WeightP1 = FFixedPoint::FromMillimeters(400); // 0.40 hacia P1
        WeightP2 = FFixedPoint::FromMillimeters(600); // 0.60 hacia P2
    }

    const FFixedPoint BaseEyeHeight = FFixedPoint::FromMillimeters(1150);
    const FFixedPoint AirborneInfluence = FFixedPoint::FromMillimeters(550);

    FFixedPoint TargetX = (P1State.Position.X * WeightP1) + (P2State.Position.X * WeightP2);
    FFixedPoint TargetZ = BaseEyeHeight + ((P1State.Position.Y + P2State.Position.Y) * FFixedPoint::FromMillimeters(500) * AirborneInfluence);

    // 2. Regulación de Zoom Competitivo (1.00x a 1.25x) basado en separación horizontal entre luchadores
    const FFixedPoint HorizontalSeparation = FFixedPoint::Abs(P1State.Position.X - P2State.Position.X);
    const FFixedPoint CloseRangeThreshold = FFixedPoint::FromMillimeters(1800); // 1.8m
    const FFixedPoint WideRangeThreshold = FFixedPoint::FromMillimeters(6200);  // 6.2m

    const FFixedPoint MinZoom = FFixedPoint::FromMillimeters(1000); // 1.00x (Media cancha abierta)
    const FFixedPoint MaxZoom = FFixedPoint::FromMillimeters(1250); // 1.25x (Clinch / Presión de esquina)

    FFixedPoint TargetZoom = MinZoom;
    if (HorizontalSeparation <= CloseRangeThreshold)
    {
        TargetZoom = MaxZoom;
    }
    else if (HorizontalSeparation < WideRangeThreshold)
    {
        const FFixedPoint RangeSpan = WideRangeThreshold - CloseRangeThreshold;
        const FFixedPoint NormalizedDist = (HorizontalSeparation - CloseRangeThreshold) / RangeSpan;
        TargetZoom = MaxZoom - ((MaxZoom - MinZoom) * NormalizedDist);
    }

    // Interpolación suave de Zoom y Distancia de Brazo Y (Base 4.80m dividido por el factor de Zoom)
    const FFixedPoint ZoomInterpAlpha = FFixedPoint::FromMillimeters(120); // 0.12 por frame
    CameraState.ZoomRatio = CameraState.ZoomRatio + ((TargetZoom - CameraState.ZoomRatio) * ZoomInterpAlpha);
    CameraState.ZoomRatio = FFixedPoint::Clamp(CameraState.ZoomRatio, MinZoom, MaxZoom);

    const FFixedPoint BaseArmMeters = FFixedPoint::FromMillimeters(4800);
    CameraState.ArmDistanceMeters = BaseArmMeters / CameraState.ZoomRatio;

    // Clamping contra bordes de escenario considerando el frustum visible
    const FFixedPoint HalfVisibleWidth = FFixedPoint::FromMillimeters(2600) / CameraState.ZoomRatio;
    const FFixedPoint SafeLeftX = StageLeftBoundMeters + HalfVisibleWidth;
    const FFixedPoint SafeRightX = StageRightBoundMeters - HalfVisibleWidth;

    if (SafeLeftX < SafeRightX)
    {
        TargetX = FFixedPoint::Clamp(TargetX, SafeLeftX, SafeRightX);
    }

    // 3. Integrador Spring-Damper en Punto Fijo Q32.32 (Dt = 1/60s = ~16.66ms)
    const FFixedPoint FixedDt = FFixedPoint::FromMillimeters(16);        // 0.016s
    const FFixedPoint SpringStiffnessK = FFixedPoint(140);               // Rigidez de resorte
    const FFixedPoint DampingC = FFixedPoint(22);                        // Amortiguamiento casi crítico

    const FFixedPoint DisplacementX = TargetX - CameraState.FocusX;
    const FFixedPoint AccelX = (DisplacementX * SpringStiffnessK) - (CameraState.VelocityX * DampingC);
    CameraState.VelocityX += AccelX * FixedDt;
    CameraState.FocusX += CameraState.VelocityX * FixedDt;

    const FFixedPoint DisplacementZ = TargetZ - CameraState.FocusZ;
    const FFixedPoint AccelZ = (DisplacementZ * SpringStiffnessK) - (CameraState.VelocityZ * DampingC);
    CameraState.VelocityZ += AccelZ * FixedDt;
    CameraState.FocusZ += CameraState.VelocityZ * FixedDt;

    // Relajación del Dutch Angle hacia 0 grados y FOV estándar (54 grados)
    const FFixedPoint ZeroFixed(0);
    const FFixedPoint DecayAlpha = FFixedPoint::FromMillimeters(180);
    CameraState.DutchAngleDegrees = CameraState.DutchAngleDegrees + ((ZeroFixed - CameraState.DutchAngleDegrees) * DecayAlpha);
    CameraState.FieldOfViewDegrees = FFixedPoint(54);
}

void UFightingCameraDirector::TriggerWallBreakCameraSequence(
    int32 DirectionSign,
    FFixedPoint NewLeftBoundMeters,
    FFixedPoint NewRightBoundMeters)
{
    CameraState.WallBreakSequenceFrame = 1;
    CameraState.WallBreakDirectionSign = (DirectionSign >= 0) ? 1 : -1;

    StageLeftBoundMeters = NewLeftBoundMeters;
    StageRightBoundMeters = NewRightBoundMeters;
}

void UFightingCameraDirector::StepWallBreakCinematic85Frames(
    const FFighterDeterministicStatePOD& P1State,
    const FFighterDeterministicStatePOD& P2State)
{
    const int32 Frame = CameraState.WallBreakSequenceFrame;
    const FFixedPoint SignFixed(CameraState.WallBreakDirectionSign);

    // El foco sigue al personaje proyectado contra el alambrado
    const FFixedPoint ImpactX = (CameraState.WallBreakDirectionSign > 0)
        ? ((P1State.Position.X > P2State.Position.X) ? P1State.Position.X : P2State.Position.X)
        : ((P1State.Position.X < P2State.Position.X) ? P1State.Position.X : P2State.Position.X);

    CameraState.FocusX = ImpactX;

    if (Frame <= 18)
    {
        // Fase 1 (Frames 1..18): Zoom-In agresivo al impacto contra el alambrado + Dutch Angle de 11 grados
        CameraState.ZoomRatio = FFixedPoint::FromMillimeters(1250);
        CameraState.ArmDistanceMeters = FFixedPoint::FromMillimeters(3100);
        CameraState.DutchAngleDegrees = FFixedPoint(11) * SignFixed;
        CameraState.FieldOfViewDegrees = FFixedPoint(44);
    }
    else if (Frame <= 55)
    {
        // Fase 2 (Frames 19..55): Ruptura de malla metálica, expansión de FOV y paneo de seguimiento por el túnel/calle
        CameraState.ZoomRatio = FFixedPoint::FromMillimeters(1100);
        CameraState.ArmDistanceMeters = FFixedPoint::FromMillimeters(4100);
        CameraState.DutchAngleDegrees = FFixedPoint(-6) * SignFixed;
        CameraState.FieldOfViewDegrees = FFixedPoint(62);
    }
    else
    {
        // Fase 3 (Frames 56..85): Re-encuadre al plano competitivo 2.5D en la nueva zona del escenario
        CameraState.ZoomRatio = FFixedPoint(1);
        CameraState.ArmDistanceMeters = FFixedPoint::FromMillimeters(4800);
        CameraState.DutchAngleDegrees = FFixedPoint(0);
        CameraState.FieldOfViewDegrees = FFixedPoint(54);
    }

    ++CameraState.WallBreakSequenceFrame;
    if (CameraState.WallBreakSequenceFrame > 85)
    {
        CameraState.WallBreakSequenceFrame = 0;
        CameraState.VelocityX = FFixedPoint(0);
        CameraState.VelocityZ = FFixedPoint(0);
    }
}

FTransform UFightingCameraDirector::GetVisualCameraTransformCm(float& OutHorizontalFOV) const
{
    // Conversión exclusivamente visual (Metros Q32.32 -> Centímetros Unreal Engine)
    const float XCm = CameraState.FocusX.ToFloatVisualOnly() * 100.0f;
    const float YCm = -CameraState.ArmDistanceMeters.ToFloatVisualOnly() * 100.0f;
    const float ZCm = CameraState.FocusZ.ToFloatVisualOnly() * 100.0f;
    const float RollDeg = CameraState.DutchAngleDegrees.ToFloatVisualOnly();

    OutHorizontalFOV = CameraState.FieldOfViewDegrees.ToFloatVisualOnly();

    // La cámara mira en +Y (Yaw = +90 grados en el sistema de coordenadas de Unreal Engine)
    const FRotator CameraRotation(0.0f, 90.0f, RollDeg);
    const FVector CameraLocation(XCm, YCm, ZCm);

    return FTransform(CameraRotation, CameraLocation, FVector::OneVector);
}

// ============================================================================
// UReplayPlaybackSubsystem - Replay Theater & Live Takeover ("VAR Interactivo")
// ============================================================================

UReplayPlaybackSubsystem::UReplayPlaybackSubsystem()
{
    CurrentPlaybackFrame = 0;
    bIsLiveTakeoverActive = false;
    ActiveTakeoverPlayerIndex = -1;
}

void UReplayPlaybackSubsystem::EnsureInternalSimulatorsInitialized()
{
    if (!IsValid(InternalSimP1))
    {
        InternalSimP1 = NewObject<UDeterministicFighterStateMachine>(this);
    }
    if (!IsValid(InternalSimP2))
    {
        InternalSimP2 = NewObject<UDeterministicFighterStateMachine>(this);
    }
    if (!IsValid(InternalSimCamera))
    {
        InternalSimCamera = NewObject<UFightingCameraDirector>(this);
    }
}

void UReplayPlaybackSubsystem::RecordLiveMatchFrame(
    uint32 FrameNumber,
    uint16 P1Input,
    uint16 P2Input,
    const FMatchDeterministicSnapshotPOD& CurrentSnapshot)
{
    if (FrameNumber == 0U)
    {
        RecordedInputs.Reset();
        KeyframeSnapshots.Reset();
    }

    FReplayFrameInputPair Pair;
    Pair.Player1InputMask = P1Input;
    Pair.Player2InputMask = P2Input;
    RecordedInputs.Add(Pair);

    // Almacenar un Keyframe completo cada 300 frames (0, 300, 600, 900...)
    if ((FrameNumber % KeyframeIntervalFrames) == 0U)
    {
        KeyframeSnapshots.Add(CurrentSnapshot);
    }

    CurrentStateSnapshot = CurrentSnapshot;
    CurrentPlaybackFrame = FrameNumber;
}

bool UReplayPlaybackSubsystem::SaveReplayToBinary(TArray<uint8>& OutBinaryReplayData) const
{
    OutBinaryReplayData.Reset();
    FMemoryWriter Writer(OutBinaryReplayData, true);

    uint32 Magic = ReplayBinaryFormat::MagicHeader;
    uint32 Version = ReplayBinaryFormat::FormatVersion;
    uint32 TotalFrames = static_cast<uint32>(RecordedInputs.Num());

    Writer << Magic;
    Writer << Version;
    Writer << TotalFrames;

    for (const FReplayFrameInputPair& InputPair : RecordedInputs)
    {
        uint16 P1 = InputPair.Player1InputMask;
        uint16 P2 = InputPair.Player2InputMask;
        Writer << P1;
        Writer << P2;
    }

    return OutBinaryReplayData.Num() > 0;
}

bool UReplayPlaybackSubsystem::LoadReplayFromBinary(const TArray<uint8>& BinaryReplayData)
{
    if (BinaryReplayData.Num() < static_cast<int32>(sizeof(uint32) * 3))
    {
        return false;
    }

    FMemoryReader Reader(BinaryReplayData, true);

    uint32 Magic = 0;
    uint32 Version = 0;
    uint32 TotalFrames = 0;

    Reader << Magic;
    Reader << Version;
    Reader << TotalFrames;

    if (Magic != ReplayBinaryFormat::MagicHeader || Version != ReplayBinaryFormat::FormatVersion)
    {
        return false;
    }

    // Límite de seguridad para un replay de round/match (máximo 36,000 frames = 10 minutos a 60fps)
    if (TotalFrames > 36000U)
    {
        return false;
    }

    RecordedInputs.Empty(static_cast<int32>(TotalFrames));
    for (uint32 i = 0; i < TotalFrames; ++i)
    {
        if (Reader.AtEnd())
        {
            return false;
        }
        FReplayFrameInputPair Pair;
        Reader << Pair.Player1InputMask;
        Reader << Pair.Player2InputMask;
        RecordedInputs.Add(Pair);
    }

    bIsLiveTakeoverActive = false;
    ActiveTakeoverPlayerIndex = -1;

    RebuildKeyframesFromInputs();
    return JumpToFrame(0U);
}

void UReplayPlaybackSubsystem::RebuildKeyframesFromInputs()
{
    EnsureInternalSimulatorsInitialized();
    KeyframeSnapshots.Reset();

    InternalSimP1->InitializeFighter(FFixedPoint(-2), true, 10000);
    InternalSimP2->InitializeFighter(FFixedPoint(2), false, 10000);
    InternalSimCamera->InitializeStageBounds(FFixedPoint(-10), FFixedPoint(10));

    const uint32 TotalFrames = static_cast<uint32>(RecordedInputs.Num());
    for (uint32 FrameIdx = 0; FrameIdx < TotalFrames; ++FrameIdx)
    {
        if ((FrameIdx % KeyframeIntervalFrames) == 0U)
        {
            FMatchDeterministicSnapshotPOD Keyframe;
            Keyframe.FrameNumber = FrameIdx;
            InternalSimP1->SaveDeterministicState(Keyframe.Player1State);
            InternalSimP2->SaveDeterministicState(Keyframe.Player2State);
            InternalSimCamera->SaveCameraState(Keyframe.CameraState);
            KeyframeSnapshots.Add(Keyframe);
        }

        const FReplayFrameInputPair& Inputs = RecordedInputs[FrameIdx];
        const FFixedVector2D P1PosBefore = InternalSimP1->GetState().Position;
        const FFixedVector2D P2PosBefore = InternalSimP2->GetState().Position;

        InternalSimP1->StepSimulationFrame(Inputs.Player1InputMask, P2PosBefore);
        InternalSimP2->StepSimulationFrame(Inputs.Player2InputMask, P1PosBefore);
        InternalSimCamera->StepDeterministicCamera(InternalSimP1->GetState(), InternalSimP2->GetState());
    }
}

bool UReplayPlaybackSubsystem::JumpToFrame(uint32 TargetFrame)
{
    if (RecordedInputs.IsEmpty() || KeyframeSnapshots.IsEmpty())
    {
        return false;
    }

    EnsureInternalSimulatorsInitialized();

    const uint32 ClampedTarget = FMath::Min(TargetFrame, static_cast<uint32>(RecordedInputs.Num() - 1));
    const uint32 KeyframeIndex = FMath::Min(
        ClampedTarget / KeyframeIntervalFrames,
        static_cast<uint32>(KeyframeSnapshots.Num() - 1));

    const FMatchDeterministicSnapshotPOD& BaseKeyframe = KeyframeSnapshots[KeyframeIndex];
    InternalSimP1->LoadDeterministicState(BaseKeyframe.Player1State);
    InternalSimP2->LoadDeterministicState(BaseKeyframe.Player2State);
    InternalSimCamera->LoadCameraState(BaseKeyframe.CameraState);

    // Re-simulación determinista ultrarrápida desde el Keyframe hasta el TargetFrame (máximo 299 pasos)
    for (uint32 SimFrame = BaseKeyframe.FrameNumber; SimFrame < ClampedTarget; ++SimFrame)
    {
        const FReplayFrameInputPair& Inputs = RecordedInputs[SimFrame];
        const FFixedVector2D P1Pos = InternalSimP1->GetState().Position;
        const FFixedVector2D P2Pos = InternalSimP2->GetState().Position;

        InternalSimP1->StepSimulationFrame(Inputs.Player1InputMask, P2Pos);
        InternalSimP2->StepSimulationFrame(Inputs.Player2InputMask, P1Pos);
        InternalSimCamera->StepDeterministicCamera(InternalSimP1->GetState(), InternalSimP2->GetState());
    }

    CurrentPlaybackFrame = ClampedTarget;
    CurrentStateSnapshot.FrameNumber = ClampedTarget;
    InternalSimP1->SaveDeterministicState(CurrentStateSnapshot.Player1State);
    InternalSimP2->SaveDeterministicState(CurrentStateSnapshot.Player2State);
    InternalSimCamera->SaveCameraState(CurrentStateSnapshot.CameraState);

    bIsLiveTakeoverActive = false;
    ActiveTakeoverPlayerIndex = -1;

    return true;
}

bool UReplayPlaybackSubsystem::TakeControlOfReplayAtCurrentFrame(
    int32 ControlledPlayerIndex,
    UDeterministicFighterStateMachine* OutLiveP1Machine,
    UDeterministicFighterStateMachine* OutLiveP2Machine,
    UFightingCameraDirector* OutLiveCameraDirector)
{
    if (ControlledPlayerIndex < 0 || ControlledPlayerIndex > 1)
    {
        return false;
    }

    if (!IsValid(OutLiveP1Machine) || !IsValid(OutLiveP2Machine) || !IsValid(OutLiveCameraDirector))
    {
        return false;
    }

    // Copiamos bit a bit el estado POD Q32.32 del frame actual hacia las máquinas de estado activas del modo entrenamiento
    OutLiveP1Machine->LoadDeterministicState(CurrentStateSnapshot.Player1State);
    OutLiveP2Machine->LoadDeterministicState(CurrentStateSnapshot.Player2State);
    OutLiveCameraDirector->LoadCameraState(CurrentStateSnapshot.CameraState);

    bIsLiveTakeoverActive = true;
    ActiveTakeoverPlayerIndex = ControlledPlayerIndex;

    return true;
}
