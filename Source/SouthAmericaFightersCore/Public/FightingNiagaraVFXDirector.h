// FightingNiagaraVFXDirector.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Deterministic Niagara VFX Subsystem, Competitive Hit/Block Encoding & Elemental Ball Trails
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "FightingNiagaraVFXDirector.generated.h"

class UNiagaraSystem;
class UNiagaraComponent;
class USkeletalMeshComponent;
class UPoseableMeshComponent;
class UMaterialInterface;

/**
 * Codificación visual competitiva de impactos para lectura instantánea (<16ms).
 */
UENUM(BlueprintType)
enum class ECombatImpactVFXType : uint8
{
    HitNormal               UMETA(DisplayName = "Hit Normal (Chispa Dorada + Briznas de Césped)"),
    CounterHit              UMETA(DisplayName = "Counter Hit (Estallido Carmesí + Onda de Choque)"),
    BlockStandard           UMETA(DisplayName = "Block Standard (Escudo Hexagonal Azul Cian)"),
    BlockPlusFrameAdvantage UMETA(DisplayName = "Block Plus on Block (Escudo Cian con Destello Amarillo/Naranja +4)"),
    GambetaParryPerfect     UMETA(DisplayName = "Gambeta Parry Perfecto (Anillo Blanco/Dorado + Ghost Mesh Trail)")
};

/**
 * Identidad elemental del balón ("NS_SuperBall_Trail") según la selección nacional CONMEBOL.
 */
UENUM(BlueprintType)
enum class ESouthAmericaBallElement : uint8
{
    None                                UMETA(DisplayName = "Standard Leather Ball (Sin Envoltura)"),
    Brazil_CanarinhaSpinRibbons         UMETA(DisplayName = "Brasil: Cintas Verde-Amarela con Efecto Magnus"),
    Argentina_AlbicelesteSupersonicFire UMETA(DisplayName = "Argentina: Fuego Azul Celeste Supersónico"),
    Bolivia_AltiplanoEmeraldVacuum      UMETA(DisplayName = "Bolivia: Distorsión de Vacío Verde Esmeralda (3600m)"),
    Venezuela_VinotintoLightning        UMETA(DisplayName = "Venezuela: Relámpago Vinotinto de Alta Tensión"),
    Uruguay_CharruaObsidianMeteor       UMETA(DisplayName = "Uruguay: Meteoro Celeste y Obsidiana (Garra Charrúa)"),
    Colombia_CafeteroSolarVortex        UMETA(DisplayName = "Colombia: Vórtice Solar Tricolor (40°C)")
};

/**
 * Registro determinista de un sistema Niagara instanciado en un frame específico.
 * Permite podar efectos especulativos si un Rollback de GGPO invalida un impacto predicho localmente.
 */
USTRUCT()
struct SOUTHAMERICAFIGHTERSCORE_API FSpawnedVFXRollbackRecord
{
    GENERATED_BODY()

    UPROPERTY()
    uint32 SpawnFrame = 0;

    UPROPERTY()
    uint32 EventHash = 0;

    UPROPERTY()
    TWeakObjectPtr<UNiagaraComponent> ActiveComponent = nullptr;
};

