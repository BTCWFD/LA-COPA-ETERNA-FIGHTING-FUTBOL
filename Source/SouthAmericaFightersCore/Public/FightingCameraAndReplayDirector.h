// FightingCameraAndReplayDirector.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - Deterministic Q32.32 2.5D Camera Rig & Replay Theater with Live Takeover
#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "FixedPointTypes.h"
#include "DeterministicFighterStateMachine.h"
#include "FightingCameraAndReplayDirector.generated.h"

/**
 * Estado POD determinista de la cámara 2.5D en punto fijo Q32.32.
 * Incluido en el snapshot de Rollback para evitar tirones de cámara al re-simular frames.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FCameraTransformPOD
{
    GENERATED_BODY()

    /** Posición horizontal (Eje X de combate) en metros Q32.32 */
    UPROPERTY(SaveGame)
    FFixedPoint FocusX = FFixedPoint(0);

    /** Posición vertical (Eje Z de altura) en metros Q32.32 */
    UPROPERTY(SaveGame)
    FFixedPoint FocusZ = FFixedPoint::FromMillimeters(1150);

    /** Velocidades del integrador Spring-Damper en Q32.32 */
    UPROPERTY(SaveGame)
    FFixedPoint VelocityX = FFixedPoint(0);

    UPROPERTY(SaveGame)
    FFixedPoint VelocityZ = FFixedPoint(0);

    /** Multiplicador de Zoom competitivo (1.00x = 1000mm a 1.25x = 1250mm en escala normalizada) */
    UPROPERTY(SaveGame)
    FFixedPoint ZoomRatio = FFixedPoint(1);

    /** Distancia de cámara en el eje Y (profundidad perpendicular al plano de lucha) en metros Q32.32 */
    UPROPERTY(SaveGame)
    FFixedPoint ArmDistanceMeters = FFixedPoint::FromMillimeters(4800);

    /** Ángulo de inclinación (Dutch Roll) en grados Q32.32 usado durante Counter-Hits y Wall Breaks */
    UPROPERTY(SaveGame)
    FFixedPoint DutchAngleDegrees = FFixedPoint(0);

    /** FOV Horizontal en grados Q32.32 */
    UPROPERTY(SaveGame)
    FFixedPoint FieldOfViewDegrees = FFixedPoint(54);

    /** Contador de cinemática de Wall Break (0 = Cámara de combate estándar, 1..85 = Secuencia de ruptura de alambrado) */
    UPROPERTY(SaveGame)
    int32 WallBreakSequenceFrame = 0;

    /** Dirección de la ruptura de escenario (+1 Derecha, -1 Izquierda) */
    UPROPERTY(SaveGame)
    int32 WallBreakDirectionSign = 1;
};

/**
 * Snapshot completo de una partida en un frame dado (Jugadores + Cámara) para Keyframes de Replay (cada 300 frames) y Live Takeover.
 */
struct SOUTHAMERICAFIGHTERSCORE_API FMatchDeterministicSnapshotPOD
{
    uint32 FrameNumber = 0;
    FFighterDeterministicStatePOD Player1State;
    FFighterDeterministicStatePOD Player2State;
    FCameraTransformPOD CameraState;
};

/**
 * Entrada de inputs por frame para el archivo binario de Replay (.safreplay).
 */
struct SOUTHAMERICAFIGHTERSCORE_API FReplayFrameInputPair
{
    uint16 Player1InputMask = 0;
    uint16 Player2InputMask = 0;
};

/**
 * Director de Cámara 2.5D Determinista (Q32.32).
 * - Calcula el Centro de Gravedad Dinámico (ponderando 60% al atacante activo en combo/presión y 40% al defensor).
 * - Integra un sistema Spring-Damper crítico en punto fijo Q32.32 para seguimiento suave y determinista.
 * - Regula el Zoom entre 1.00x (combate abierto en media cancha) y 1.25x (clinch/esquina a corta distancia).
 * - Orquesta la cinemática de 85 frames de Wall Break (Ruptura de Alambrado / Valla Publicitaria).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UFightingCameraDirector : public UObject
{
    GENERATED_BODY()

public:
    UFightingCameraDirector();

    /**
     * Inicializa los límites del escenario actual en metros Q32.32.
     */
    void InitializeStageBounds(FFixedPoint InLeftBoundaryMeters, FFixedPoint InRightBoundaryMeters);

    /**
     * Avanza exactamente 1 frame (1/60s) la física determinista de la cámara 2.5D en formato Q32.32.
     */
    void StepDeterministicCamera(
        const FFighterDeterministicStatePOD& P1State,
        const FFighterDeterministicStatePOD& P2State);

    /**
     * Inicia la secuencia cinemática de 85 frames de Ruptura de Escenario (Wall Break).
     * @param DirectionSign +1 hacia el borde derecho, -1 hacia el borde izquierdo.
     * @param NewLeftBoundMeters Nuevo límite izquierdo de la zona desbloqueada tras el Wall Break.
     * @param NewRightBoundMeters Nuevo límite derecho de la zona desbloqueada tras el Wall Break.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Camera")
    void TriggerWallBreakCameraSequence(
        int32 DirectionSign,
        FFixedPoint NewLeftBoundMeters,
        FFixedPoint NewRightBoundMeters);

    /**
     * Convierte el estado Q32.32 de la cámara a FTransform de Unreal Engine (en centímetros) exclusivamente para el Render Thread.
     */
    UFUNCTION(BlueprintPure, Category = "Combat|Camera")
    FTransform GetVisualCameraTransformCm(float& OutHorizontalFOV) const;

    const FCameraTransformPOD& GetCameraState() const { return CameraState; }
    void SaveCameraState(FCameraTransformPOD& OutState) const { OutState = CameraState; }
    void LoadCameraState(const FCameraTransformPOD& InState) { CameraState = InState; }

