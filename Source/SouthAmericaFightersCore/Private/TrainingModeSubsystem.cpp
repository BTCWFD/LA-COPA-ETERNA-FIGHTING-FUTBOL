// TrainingModeSubsystem.cpp - SouthAmericaFightersCore
#include "TrainingModeSubsystem.h"
#include "FightingInputParser.h"

void UTrainingModeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    RecordingSlots.SetNum(TotalRecordingSlots);
    for (int32 i = 0; i < TotalRecordingSlots; ++i)
    {
        RecordingSlots[i].InitializeSlot();
    }

    DeterministicRNG.Initialize(19301950); // Semilla determinista CONMEBOL
    CurrentDummyMode = EDummyStateMode::StandIdle;
    ActiveRecordingSlotIndex = 0;
    ActivePlaybackSlotIndex = -1;
    CurrentPlaybackFrameCursor = 0;
    ActiveReversalFrameCursor = -1;
}

void UTrainingModeSubsystem::Deinitialize()
{
    RecordingSlots.Empty();
    Player1SM = nullptr;
    DummyPlayer2SM = nullptr;
    Super::Deinitialize();
}

void UTrainingModeSubsystem::BindTrainingFighters(
    UDeterministicFighterStateMachine* InPlayer1,
    UDeterministicFighterStateMachine* InDummyPlayer2)
{
    Player1SM = InPlayer1;
    DummyPlayer2SM = InDummyPlayer2;
    PreviousDummyActionState = DummyPlayer2SM ? DummyPlayer2SM->GetState().CurrentState : EFighterActionState::Idle;
}

void UTrainingModeSubsystem::SetDummyMode(EDummyStateMode NewMode)
{
    CurrentDummyMode = NewMode;
    if (NewMode != EDummyStateMode::PlaybackMultiSlot)
    {
        ActivePlaybackSlotIndex = -1;
        CurrentPlaybackFrameCursor = 0;
    }
}

bool UTrainingModeSubsystem::StartRecordingSlot(int32 SlotIndex, bool bCurrentFacingRight)
{
    if (!RecordingSlots.IsValidIndex(SlotIndex))
    {
        return false;
    }

    ActiveRecordingSlotIndex = SlotIndex;
    FDummyRecordingSlot& Slot = RecordingSlots[SlotIndex];
    Slot.InitializeSlot();
    Slot.bRecordedFacingRight = bCurrentFacingRight;
    Slot.bIsSlotEnabled = true;

    CurrentDummyMode = EDummyStateMode::RecordingInput;
    return true;
}

void UTrainingModeSubsystem::StopRecording()
{
    if (CurrentDummyMode == EDummyStateMode::RecordingInput)
    {
        CurrentDummyMode = EDummyStateMode::StandIdle;
    }
}

bool UTrainingModeSubsystem::StartProbabilisticPlayback()
{
    const int32 ChosenSlot = SelectWeightedRandomSlot();
    if (!RecordingSlots.IsValidIndex(ChosenSlot))
    {
        return false;
    }

    ActivePlaybackSlotIndex = ChosenSlot;
    CurrentPlaybackFrameCursor = 0;
    CurrentDummyMode = EDummyStateMode::PlaybackMultiSlot;
    return true;
}

void UTrainingModeSubsystem::ConfigureSlotWeight(int32 SlotIndex, int32 Weight, bool bEnabled)
{
    if (RecordingSlots.IsValidIndex(SlotIndex))
    {
        RecordingSlots[SlotIndex].SelectionWeight = FMath::Clamp(Weight, 0, 100);
        RecordingSlots[SlotIndex].bIsSlotEnabled = bEnabled;
    }
}

bool UTrainingModeSubsystem::SaveInstantSituation()
{
    if (!Player1SM || !DummyPlayer2SM)
    {
        return false;
    }

    Player1SM->SaveDeterministicState(SavedSituation.Player1State);
    DummyPlayer2SM->SaveDeterministicState(SavedSituation.Player2State);
    SavedSituation.SavedChecksum = Player1SM->ComputeStateChecksum() ^ DummyPlayer2SM->ComputeStateChecksum();
    SavedSituation.bHasValidSnapshot = true;
    return true;
}

