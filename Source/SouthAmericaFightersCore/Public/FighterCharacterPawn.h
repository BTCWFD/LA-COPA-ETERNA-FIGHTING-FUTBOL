// FighterCharacterPawn.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Deterministic Fighter Pawn, Ball Projectile & Greyboxing AABB Visualizer
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Actor.h"
#include "FixedPointTypes.h"
#include "DeterministicFighterStateMachine.h"
#include "FighterVisualFeedbackComponent.h"
#include "FighterCharacterPawn.generated.h"

class USceneComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UInputAction;
class UInputMappingContext;

/**
 * Estado POD determinista de un proyectil de balón en el plano de combate 2.5D (Q32.32).
 * Copiable con memcpy para el Ring Buffer de Rollback GGPO.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FBallProjectileDeterministicStatePOD
{
    GENERATED_BODY()

    UPROPERTY(SaveGame)
    bool bIsActive = false;

    UPROPERTY(SaveGame)
    int32 OwnerPlayerIndex = 0; // 0 = P1, 1 = P2

    UPROPERTY(SaveGame)
    FFixedVector2D Position;

    UPROPERTY(SaveGame)
    FFixedVector2D Velocity;

    /** Durabilidad de choque de proyectiles: 2 puntos para el Bati-Cañonazo cargado de El Cañón, 1 para proyectiles estándar */
    UPROPERTY(SaveGame)
    int32 RemainingClashHitPoints = 1;

    UPROPERTY(SaveGame)
    int32 BaseDamage = 1100;

    UPROPERTY(SaveGame)
    int32 AdvantageOnBlock = -3;

    UPROPERTY(SaveGame)
    int32 AdvantageOnHit = 12;

    UPROPERTY(SaveGame)
    int32 RemainingLifetimeFrames = 120;

    /** True si el balón fue reflejado por "El Escorpión" (214+SK) de El Loco, incrementando su velocidad un 35% */
    UPROPERTY(SaveGame)
    bool bReflectedByScorpion = false;
};

/**
 * Actor de Proyectil de Balón Determinista (Bati-Cañonazo, Pase Filtrado, Efecto Jabulani, Folha Seca).
 */
UCLASS(BlueprintType, Blueprintable)
class SOUTHAMERICAFIGHTERSCORE_API ADeterministicBallProjectile : public AActor
{
    GENERATED_BODY()

public:
    ADeterministicBallProjectile();

    /** Inicializa el proyectil en coordenadas Q32.32. */
    void SpawnDeterministicBall(
        int32 InOwnerPlayerIndex,
        const FFixedVector2D& SpawnPos,
        const FFixedVector2D& LaunchVelocity,
        int32 InClashHitPoints,
        int32 InBaseDamage,
        int32 InAdvBlock = -3,
        int32 InAdvHit = 12);

    /** Paso de física en punto fijo Q32.32 a 60 Hz. */
    void StepDeterministicBallFrame();

    /** Invierte el propietario y acelera el proyectil un 35% al ser reflejado por El Escorpión (214+SK). */
    void ReflectByScorpionKick(int32 NewOwnerPlayerIndex);

    /** Caja de colisión AABB del balón en punto fijo Q32.32 (Radio = 220 mm). */
    FFixedAABB GetBallHitboxAABB() const;

    /** Sincroniza el Transform 3D de Unreal desde Q32.32 y dibuja la Hitbox AABB en modo Greyboxing. */
    void SyncBallVisualTransform(bool bDrawGreyboxAABB);

    const FBallProjectileDeterministicStatePOD& GetBallState() const { return BallState; }
    void SaveBallState(FBallProjectileDeterministicStatePOD& OutState) const { OutState = BallState; }
    void LoadBallState(const FBallProjectileDeterministicStatePOD& InState) { BallState = InState; }
    void ConsumeClashHitPoints(int32 Amount);
    void DeactivateBall() { BallState.bIsActive = false; SetActorHiddenInGame(true); }

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Ball|Components")
    TObjectPtr<UStaticMeshComponent> BallMeshComponent;

private:
    FBallProjectileDeterministicStatePOD BallState;
};

/**
 * Pawn de Luchador Determinista a 60 Hz ("La Copa Eterna: Sangre y Potrero").
 * Posee la máquina de estados en punto fijo Q32.32, el componente de feedback técnico (Hitstop/Shake/Street-Ink CPD),
 * la captura de entradas a máscara de 16 bits (ECombatInputBits) y la visualización Greyboxing de cajas AABB.
 */
UCLASS(BlueprintType, Blueprintable)
class SOUTHAMERICAFIGHTERSCORE_API AFighterCharacterPawn : public APawn
{
    GENERATED_BODY()

public:
    AFighterCharacterPawn();

    virtual void BeginPlay() override;
    virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

