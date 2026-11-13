// FighterAnimInstance.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - 60FPS Stepped Animation Bridge, Control Rig Smear Frames (1.25x),
// KawaiiPhysics/Spring Hair Solver (El Pibe / El Loco) & Chaos Cloth 5.4 AnimDrive Stiffness
#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "DeterministicFighterStateMachine.h"
#include "FighterAnimInstance.generated.h"

/**
 * Arquetipo de cadena de resortes secundarios (KawaiiPhysics / AnimNode_SpringBone)
 * para las melenas icónicas del plantel sudamericano.
 */
UENUM(BlueprintType)
enum class EFighterHairArchetype : uint8
{
    StandardShort           UMETA(DisplayName = "Corte Clásico (Sin Cadena de Resortes)"),
    ElPibe_Curly90sMane     UMETA(DisplayName = "El Pibe: Melena Rizada Años 90 (Rebote Elástico Radial)"),
    ElLoco_LongFlowingLocks UMETA(DisplayName = "El Loco: Melena Larga Suelta (Inercia Fluida con Viento)"),
    Guerrera_BraidedTail    UMETA(DisplayName = "Trenza / Coleta Larga (Péndulo Balístico)")
};

/**
 * Pesos de exageración de extremidades ("Smear / Exaggeration Control Rig") evaluados a 60Hz.
 * Escalan tibia/botín hasta 1.25x durante los frames activos de voleas, chilenas y puntazos
 * para maximizar el impacto visual sin alterar los hitboxes AABB en punto fijo Q32.32.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FControlRigSmearFrameWeights
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    bool bEnableSmearDeformation = false;

    /** Escala no uniforme en tibia y botín derecho (1.0f en reposo -> 1.25f en Active Frames de patada/volea) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    FVector RightTibiaAndBootScale = FVector::OneVector;

    /** Escala no uniforme en tibia y botín izquierdo (1.0f en reposo -> 1.25f en Active Frames de chilena/barrida) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    FVector LeftTibiaAndBootScale = FVector::OneVector;

    /** Escala en puño/antebrazo delantero para golpes de mano/despeje de arquero */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    FVector LeadHandScale = FVector::OneVector;

    /** Escala craneal sutil (1.15x) en el frame activo de Cabezazo Palomita */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    FVector HeaderCrownScale = FVector::OneVector;

    /** Vector tangente del arco de golpeo para orientar el Mesh de Smear Frame */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ControlRig|Smear")
    FVector SwingArcTangentLocal = FVector::ForwardVector;
};

/**
 * Parámetros deterministas para el solver de cadenas de resortes (KawaiiPhysics / AnimGraph Spring Solver)
 * aplicados a las melenas de El Pibe y El Loco, bandanas y cordones.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FSecondaryHairSpringChainParams
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    EFighterHairArchetype HairArchetype = EFighterHairArchetype::ElPibe_Curly90sMane;

    /** Amortiguación del resorte (0.05..0.45) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    float Damping = 0.14f;

    /** Rigidez de retorno a la pose original del rizo/mechón (0.05..0.60) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    float Stiffness = 0.28f;

    /** Radio de colisión esférica contra cráneo, cuello y clavículas en centímetros */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    float CapsuleCollisionRadiusCm = 5.5f;

    /** Fuerza inercial + viento aparente en espacio mundo inyectada al solver cada frame */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    FVector WorldInertialWindForce = FVector::ZeroVector;

    /** Congela la integración del pelo durante los frames de Hitstop para mantener silueta de impacto */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "SpringSolver|Hair")
    float SolverAlpha = 1.0f;
};

/**
 * Reglas de mapas de peso y rigidez dinámica para Chaos Cloth en Unreal Engine 5.4.
 * Evita que las camisetas holgadas de los años 90 o los pantalones cortos atraviesen el cuerpo en rollbacks o teleports.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FChaosCloth54DynamicRules
{
    GENERATED_BODY()

    /**
     * AnimDriveStiffness:
     * - 0.18f en locomoción normal / idle (caída libre y pliegues naturales de casaca noventera).
     * - 0.95f durante Rollbacks, Teleports o Gambeta Dashes extremos para anclar la tela a la pose cinemática.
     */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ChaosCloth|UE5.4")
    float AnimDriveStiffness = 0.18f;

    /** Amortiguación de resorte hacia la malla animada */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ChaosCloth|UE5.4")
    float AnimDriveDamping = 0.25f;

    /** Escala global del mapa de peso MaxDistance (0.0cm en cuello/hombros/cintura -> 18.0cm en faldón inferior de camiseta) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ChaosCloth|UE5.4")
    float MaxDistanceScaleCm = 18.0f;

    /** Coeficiente de arrastre aerodinámico de la tela */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ChaosCloth|UE5.4")
    float AerodynamicDrag = 0.08f;

    /** Escala de velocidad lineal heredada del hueso raíz (0.0 en teleport para suprimir latigazo -> 0.75 en combate normal) */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "ChaosCloth|UE5.4")
    float LinearVelocityScale = 0.75f;
};

