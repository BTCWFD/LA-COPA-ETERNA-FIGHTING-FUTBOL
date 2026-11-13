// TrainingModeSubsystem.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DeterministicFighterStateMachine.h"
#include "BossAIController.h"
#include "TrainingModeSubsystem.generated.h"

/**
 * Modos de comportamiento del Dummy en el Modo Entrenamiento ("El Potrero").
 */
UENUM(BlueprintType)
enum class EDummyStateMode : uint8
{
    StandIdle           UMETA(DisplayName = "Stand Idle"),
    CrouchIdle          UMETA(DisplayName = "Crouch Idle"),
    JumpLoop            UMETA(DisplayName = "Continuous Jump"),
    BlockAll            UMETA(DisplayName = "Block All (Auto High/Low/Crossup)"),
    BlockAfterFirstHit  UMETA(DisplayName = "Block After First Hit (Combo Check)"),
    RandomBlock         UMETA(DisplayName = "Random Block (50/50)"),
    RecordingInput      UMETA(DisplayName = "Recording Player Inputs (Slot)"),
    PlaybackMultiSlot   UMETA(DisplayName = "Probabilistic Multi-Slot Playback")
};

/**
 * Ranura de grabación de inputs para el Dummy de Entrenamiento (hasta 600 frames = 10 segundos a 60 Hz).
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FDummyRecordingSlot
{
    GENERATED_BODY()

    static constexpr int32 MaxFramesPerSlot = 600; // 10 segundos exactos a 60 Hz

    /** Buffer de máscaras de bits de 16 bits (ECombatInputBits) por frame grabado. */
    UPROPERTY(BlueprintReadOnly, Category = "Training|Recording")
    TArray<uint16> FrameInputs;

    /** Orientación original del Dummy en el frame 0 de la grabación (para auto-flip al cambiar de lado). */
    UPROPERTY(BlueprintReadOnly, Category = "Training|Recording")
    bool bRecordedFacingRight = true;

    /** Peso de selección probabilística cuando la reproducción aleatoria multi-slot está activa (0 = deshabilitado). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Training|Recording", meta = (ClampMin = "0", ClampMax = "100"))
    int32 SelectionWeight = 25;

    /** Habilita o deshabilita esta ranura en la rotación de reproducción multi-slot. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Training|Recording")
    bool bIsSlotEnabled = false;

    void InitializeSlot()
    {
        FrameInputs.Reset(MaxFramesPerSlot);
        bRecordedFacingRight = true;
    }

    bool HasRecordedData() const
    {
        return FrameInputs.Num() > 0;
    }
};

/**
 * Snapshot completo de situación de entrenamiento (Save/Load State instantáneo en 1 frame).
 */
struct FTrainingSituationSnapshot
{
    FFighterDeterministicStatePOD Player1State;
    FFighterDeterministicStatePOD Player2State;
    uint32 SavedChecksum = 0;
    bool bHasValidSnapshot = false;
};

/**
 * Subsistema de Modo Entrenamiento Avanzado ("El Potrero" / Estadio Vacío).
 * Incluye 8 ranuras de grabación de 600 frames con reproducción probabilística,
 * Save/Load State instantáneo (< 0.02 ms), inversión automática de bits horizontales
 * y sistema de Reversals exactos al Frame 1 (Wake-up / On-Block / On-Hit).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UTrainingModeSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    static constexpr int32 TotalRecordingSlots = 8;

    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    /** Vincula las máquinas de estado deterministas de P1 y P2 (Dummy). */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode")
    void BindTrainingFighters(UDeterministicFighterStateMachine* InPlayer1, UDeterministicFighterStateMachine* InDummyPlayer2);

    /** Cambia el modo de estado activo del Dummy. */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode")
    void SetDummyMode(EDummyStateMode NewMode);

    UFUNCTION(BlueprintPure, Category = "TrainingMode")
    EDummyStateMode GetDummyMode() const { return CurrentDummyMode; }

    /** Inicia la grabación en una de las 8 ranuras (0 a 7). */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|Recording")
    bool StartRecordingSlot(int32 SlotIndex, bool bCurrentFacingRight);

    /** Detiene la grabación activa. */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|Recording")
    void StopRecording();

    /** Inicia la reproducción probabilística ponderada entre las ranuras habilitadas con datos. */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|Recording")
    bool StartProbabilisticPlayback();

    /** Configura el peso probabilístico y estado de habilitación de una ranura (0 a 7). */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|Recording")
    void ConfigureSlotWeight(int32 SlotIndex, int32 Weight, bool bEnabled);

    /** Guarda instantáneamente la situación exacta de combate (posiciones Q32.32, barras, velocidades y estados). */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|SaveState")
    bool SaveInstantSituation();

    /** Restaura en 1 frame la situación guardada previamente mediante copia POD determinista. */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|SaveState")
    bool LoadInstantSituation();

    /**
     * Configura una secuencia de inputs de Reversal que el Dummy ejecutará en el Frame 1 exacto
     * al salir de Blockstun, Hitstun o HardKnockdown (Wake-up).
     */
    UFUNCTION(BlueprintCallable, Category = "TrainingMode|Reversal")
    void SetFrameOneReversalSequence(const TArray<int32>& InReversalBitmasks, bool bTriggerOnBlock, bool bTriggerOnHit, bool bTriggerOnWakeup);

    /**
     * Paso determinista a 60 Hz para el Dummy: graba inputs o devuelve la máscara de entrada que debe ejecutar P2.
     */
    uint16 EvaluateDummyFrameInput(uint16 Player1InputWhenRecording);

    /**
     * Invierte automáticamente los bits Left (1<<2) y Right (1<<3) si la orientación actual del Dummy
     * difiere de la orientación con la que se grabó la secuencia.
     */
    static uint16 FlipHorizontalInputBitsIfNeeded(uint16 RawMask, bool bRecordedFacingRight, bool bCurrentFacingRight);

private:
    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> Player1SM;

    UPROPERTY(Transient)
    TObjectPtr<UDeterministicFighterStateMachine> DummyPlayer2SM;

    UPROPERTY()
    TArray<FDummyRecordingSlot> RecordingSlots;

    EDummyStateMode CurrentDummyMode = EDummyStateMode::StandIdle;

    int32 ActiveRecordingSlotIndex = 0;
    int32 ActivePlaybackSlotIndex = -1;
    int32 CurrentPlaybackFrameCursor = 0;

    FTrainingSituationSnapshot SavedSituation;
    FRandomStream DeterministicRNG;

    // Estado de Reversals exactos al Frame 1
    EFighterActionState PreviousDummyActionState = EFighterActionState::Idle;
    TArray<uint16> ReversalInputSequence;
    int32 ActiveReversalFrameCursor = -1;
    bool bReversalFacingRightAtStart = true;
    bool bReversalOnBlock = false;
    bool bReversalOnHit = false;
    bool bReversalOnWakeup = false;

    int32 SelectWeightedRandomSlot();
    uint16 ComputeAutoBlockBitmask() const;
};
