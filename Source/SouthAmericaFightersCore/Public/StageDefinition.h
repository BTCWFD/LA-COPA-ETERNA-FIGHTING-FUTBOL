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

    /** Coordenada X del muro izquierdo expresada en milímetros (punto fijo Q32.32: -12500 mm = -12.5m / -1250 cm). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Bounds")
    int64 LeftWallFixedMm = -12500; // -12.5m / -1250 cm

    /** Coordenada X del muro derecho expresada en milímetros (punto fijo Q32.32: +12500 mm = +12.5m / +1250 cm). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Bounds")
    int64 RightWallFixedMm = 12500; // +12.5m / +1250 cm

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

    /** Altitud canónica del Estadio Hernando Siles de La Paz (3600m s.n.m., alineada con DT_StagesCONMEBOL.json y GDD). */
    static constexpr float LaPazAltitudeMeters = 3600.0f;

    /** Altitud sobre el nivel del mar en metros (3600.0f para STAGE_HERNANDO_SILES en La Paz). */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Environment")
    float AltitudeMeters = 0.0f;

    float GetEffectiveAltitudeMeters() const
    {
        if (AltitudeMeters > 0.0f)
        {
            return AltitudeMeters;
        }
        if (StageID == TEXT("STAGE_HERNANDO_SILES") || StageID == TEXT("Stage_LaPaz_3600m"))
        {
            return LaPazAltitudeMeters;
        }
        return 0.0f;
    }
};

/**
 * Fila plana de DataTable importada directamente desde DT_StagesCONMEBOL.json.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FStageCONMEBOLTableRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage")
    FName StageID;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage")
    FText DisplayName;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage")
    FString Country;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    int32 ZoneAWidth = 2400;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    int32 WallHealth = 3;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Environment")
    FString ClimateLighting;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Audio")
    float BPM = 120.0f;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    FString ZoneAName;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Zones")
    FString ZoneBName;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Stage|Environment")
    float AltitudeMeters = 0.0f;

    /** Convierte esta fila de tabla plana en la estructura FStageDataRow con límites Q32.32 Zona A/B. */
    FStageDataRow ToStageDataRow() const
    {
        FStageDataRow OutRow;
        OutRow.StageID = StageID;
        OutRow.DisplayName = DisplayName;

        const int64 HalfZoneAMm = static_cast<int64>(FMath::Max(1000, ZoneAWidth)) * 5LL;
        OutRow.ZoneABounds.LeftWallFixedMm = -HalfZoneAMm;
        OutRow.ZoneABounds.RightWallFixedMm = HalfZoneAMm;
        OutRow.ZoneABounds.MaxWallHealth = FMath::Max(1, WallHealth);

        const int64 HalfZoneBMm = HalfZoneAMm + 6000LL;
        OutRow.ZoneBBounds.LeftWallFixedMm = -HalfZoneBMm;
        OutRow.ZoneBBounds.RightWallFixedMm = HalfZoneBMm;
        OutRow.ZoneBBounds.MaxWallHealth = 99;

        OutRow.BaseTempoBPM = (BPM > 0.0f) ? BPM : 120.0f;
        OutRow.AltitudeMeters = (AltitudeMeters > 0.0f)
            ? AltitudeMeters
            : ((StageID == TEXT("STAGE_HERNANDO_SILES") || StageID == TEXT("Stage_LaPaz_3600m"))
                ? FStageDataRow::LaPazAltitudeMeters
                : 0.0f);
        return OutRow;
    }
};