    /** Inicializa el luchador para la ronda en posición Q32.32. */
    UFUNCTION(BlueprintCallable, Category = "Fighter|Deterministic")
    void InitializeFighterForRound(
        int32 InPlayerIndex,
        FName InFighterRosterID,
        FFixedPoint SpawnX,
        bool bStartFacingRight,
        int32 InMaxHealth = 10000);

    /** Captura y empaqueta los botones presionados actualmente en una máscara determinista de 16 bits (ECombatInputBits). */
    uint16 PollLocalRawInputBitmask() const;

    /** Permite inyectar una máscara de bits directa (para pruebas automatizadas, IA o reproducción de Replay). */
    void SetInjectedInputBitmask(uint16 InMask, bool bEnableOverride);

    /**
     * Convierte las coordenadas Q32.32 (metros de punto fijo) a centímetros de Unreal Engine (FVector)
     * para actualizar el Actor en el hilo de renderizado, y dibuja las cajas AABB en vivo (Greyboxing).
     * - Pushbox: Amarillo
     * - Hurtbox: Verde (Normal) / Azul Cian (Blockstun/Invulnerable)
     * - Hitbox: Rojo Intenso
     */
    void SyncVisualTransformFromFixedPoint(uint32 CurrentFrame, bool bDrawGreyboxAABBs = true);

    UFUNCTION(BlueprintPure, Category = "Fighter|Deterministic")
    UDeterministicFighterStateMachine* GetFighterStateMachine() const { return StateMachine; }

    UFUNCTION(BlueprintPure, Category = "Fighter|TechArt")
    UFighterVisualFeedbackComponent* GetVisualFeedbackComponent() const { return VisualFeedbackComponent; }

    UFUNCTION(BlueprintPure, Category = "Fighter|Identity")
    FName GetFighterRosterID() const { return FighterRosterID; }

    UFUNCTION(BlueprintPure, Category = "Fighter|Identity")
    int32 GetPlayerIndex() const { return PlayerIndex; }

    UFUNCTION(BlueprintPure, Category = "Fighter|Identity")
    int32 GetMaxHealth() const { return MaxHealth; }

public:
    /** Si es true, renderiza las cajas AABB (Pushbox, Hurtbox, Hitbox) en cada frame a 60 FPS para depuración de Frame Data. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fighter|Greyboxing")
    bool bEnableLiveAABBDebugDraw = true;

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Fighter|Components")
    TObjectPtr<USceneComponent> RootPivotComponent;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Fighter|Components")
    TObjectPtr<USkeletalMeshComponent> MainSkeletalMesh;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Fighter|Components")
    TObjectPtr<UFighterVisualFeedbackComponent> VisualFeedbackComponent;

    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> StateMachine;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fighter|Identity")
    FName FighterRosterID = TEXT("FENOMENO_BR");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fighter|Identity")
    int32 PlayerIndex = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fighter|Identity")
    int32 MaxHealth = 10000;

private:
    uint16 LiveHardwareInputMask = 0;
    uint16 InjectedOverrideMask = 0;
    bool bUseInjectedInputOverride = false;

    // Handlers para construcción instantánea de la máscara de 9 bits activos
    void OnInputUpPressed()     { LiveHardwareInputMask |= ECombatInputBits::Up; }
    void OnInputUpReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::Up; }
    void OnInputDownPressed()   { LiveHardwareInputMask |= ECombatInputBits::Down; }
    void OnInputDownReleased()  { LiveHardwareInputMask &= ~ECombatInputBits::Down; }
    void OnInputLeftPressed()   { LiveHardwareInputMask |= ECombatInputBits::Left; }
    void OnInputLeftReleased()  { LiveHardwareInputMask &= ~ECombatInputBits::Left; }
    void OnInputRightPressed()  { LiveHardwareInputMask |= ECombatInputBits::Right; }
    void OnInputRightReleased() { LiveHardwareInputMask &= ~ECombatInputBits::Right; }
    void OnInputLPPressed()     { LiveHardwareInputMask |= ECombatInputBits::LP; }
    void OnInputLPReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::LP; }
    void OnInputMPPressed()     { LiveHardwareInputMask |= ECombatInputBits::MP; }
    void OnInputMPReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::MP; }
    void OnInputHPPressed()     { LiveHardwareInputMask |= ECombatInputBits::HP; }
    void OnInputHPReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::HP; }
    void OnInputSKPressed()     { LiveHardwareInputMask |= ECombatInputBits::SK; }
    void OnInputSKReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::SK; }
    void OnInputGBPressed()     { LiveHardwareInputMask |= ECombatInputBits::GB; }
    void OnInputGBReleased()    { LiveHardwareInputMask &= ~ECombatInputBits::GB; }

    void DrawFixedAABBDebugBox(const FFixedAABB& Box, const FColor& Color, float Thickness = 2.0f) const;
};