bool UTrainingModeSubsystem::LoadInstantSituation()
{
    if (!SavedSituation.bHasValidSnapshot || !Player1SM || !DummyPlayer2SM)
    {
        return false;
    }

    Player1SM->LoadDeterministicState(SavedSituation.Player1State);
    DummyPlayer2SM->LoadDeterministicState(SavedSituation.Player2State);
    ActiveReversalFrameCursor = -1;
    PreviousDummyActionState = SavedSituation.Player2State.CurrentState;

    const uint32 RestoredChecksum = Player1SM->ComputeStateChecksum() ^ DummyPlayer2SM->ComputeStateChecksum();
    return (RestoredChecksum == SavedSituation.SavedChecksum);
}

void UTrainingModeSubsystem::SetFrameOneReversalSequence(
    const TArray<int32>& InReversalBitmasks,
    bool bTriggerOnBlock,
    bool bTriggerOnHit,
    bool bTriggerOnWakeup)
{
    ReversalInputSequence.Reset(InReversalBitmasks.Num());
    for (int32 Mask : InReversalBitmasks)
    {
        ReversalInputSequence.Add(static_cast<uint16>(Mask & 0xFFFF));
    }

    bReversalOnBlock = bTriggerOnBlock;
    bReversalOnHit = bTriggerOnHit;
    bReversalOnWakeup = bTriggerOnWakeup;
    ActiveReversalFrameCursor = -1;
}

uint16 UTrainingModeSubsystem::EvaluateDummyFrameInput(uint16 Player1InputWhenRecording)
{
    const bool bCurrentFacingRight = DummyPlayer2SM ? DummyPlayer2SM->GetState().bIsFacingRight : false;
    const EFighterActionState CurrentAction = DummyPlayer2SM ? DummyPlayer2SM->GetState().CurrentState : EFighterActionState::Idle;

    // 1. Detectar transición exacta al Frame 1 tras salir de Blockstun, Hitstun o HardKnockdown (Wake-up)
    if (ReversalInputSequence.Num() > 0 && ActiveReversalFrameCursor < 0)
    {
        const bool bExitedBlockstun = (PreviousDummyActionState == EFighterActionState::Blockstun && CurrentAction == EFighterActionState::Idle);
        const bool bExitedHitstun   = (PreviousDummyActionState == EFighterActionState::Hitstun && CurrentAction == EFighterActionState::Idle);
        const bool bExitedKnockdown = (PreviousDummyActionState == EFighterActionState::HardKnockdown && CurrentAction == EFighterActionState::Idle);

        if ((bExitedBlockstun && bReversalOnBlock) ||
            (bExitedHitstun && bReversalOnHit) ||
            (bExitedKnockdown && bReversalOnWakeup))
        {
            ActiveReversalFrameCursor = 0;
            bReversalFacingRightAtStart = bCurrentFacingRight;
        }
    }
    PreviousDummyActionState = CurrentAction;

    // 2. Si hay una secuencia de Reversal al Frame 1 en ejecución, tiene prioridad absoluta
    if (ActiveReversalFrameCursor >= 0 && ActiveReversalFrameCursor < ReversalInputSequence.Num())
    {
        const uint16 RawReversalMask = ReversalInputSequence[ActiveReversalFrameCursor];
        ++ActiveReversalFrameCursor;
        if (ActiveReversalFrameCursor >= ReversalInputSequence.Num())
        {
            ActiveReversalFrameCursor = -1;
        }
        return FlipHorizontalInputBitsIfNeeded(RawReversalMask, true, bReversalFacingRightAtStart);
    }

    // 3. Evaluación según el modo de Dummy seleccionado
    switch (CurrentDummyMode)
    {
    case EDummyStateMode::StandIdle:
        return 0;

    case EDummyStateMode::CrouchIdle:
        return ECombatInputBits::Down;

    case EDummyStateMode::JumpLoop:
        return ECombatInputBits::Up;

    case EDummyStateMode::BlockAll:
        return ComputeAutoBlockBitmask();

    case EDummyStateMode::BlockAfterFirstHit:
        if (CurrentAction == EFighterActionState::Hitstun || CurrentAction == EFighterActionState::Blockstun)
        {
            return ComputeAutoBlockBitmask();
        }
        return 0;

    case EDummyStateMode::RandomBlock:
        return (DeterministicRNG.RandRange(0, 1) == 1) ? ComputeAutoBlockBitmask() : 0;

    case EDummyStateMode::RecordingInput:
        if (RecordingSlots.IsValidIndex(ActiveRecordingSlotIndex))
        {
            FDummyRecordingSlot& Slot = RecordingSlots[ActiveRecordingSlotIndex];
            if (Slot.FrameInputs.Num() < FDummyRecordingSlot::MaxFramesPerSlot)
            {
                Slot.FrameInputs.Add(Player1InputWhenRecording);
            }
            else
            {
                StopRecording();
            }
        }
        return Player1InputWhenRecording;

    case EDummyStateMode::PlaybackMultiSlot:
        if (!RecordingSlots.IsValidIndex(ActivePlaybackSlotIndex) ||
            !RecordingSlots[ActivePlaybackSlotIndex].HasRecordedData())
        {
            ActivePlaybackSlotIndex = SelectWeightedRandomSlot();
            CurrentPlaybackFrameCursor = 0;
        }

        if (RecordingSlots.IsValidIndex(ActivePlaybackSlotIndex))
        {
            const FDummyRecordingSlot& ActiveSlot = RecordingSlots[ActivePlaybackSlotIndex];
            if (CurrentPlaybackFrameCursor < ActiveSlot.FrameInputs.Num())
            {
                const uint16 RecordedMask = ActiveSlot.FrameInputs[CurrentPlaybackFrameCursor];
                ++CurrentPlaybackFrameCursor;

                if (CurrentPlaybackFrameCursor >= ActiveSlot.FrameInputs.Num())
                {
                    ActivePlaybackSlotIndex = SelectWeightedRandomSlot();
                    CurrentPlaybackFrameCursor = 0;
                }

                return FlipHorizontalInputBitsIfNeeded(RecordedMask, ActiveSlot.bRecordedFacingRight, bCurrentFacingRight);
            }
        }
        return 0;
    }

    return 0;
}

