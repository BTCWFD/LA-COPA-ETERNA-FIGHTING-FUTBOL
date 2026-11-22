// FighterVisualFeedbackComponent.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - AAA Technical Art & Deterministic Visual Feedback Pipeline
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FighterVisualFeedbackComponent.generated.h"

class USkeletalMeshComponent;
class UMaterialInstanceDynamic;

/**
 * Estados de aura competitiva de lectura instantánea (<16ms de reconocimiento visual).
 * Alimentan los Custom Primitive Data (Índices 0..4) del shader HLSL Street-Ink.
 */
UENUM(BlueprintType)
enum class EVisualCombatAura : uint8
{
    None                UMETA(DisplayName = "None (Neutral)"),
    Invulnerable_White  UMETA(DisplayName = "Invulnerable / Reversal (Pure White)"),
    SuperArmor_Gold     UMETA(DisplayName = "Super Armor / Garra Charrua (Gold)"),
    GuardCrush_Crimson  UMETA(DisplayName = "Guard Crush /Tarjeta Roja (Crimson)"),
    AltitudeDebuff_Green UMETA(DisplayName = "Altitude Hypoxia / Soroche (Toxic Green)")
};

/**
 * Selector de Dirección de Arte en Tiempo Real (Toggle `ArtStyleMode`: 0 = Street-Ink, 1 = Renaissance Sfumato).
 * Alimenta CustomPrimitiveData[7] y el Post-Process `M_PP_SfumatoChiaroscuro`.
 */
UENUM(BlueprintType)
enum class ECombatArtStyleMode : uint8
{
    StreetInk           = 0 UMETA(DisplayName = "0: Street-Ink Muralismo Sudamericano"),
    RenaissanceSfumato  = 1 UMETA(DisplayName = "1: Renacimiento Sfumato (Mona Lisa / Da Vinci)")
};

/**
 * Snapshot visual determinista sincronizado con el bucle de Rollback (GGPO).
 * Permite restaurar hitstop, fase de vibración y acumuladores de barro/sudor tras un rollback.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFighterVisualStateSnapshot
{
    GENERATED_BODY()

    UPROPERTY()
    uint32 FrameNumber = 0;

    UPROPERTY()
    int32 HitstopFramesRemaining = 0;

    UPROPERTY()
    bool bIsDefenderInHitstop = false;

    UPROPERTY()
    float ShakeAmplitudeCm = 0.0f;

    UPROPERTY()
    EVisualCombatAura ActiveAura = EVisualCombatAura::None;

    UPROPERTY()
    float AuraIntensity = 0.0f;

    UPROPERTY()
    float AccumulatedSweat = 0.0f;

    UPROPERTY()
    float AccumulatedPitchMud = 0.0f;
};

/**
 * Componente de Arte Técnico que gestiona:
 * 1. Hitstop determinista con congelamiento de UAnimInstance y vibración sinoidal de alta frecuencia (60Hz) en el defensor.
 * 2. Inyección zero-overhead vía CustomPrimitiveData (CPD) hacia el shader Street-Ink.
 * 3. Supresión de explosiones de Chaos Cloth durante rollbacks o teleports bruscos (ResetClothTeleportAndReset).
 * 4. Acumulación progresiva de sudor especular y barro de potrero por deslizamiento/knockdown.
 */
