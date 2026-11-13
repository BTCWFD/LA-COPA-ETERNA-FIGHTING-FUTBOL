// FightingInputParser.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "FightingInputParser.generated.h"

namespace ECombatInputBits
{
    constexpr uint16 Up    = 1 << 0;
    constexpr uint16 Down  = 1 << 1;
    constexpr uint16 Left  = 1 << 2;
    constexpr uint16 Right = 1 << 3;
    constexpr uint16 LP    = 1 << 4; // Toque Corto / Jab
    constexpr uint16 MP    = 1 << 5; // Cabezazo / Cuerpo Medio
    constexpr uint16 HP    = 1 << 6; // Falta Táctica / Potente
    constexpr uint16 SK    = 1 << 7; // Habilidad Balón / Proyectil
    constexpr uint16 GB    = 1 << 8; // Gambeta / Drive / Parry
}

UENUM(BlueprintType)
enum class ECommandMotionType : uint8
{
    None,
    QCF_236,         // Cuarto de círculo adelante (Bati-Cañón, Pedalada)
    QCB_214,         // Cuarto de círculo atrás (El Escorpión, Tiro al Ángulo)
    DP_623,          // Movimiento en Z / Dragon Punch (Volea, Despeje de Puños)
    HCF_41236,       // Medio círculo adelante (Elástica, Command Grab Pistolero/Bulldog)
    DoubleDown_22,   // Abajo, Abajo (La Mano Salvadora Parry, Detonar Pase)
    ChargeBackFwd,   // Cargar [4] por 45 frames -> 6 (Cabezazo en Plancha)
    Super_236236,    // Doble QCF (Super Nivel 1)
    Ultimate_214214  // Doble QCB (Grito Sagrado Nivel 3)
};

struct FInputFrameEntry
{
    uint16 RawBitmask = 0;
    uint16 PressedThisFrame = 0;
    uint8 RelativeNumpadDir = 5;
};

class SOUTHAMERICAFIGHTERSCORE_API FFightingInputRingBuffer
{
public:
    static constexpr int32 BufferCapacity = 60; // 1 segundo exacto a 60 Hz

    void PushFrameInput(uint16 InRawBitmask, bool bIsFacingRight);
    bool CheckCommand(ECommandMotionType Motion, uint16 RequiredButtonMask, int32 ButtonLenienceFrames = 4) const;
    static uint8 ComputeRelativeNumpadDirection(uint16 Bitmask, bool bIsFacingRight);

    FORCEINLINE const FInputFrameEntry& GetFrameFromBack(int32 FramesAgo) const
    {
        const int32 Index = (WriteIndex - 1 - FramesAgo + BufferCapacity * 2) % BufferCapacity;
        return History[Index];
    }

private:
    TStaticArray<FInputFrameEntry, BufferCapacity> History;
    int32 WriteIndex = 0;
    uint16 PreviousRawBitmask = 0;

    bool MatchDirectionalSequence(TArrayView<const uint8> TargetSeq, int32 MaxTotalWindowFrames) const;
    bool MatchChargeBackForward(int32 RequiredChargeFrames = 45, int32 MaxTransitionWindow = 10) const;
};
