// FrameDataTypes.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "FixedPointTypes.h"
#include "FrameDataTypes.generated.h"

UENUM(BlueprintType, Meta = (Bitflags, UseEnumValuesAsMaskValuesInEditor = "true"))
enum class ECancelWindowFlags : uint8
{
    None           = 0 UMETA(Hidden),
    ChainCancel    = 1 << 0, // CH: Cancelable en otros ligeros
    SpecialCancel  = 1 << 1, // SP: Cancelable en 236/623/214
    SuperCancel    = 1 << 2, // SU: Cancelable en Nivel 1 o 3
    GambetaCancel  = 1 << 3  // GB: Cancelable en Dash/Run
};
ENUM_CLASS_FLAGS(ECancelWindowFlags);

USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FMoveFrameDataRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    FName MoveID;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    FString NumpadNotation; // Ej. "236+SK"

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 StartupFrames = 4;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 ActiveFrames = 3;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 RecoveryFrames = 7;

    // Ventaja calculada: Hitstun/Blockstun - (Active restantes + Recovery)
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 AdvantageOnBlock = 1;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 AdvantageOnHit = 4;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 BaseDamage = 400;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData", Meta = (Bitmask, BitmaskEnum = "/Script/SouthAmericaFightersCore.ECancelWindowFlags"))
    uint8 CancelFlags = 0;

    // Ventana exacta de cancelación tras el primer frame activo
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "FrameData")
    int32 CancelWindowDurationFrames = 6;
};

/**
 * Fila de DataTable para el plantel oficial sudamericano (DT_SouthAmericaRoster.json).
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFighterRosterRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FName Name;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FText DisplayName;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FString Country;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FString Era;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FString Archetype;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    int32 MaxHealth = 10000;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    int32 StunThreshold = 1000;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    int32 ForwardDashFrames = 16;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    int32 BackDashFrames = 20;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FString SignatureMoveNotation;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Roster")
    FString SignatureMoveName;
};