private:
    FCameraTransformPOD CameraState;
    FFixedPoint StageLeftBoundMeters = FFixedPoint(-10);
    FFixedPoint StageRightBoundMeters = FFixedPoint(10);

    void StepWallBreakCinematic85Frames(
        const FFighterDeterministicStatePOD& P1State,
        const FFighterDeterministicStatePOD& P2State);
};

/**
 * Subsistema de Teatro de Repeticiones ("VAR Interactivo") con soporte de Búsqueda Instantánea (Keyframes cada 300 frames)
 * y Live Takeover (tomar el control en vivo de Jugador 1 o Jugador 2 desde cualquier frame de la repetición).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UReplayPlaybackSubsystem : public UObject
{
    GENERATED_BODY()

public:
    UReplayPlaybackSubsystem();

    static constexpr uint32 KeyframeIntervalFrames = 300U; // 1 Keyframe cada 5.0 segundos (60fps)

    /**
     * Carga un flujo binario de repetición (Header + Tabla de Inputs + Pre-generación de Keyframes cada 300 frames).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Replay")
    bool LoadReplayFromBinary(const TArray<uint8>& BinaryReplayData);

    /**
     * Exporta la grabación actual a un buffer binario compacto con cabecera mágica 'SAFR'.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Replay")
    bool SaveReplayToBinary(TArray<uint8>& OutBinaryReplayData) const;

    /**
     * Registra un frame durante una partida en vivo y almacena automáticamente un Keyframe cada 300 frames.
     */
    void RecordLiveMatchFrame(
        uint32 FrameNumber,
        uint16 P1Input,
        uint16 P2Input,
        const FMatchDeterministicSnapshotPOD& CurrentSnapshot);

    /**
     * Salta instantáneamente a cualquier frame de la partida (< 1.5ms).
     * Restaura el Keyframe múltiplo de 300 más cercano y re-simula determinísticamente el residuo (0..299 frames).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Replay")
    bool JumpToFrame(uint32 TargetFrame);

    /**
     * LIVE TAKEOVER ("Entrenamiento sobre Repetición"):
     * Detiene la reproducción pasiva en el frame actual, clona el estado exacto de P1, P2 y Cámara (Q32.32),
     * y transfiere el mando inmediatamente al jugador humano para ensayar respuestas o castigos reales.
     * @param ControlledPlayerIndex 0 para tomar el control de P1, 1 para tomar el control de P2.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|Replay")
    bool TakeControlOfReplayAtCurrentFrame(
        int32 ControlledPlayerIndex,
        UDeterministicFighterStateMachine* OutLiveP1Machine,
        UDeterministicFighterStateMachine* OutLiveP2Machine,
        UFightingCameraDirector* OutLiveCameraDirector);

    UFUNCTION(BlueprintPure, Category = "Combat|Replay")
    uint32 GetCurrentReplayFrame() const { return CurrentPlaybackFrame; }

    UFUNCTION(BlueprintPure, Category = "Combat|Replay")
    uint32 GetTotalReplayFrames() const { return static_cast<uint32>(RecordedInputs.Num()); }

    UFUNCTION(BlueprintPure, Category = "Combat|Replay")
    bool IsInLiveTakeoverMode() const { return bIsLiveTakeoverActive; }

    UFUNCTION(BlueprintPure, Category = "Combat|Replay")
    int32 GetLiveTakeoverControlledPlayer() const { return ActiveTakeoverPlayerIndex; }

    const FMatchDeterministicSnapshotPOD& GetCurrentSnapshot() const { return CurrentStateSnapshot; }

private:
    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> InternalSimP1 = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> InternalSimP2 = nullptr;

    UPROPERTY(Transient)
    TObjectPtr<UFightingCameraDirector> InternalSimCamera = nullptr;

    TArray<FReplayFrameInputPair> RecordedInputs;
    TArray<FMatchDeterministicSnapshotPOD> KeyframeSnapshots;

    FMatchDeterministicSnapshotPOD CurrentStateSnapshot;
    uint32 CurrentPlaybackFrame = 0;
    bool bIsLiveTakeoverActive = false;
    int32 ActiveTakeoverPlayerIndex = -1;

    void EnsureInternalSimulatorsInitialized();
    void RebuildKeyframesFromInputs();
};