/**
 * Subsistema de Mundo que orquesta todos los efectos Niagara con determinismo de semilla (`RandomSeed = CurrentFrame`):
 * 1. Codificación cromática de Hit / Counter-Hit / Block Standard / Plus on Block (ej. Bati-Cañonazo Cargado +4) / Gambeta Parry.
 * 2. Orientación física de briznas de césped y tierra según `HitVelocityVector`.
 * 3. Generación de Ghost Mesh Trails para Gambeta Parry Perfecto.
 * 4. Envoltura elemental del balón (`NS_SuperBall_Trail`) por selección nacional y acoplamiento con `La Garúa` (Lima).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UFightingNiagaraVFXDirector : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    /**
     * Registra los assets maestros de Niagara al cargar el escenario.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    void RegisterCombatNiagaraTemplates(
        UNiagaraSystem* InHitSparkSystem,
        UNiagaraSystem* InBlockShieldHexSystem,
        UNiagaraSystem* InGambetaParryRingSystem,
        UNiagaraSystem* InSuperBallTrailSystem,
        UMaterialInterface* InGhostTrailMaterial);

    /**
     * Instancia de forma determinista el efecto de impacto/bloqueo con `User.DeterministicSeed = CurrentFrame`.
     * Si `bWasBlocked == true` y `FrameAdvantageOnBlock > 0` (ej. Bati-Cañonazo Cargado +4), eleva automáticamente
     * el efecto a `BlockPlusFrameAdvantage` (escudo hexagonal cian que parpadea en amarillo/naranja intenso).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    UNiagaraComponent* SpawnDeterministicImpactVFX(
        uint32 CurrentFrame,
        ECombatImpactVFXType ImpactType,
        const FVector& ImpactLocationCm,
        const FVector& HitVelocityVectorCmPerSec,
        int32 FrameAdvantageOnBlock = 0,
        bool bIsRollbackReSimulation = false);

    /**
     * Genera una captura espectral (Ghost Mesh Trail) de la pose exacta del personaje al ejecutar un Gambeta Parry Perfecto.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    void SpawnGambetaGhostMeshTrail(
        uint32 CurrentFrame,
        USkeletalMeshComponent* SourceFighterMesh,
        const FLinearColor& GhostTint = FLinearColor(1.0f, 0.82f, 0.18f, 0.85f),
        float LifetimeSeconds = 0.22f);

    /**
     * Activa o actualiza frame a frame la envoltura elemental del balón (`NS_SuperBall_Trail`) según la selección nacional.
     * También actualiza la posición previa y actual del balón para el shader volumétrico de `La Garúa` en Lima.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    void UpdateSuperBallElementalTrail(
        uint32 CurrentFrame,
        ESouthAmericaBallElement BallElement,
        const FVector& BallPositionCm,
        const FVector& BallVelocityCmPerSec,
        float SpinRateRPM = 1800.0f);

    /**
     * Llamado por el motor de Rollback cuando se rebobina al frame `RollbackTargetFrame`.
     * Destruye inmediatamente cualquier partícula predicha en frames `>= RollbackTargetFrame` que haya quedado invalidada.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    void PruneSpeculativeVFXFromRollback(uint32 RollbackTargetFrame);

    /**
     * Paso determinista por frame (60Hz) para actualizar el contador de 3 frames del post-proceso `PP_StreetInk_Impact`
     * y el decaimiento de los Ghost Mesh Trails.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|NiagaraVFX")
    void TickDeterministicVFXFrame(uint32 CurrentFrame);

    /** Devuelve el peso normalizado (1.0, 0.66, 0.33, 0.0) del pulso de 3 frames `PP_StreetInk_Impact` */
    UFUNCTION(BlueprintPure, Category = "Combat|NiagaraVFX")
    float GetStreetInkImpactNormalizedWeight(FVector2D& OutScreenImpactUV) const;

    /** Devuelve los parámetros de disipación volumétrica del balón de fuego para el shader `EvaluateLimaGaruaFogDissipation` */
    UFUNCTION(BlueprintPure, Category = "Combat|NiagaraVFX")
    void GetActiveBallFogCarvingData(
        FVector& OutBallCurrentPosCm,
        FVector& OutBallPrevPosCm,
        float& OutCavityRadiusCm,
        float& OutTrailFadeFactor,
        FLinearColor& OutElementalGlowColor) const;

private:
    UPROPERTY(Transient)
    TObjectPtr<UNiagaraSystem> HitSparkTemplate = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UNiagaraSystem> BlockShieldHexTemplate = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UNiagaraSystem> GambetaParryRingTemplate = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UNiagaraSystem> SuperBallTrailTemplate = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UMaterialInterface> GhostTrailMaterialTemplate = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UNiagaraComponent> ActiveSuperBallTrailComponent = nullptr;

    UPROPERTY(Transient)
    TArray<FSpawnedVFXRollbackRecord> SpawnHistoryRingBuffer;

    struct FActiveGhostMeshEntry
    {
        TWeakObjectPtr<UPoseableMeshComponent> PoseableMesh;
        uint32 SpawnFrame = 0;
        uint32 DurationFrames = 13;
    };
    TArray<FActiveGhostMeshEntry> ActiveGhostMeshes;

    // Estado del Post-Proceso de 3 frames PP_StreetInk_Impact
    int32 StreetInkImpactFramesRemaining = 0;
    FVector2D LastHeavyImpactScreenUV = FVector2D(0.5f, 0.5f);

    // Estado del balón para disipación de niebla La Garúa
    ESouthAmericaBallElement CurrentBallElement = ESouthAmericaBallElement::None;
    FVector CurrentBallPosCm = FVector::ZeroVector;
    FVector PreviousBallPosCm = FVector::ZeroVector;
    float CurrentBallCavityRadiusCm = 0.0f;
    float CurrentBallTrailFade = 0.0f;
    FLinearColor CurrentBallGlowColor = FLinearColor::Black;

    uint32 ComputeImpactEventHash(ECombatImpactVFXType Type, const FVector& LocationCm, uint32 Frame) const;
};