uint16 UTrainingModeSubsystem::FlipHorizontalInputBitsIfNeeded(
    uint16 RawMask,
    bool bRecordedFacingRight,
    bool bCurrentFacingRight)
{
    if (bRecordedFacingRight == bCurrentFacingRight)
    {
        return RawMask;
    }

    const bool bHadLeft  = (RawMask & ECombatInputBits::Left) != 0;
    const bool bHadRight = (RawMask & ECombatInputBits::Right) != 0;

    uint16 ClearedMask = RawMask & ~(ECombatInputBits::Left | ECombatInputBits::Right);
    if (bHadLeft)
    {
        ClearedMask |= ECombatInputBits::Right;
    }
    if (bHadRight)
    {
        ClearedMask |= ECombatInputBits::Left;
    }
    return ClearedMask;
}

int32 UTrainingModeSubsystem::SelectWeightedRandomSlot()
{
    int32 TotalWeight = 0;
    for (int32 i = 0; i < RecordingSlots.Num(); ++i)
    {
        if (RecordingSlots[i].bIsSlotEnabled && RecordingSlots[i].HasRecordedData() && RecordingSlots[i].SelectionWeight > 0)
        {
            TotalWeight += RecordingSlots[i].SelectionWeight;
        }
    }

    if (TotalWeight <= 0)
    {
        return INDEX_NONE;
    }

    int32 Roll = DeterministicRNG.RandRange(1, TotalWeight);
    for (int32 i = 0; i < RecordingSlots.Num(); ++i)
    {
        if (RecordingSlots[i].bIsSlotEnabled && RecordingSlots[i].HasRecordedData() && RecordingSlots[i].SelectionWeight > 0)
        {
            Roll -= RecordingSlots[i].SelectionWeight;
            if (Roll <= 0)
            {
                return i;
            }
        }
    }

    return INDEX_NONE;
}

uint16 UTrainingModeSubsystem::ComputeAutoBlockBitmask() const
{
    if (!DummyPlayer2SM || !Player1SM)
    {
        return ECombatInputBits::Left;
    }

    const FFighterDeterministicStatePOD& P1 = Player1SM->GetState();
    const FFighterDeterministicStatePOD& P2 = DummyPlayer2SM->GetState();

    // Auto-orientación contra Cross-ups: "Atrás" es siempre la dirección opuesta a la posición actual de P1
    const uint16 BackBit = (P1.Position.X >= P2.Position.X) ? ECombatInputBits::Left : ECombatInputBits::Right;

    // Si P1 está en el aire, bloquear de pie (Overhead); de lo contrario, bloquear agachado (Crouch Block)
    if (P1.CurrentState == EFighterActionState::Airborne || P1.Position.Y > FFixedPoint(0))
    {
        return BackBit;
    }

    return BackBit | ECombatInputBits::Down;
}
