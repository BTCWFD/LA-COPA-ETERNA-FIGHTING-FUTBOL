// StageDefinition.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "FixedPointTypes.h"
#include "StageDefinition.generated.h"

/**
 * Límites físicos deterministas (en milímetros de punto fijo) y salud de muro para cada zona de un estadio CONMEBOL.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FStageZoneBounds
{
    GENERATED_BODY()

    /** Coordenada X del muro izquierdo expresada en milímetros (punto fijo Q32.32). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Bounds")
    int64 LeftWallFixedMm = -1250000; // -1250.0m / -1250u

    /** Coordenada X del muro derecho expresada en milímetros (punto fijo Q32.32). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Bounds")
    int64 RightWallFixedMm = 1250000; // +1250.0m / +1250u

    /** Impactos de Wall Splat / Knockback pesado necesarios para producir Wall Break hacia la siguiente zona. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Bounds")
    int32 MaxWallHealth = 3;

    constexpr FFixedPoint GetLeftWallFixed() const
    {
        return FFixedPoint::FromMillimeters(LeftWallFixedMm);
    }

    constexpr FFixedPoint GetRightWallFixed() const
    {
        return FFixedPoint::FromMillimeters(RightWallFixedMm);
    }
};

/**
 * Definición de fila de DataTable para los 10 estadios míticos de la CONMEBOL con soporte de Wall Break y Wwise reactivo.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FStageDataRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage")
    FName StageID;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage")
    FText DisplayName;

    /** Límites iniciales dentro de la cancha principal (Zona A). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    FStageZoneBounds ZoneABounds;

    /** Límites extendidos tras ejecutar un Wall Break (Zona B: Explanada, Caminito, Museo, etc.). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    FStageZoneBounds ZoneBBounds;

    /** Grupo de Switch en Audiokinetic Wwise 2023.1+ para controlar la transición musical del estadio. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Audio")
    FName WwiseMusicSwitchGroup = TEXT("SWG_Stage_MusicZone");

    /** Estado del Switch Wwise durante el combate en Zona A (Cancha). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Audio")
    FName WwiseZoneSwitchStateA = TEXT("ZoneA_Pitch");

    /** Estado del Switch Wwise tras la transición por Wall Break hacia Zona B. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Audio")
    FName WwiseZoneSwitchStateB = TEXT("ZoneB_Exterior");

    /** Tempo base (BPM) de la percusión del estadio para sincronizar animaciones de hinchada y cánticos. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Audio")
    float BaseTempoBPM = 120.0f;
};