/**
 * Puente C++ de Animación Competitiva a 60 FPS para Unreal Engine 5.4+.
 * Conecta directamente `FFighterDeterministicStatePOD` con el AnimGraph, Control Rig y Chaos Cloth:
 * 1. Cuantización de tiempo a 60 FPS puros (`QuantizedSequenceExplicitTime`, cero interpolación engañosa en Startup/Active).
 * 2. Deformación de extremidades `1.25x` (Smear / Exaggeration Rig) en voleas y chilenas.
 * 3. Dinámica de melenas (KawaiiPhysics / Spring Solver) para El Pibe y El Loco.
 * 4. Control determinista de `AnimDriveStiffness` (`0.95` en rollbacks/teleports) para Chaos Cloth 5.4.
 */
UCLASS(Transient, Blueprintable)
class SOUTHAMERICAFIGHTERSCORE_API UFighterAnimInstance : public UAnimInstance
{
    GENERATED_BODY()

public:
    UFighterAnimInstance();

    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;

    /**
     * Sincroniza la instancia de animación directamente con el estado determinista Q32.32 del frame actual.
     * @param DeterministicState Estado POD de la máquina de estados del luchador.
     * @param bHadRollbackOrTeleportThisFrame Si es true, eleva `AnimDriveStiffness` a `0.95` y anula la inercia de tela/pelo.
     * @param bIsInHitstop Congela el solver secundario de pelo y mantiene el Smear Frame en su pico máximo.
     */
    void SyncFromDeterministicFighterState(
        const FFighterDeterministicStatePOD& DeterministicState,
        bool bHadRollbackOrTeleportThisFrame,
        bool bIsInHitstop);

    /**
     * Configura el arquetipo capilar del personaje (ej. `ElPibe_Curly90sMane` o `ElLoco_LongFlowingLocks`).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Animation")
    void SetFighterHairArchetype(EFighterHairArchetype InArchetype);

    /**
     * Cuantiza cualquier tiempo flotante al escalón exacto de 60.0 FPS (múltiplos de 0.01666667s).
     */
    UFUNCTION(BlueprintPure, Category = "Combat|Animation")
    static float QuantizeTimeToStepped60FPS(float RawTimeSeconds);

protected:
    /** Estado actual reflejado para el AnimGraph */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    EFighterActionState CurrentActionState = EFighterActionState::Idle;

    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    FName ActiveMoveID = NAME_None;

    /** Frame entero exacto dentro de la animación actual (0, 1, 2...) */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    int32 SteppedStateFrameIndex = 0;

    /** Tiempo explícito cuantizado a 60 FPS (`SteppedStateFrameIndex / 60.0f`) para nodos Sequence Evaluator (Sin Interpolación) */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    float QuantizedSequenceExplicitTime = 0.0f;

    /** Desactiva la interpolación sub-frame en el Sequence Evaluator durante ataques para garantizar lectura pura de Overheads/Lows */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    bool bForceSteppedPoseNoInterpolation = true;

    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    bool bIsFacingRight = true;

    UPROPERTY(BlueprintReadOnly, Category = "Combat|AnimGraph")
    FVector2D PlanarVelocityMetersPerSec = FVector2D::ZeroVector;

    /** Salida hacia el nodo Control Rig en el AnimGraph para Smear Frames (1.25x en tibia/botín) */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|ControlRig")
    FControlRigSmearFrameWeights SmearRigWeights;

    /** Salida hacia el nodo KawaiiPhysics / Spring Solver para las melenas de El Pibe y El Loco */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|SpringHair")
    FSecondaryHairSpringChainParams HairSpringParams;

    /** Salida hacia el Interactor de Chaos Cloth 5.4 */
    UPROPERTY(BlueprintReadOnly, Category = "Combat|ChaosCloth")
    FChaosCloth54DynamicRules ChaosClothRules;

private:
    int32 TeleportStiffnessHoldFrames = 0;

    void EvaluateControlRigSmearWeights(const FFighterDeterministicStatePOD& State);
    void EvaluateHairSpringChainSolver(const FFighterDeterministicStatePOD& State, bool bHadTeleport, bool bIsInHitstop);
    void EvaluateChaosCloth54Parameters(const FFighterDeterministicStatePOD& State, bool bHadTeleport);
    void PushChaosClothParametersToSkeletalMesh();
};
