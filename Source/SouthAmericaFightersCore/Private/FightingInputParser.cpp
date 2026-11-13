// FightingInputParser.cpp - SouthAmericaFightersCore
#include "FightingInputParser.h"

void FFightingInputRingBuffer::PushFrameInput(uint16 InRawBitmask, bool bIsFacingRight)
{
    FInputFrameEntry& Entry = History[WriteIndex];
    Entry.RawBitmask = InRawBitmask;
    Entry.PressedThisFrame = InRawBitmask & (~PreviousRawBitmask);
    Entry.RelativeNumpadDir = ComputeRelativeNumpadDirection(InRawBitmask, bIsFacingRight);

    PreviousRawBitmask = InRawBitmask;
    WriteIndex = (WriteIndex + 1) % BufferCapacity;
}

uint8 FFightingInputRingBuffer::ComputeRelativeNumpadDirection(uint16 Bitmask, bool bIsFacingRight)
{
    // Limpieza SOCD: Arriba+Abajo = Neutro, Izq+Der = Neutro
    bool bUp    = (Bitmask & ECombatInputBits::Up) != 0;
    bool bDown  = (Bitmask & ECombatInputBits::Down) != 0;
    bool bLeft  = (Bitmask & ECombatInputBits::Left) != 0;
    bool bRight = (Bitmask & ECombatInputBits::Right) != 0;

    if (bUp && bDown) { bUp = false; bDown = false; }
    if (bLeft && bRight) { bLeft = false; bRight = false; }

    const bool bForward = bIsFacingRight ? bRight : bLeft;
    const bool bBack    = bIsFacingRight ? bLeft : bRight;

    int32 Vertical = 0;
    if (bUp) Vertical = 1;
    else if (bDown) Vertical = -1;

    int32 Horizontal = 0;
    if (bForward) Horizontal = 1;
    else if (bBack) Horizontal = -1;

    // Directo a notación Numpad (5 = Neutro, 2 = Abajo, 6 = Adelante, 3 = Abajo-Adelante, etc.)
    return static_cast<uint8>(5 + (Vertical * 3) + Horizontal);
}

bool FFightingInputRingBuffer::CheckCommand(
    ECommandMotionType Motion, uint16 RequiredButtonMask, int32 ButtonLenienceFrames) const
{
    bool bButtonTriggered = false;
    for (int32 i = 0; i < ButtonLenienceFrames; ++i)
    {
        if ((GetFrameFromBack(i).PressedThisFrame & RequiredButtonMask) == RequiredButtonMask)
        {
            bButtonTriggered = true;
            break;
        }
    }
    if (!bButtonTriggered) return false;

    switch (Motion)
    {
    case ECommandMotionType::Ultimate_214214:
        {
            static constexpr uint8 Seq[] = { 2, 1, 4, 2, 1, 4 };
            return MatchDirectionalSequence(Seq, 26);
        }
    case ECommandMotionType::Super_236236:
        {
            static constexpr uint8 Seq[] = { 2, 3, 6, 2, 3, 6 };
            return MatchDirectionalSequence(Seq, 24);
        }
    case ECommandMotionType::HCF_41236:
        {
            static constexpr uint8 StrictSeq[] = { 4, 1, 2, 3, 6 };
            static constexpr uint8 LenientSeq[] = { 4, 2, 3, 6 };
            return MatchDirectionalSequence(StrictSeq, 20) || MatchDirectionalSequence(LenientSeq, 18);
        }
    case ECommandMotionType::DP_623:
        {
            static constexpr uint8 StandardDP[] = { 6, 2, 3 };
            return MatchDirectionalSequence(StandardDP, 14);
        }
    case ECommandMotionType::QCF_236:
        {
            static constexpr uint8 Seq[] = { 2, 3, 6 };
            return MatchDirectionalSequence(Seq, 12);
        }
    case ECommandMotionType::QCB_214:
        {
            static constexpr uint8 Seq[] = { 2, 1, 4 };
            return MatchDirectionalSequence(Seq, 12);
        }
    case ECommandMotionType::DoubleDown_22:
        {
            static constexpr uint8 Seq[] = { 2, 5, 2 };
            return MatchDirectionalSequence(Seq, 14);
        }
    case ECommandMotionType::ChargeBackFwd:
        return MatchChargeBackForward(45, 10);
    default:
        return true;
    }
}

bool FFightingInputRingBuffer::MatchDirectionalSequence(
    TArrayView<const uint8> TargetSeq, int32 MaxTotalWindowFrames) const
{
    int32 SeqCursor = TargetSeq.Num() - 1;
    const int32 Limit = FMath::Min(MaxTotalWindowFrames, BufferCapacity);

    for (int32 FramesAgo = 0; FramesAgo < Limit; ++FramesAgo)
    {
        const uint8 Dir = GetFrameFromBack(FramesAgo).RelativeNumpadDir;
        if (Dir == TargetSeq[SeqCursor])
        {
            --SeqCursor;
            if (SeqCursor < 0)
            {
                return true;
            }
        }
    }
    return false;
}

bool FFightingInputRingBuffer::MatchChargeBackForward(int32 RequiredChargeFrames, int32 MaxTransitionWindow) const
{
    int32 ForwardFrameAgo = -1;
    for (int32 i = 0; i < 6; ++i)
    {
        const uint8 Dir = GetFrameFromBack(i).RelativeNumpadDir;
        if (Dir == 6 || Dir == 3 || Dir == 9)
        {
            ForwardFrameAgo = i;
            break;
        }
    }
    if (ForwardFrameAgo == -1) return false;

    int32 ChargeCount = 0;
    int32 NeutralGap = 0;
    for (int32 i = ForwardFrameAgo + 1; i < BufferCapacity; ++i)
    {
        const uint8 Dir = GetFrameFromBack(i).RelativeNumpadDir;
        if (Dir == 4 || Dir == 1 || Dir == 7)
        {
            ++ChargeCount;
            if (ChargeCount >= RequiredChargeFrames) return true;
        }
        else
        {
            ++NeutralGap;
            if (NeutralGap > MaxTransitionWindow) break;
        }
    }
    return false;
}