UCLASS(ClassGroup = (Custom), meta = (BlueprintSpawnableComponent))
class SOUTHAMERICAFIGHTERSCORE_API UFighterVisualFeedbackComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UFighterVisualFeedbackComponent();

    virtual void BeginPlay() override;

    /**
     * Ejecutado exactamente 1 vez por frame visual (60Hz) tras resolver la simulación determinista.
     * Controla el conteo regresivo de Hitstop, el offset oscilatorio del Mesh defensor y el decaimiento de Chaos Cloth.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void DeterministicVisualStep(uint32 CurrentFrame);

    /**
     * Dispara Hitstop síncrono para el atacante o el defensor.
     * @param FreezeFrames Número exacto de frames a 60fps durante los cuales se congela la pose de animación.
     * @param bIsDefender Si es true, aplica vibración horizontal de alta frecuencia (Shake) sobre el pivote visual.
     * @param ShakeAmplitudeCm Amplitud máxima en centímetros de la sacudida durante el hitstop (ej. 3.0cm ligero, 6.5cm counter-hit).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void TriggerHitstopAndShake(int32 FreezeFrames, bool bIsDefender, float ShakeAmplitudeCm = 3.0f);

    /**
     * Actualiza inmediatamente el estado de Rim Light competitivo en el Custom Primitive Data del SkeletalMesh.
     * CPD[0..2] = Color RGB Lineal, CPD[3] = Intensidad HDR, CPD[4] = Multiplicador de grosor de tinta.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void SetCompetitiveAuraState(EVisualCombatAura NewAura, float Intensity = 1.0f, float InkThicknessMultiplier = 1.0f);

    /**
     * Llamado por el subsistema de Rollback cuando ocurre una corrección de estado (>2 frames) o un teleport de animación.
     * Congela y reinicia las velocidades de partículas de Chaos Cloth por 2 frames para evitar artefactos elásticos.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void NotifyRollbackOrTeleportSnap(float PositionDeltaSqCm);

    /**
     * Actualiza los canales de desgaste ambiental del personaje (Sudor por gasto de Gambeta/Stamina y Barro por barridas/caídas).
     * CPD[5] = Sudor (Roughness drop + Specular micro-droplets), CPD[6] = Barro/Pasto en piernas y camiseta.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void UpdateSweatAndPitchDirt(float StaminaRatio, bool bTriggeredSlideOrKnockdown, float MudIncrement = 0.18f);

    /**
     * Captura y restaura el estado visual para sincronizar con el buffer circular de Rollback.
     */
    void CaptureVisualSnapshot(uint32 FrameNumber, FFighterVisualStateSnapshot& OutSnapshot) const;
    void RestoreVisualSnapshot(const FFighterVisualStateSnapshot& InSnapshot);

    /**
     * Conmuta en tiempo real entre Street-Ink (0) y Renacimiento Sfumato / Chiaroscuro Da Vinci (1).
     * Inyecta el valor en CustomPrimitiveData[7] (CPD[7]) sin coste de CPU ni recreación de MIDs.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void SetArtStyleMode(ECombatArtStyleMode NewArtStyleMode);

    UFUNCTION(BlueprintPure, Category = "Combat|TechArt")
    ECombatArtStyleMode GetArtStyleMode() const { return CurrentArtStyleMode; }

    /**
     * Asigna explícitamente el SkeletalMesh principal e indumentaria secundaria (camiseta holgada/bandana con Chaos Cloth).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|TechArt")
    void RegisterFighterMeshes(USkeletalMeshComponent* InMainBodyMesh, const TArray<USkeletalMeshComponent*>& InClothApparelMeshes);

protected:
    UPROPERTY(Transient)
    TObjectPtr<USkeletalMeshComponent> MainBodyMesh = nullptr;

    UPROPERTY(Transient)
    TArray<TObjectPtr<USkeletalMeshComponent>> ClothApparelMeshes;

    /** Ubicación relativa original del SkeletalMesh en el Actor para restaurar tras el Hitstop Shake */
    FVector BaseRelativeLocation = FVector::ZeroVector;

    /** Estado actual de Hitstop */
    int32 RemainingHitstopFrames = 0;
    bool bCurrentHitstopIsDefender = false;
    float CurrentShakeAmplitudeCm = 0.0f;

    /** Contador de frames de estabilización de Chaos Cloth tras un Rollback o Teleport */
    int32 ClothTeleportStabilizationFrames = 0;

    /** Estado actual de Aura, Desgaste y Estilo Artístico */
    EVisualCombatAura CurrentAura = EVisualCombatAura::None;
    ECombatArtStyleMode CurrentArtStyleMode = ECombatArtStyleMode::StreetInk;
    float CurrentAuraIntensity = 0.0f;
    float CurrentInkThicknessScale = 1.0f;
    float CurrentSweatAmount = 0.0f;
    float CurrentPitchMudAmount = 0.0f;

private:
    void ApplyCustomPrimitiveDataToMeshes(const FLinearColor& RimColor, float RimIntensity, float InkScale);
    void SetMeshesAnimationPauseState(bool bPaused);
};
