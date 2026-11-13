// FightingUIManagerSubsystem.h - SouthAmericaFightersCore
// Unreal Engine 5.4+ - 4-Layer CommonUI Stack Architecture, Dual-Cursor Routing,
// 16-Player "La Concentracion" Lobby, EOS LAN/Wi-Fi Match Filter & Numpad Glyph Translator
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Engine/DataAsset.h"
#include "CommonActivatableWidget.h"
#include "Widgets/CommonActivatableWidgetContainer.h"
#include "FightingUIManagerSubsystem.generated.h"

/**
 * Las 4 Capas Jerárquicas de CommonUI para "La Copa Eterna".
 */
UENUM(BlueprintType)
enum class EFightingUILayerID : uint8
{
    Layer1_CombatHUD            UMETA(DisplayName = "Layer 1: Combat HUD (Barras SDF, Reloj 99s, Frame Meter, Ping)"),
    Layer2_FrontendAndLobby     UMETA(DisplayName = "Layer 2: Frontend & La Concentracion (Lobby 16P + Selector Dual-Cursor)"),
    Layer3_PauseAndTrainingMenu UMETA(DisplayName = "Layer 3: Pause & Training Menu (Grabadora Multi-Slot, Frame Data, Inputs)"),
    Layer4_SystemModal          UMETA(DisplayName = "Layer 4: System Modal (Alerta Rival EOS LAN/Wi-Fi + Desconexión Mando)")
};

/**
 * Perfiles de iconos de hardware con conmutación en <1 frame al detectar actividad en el bus de entrada.
 */
UENUM(BlueprintType)
enum class EFightingInputGlyphProfile : uint8
{
    PS5_DualSense   UMETA(DisplayName = "PlayStation 5 DualSense (Cuadrado, Triángulo, R1, R2)"),
    XSX_Gamepad     UMETA(DisplayName = "Xbox Series X|S Controller (X, Y, RB, RT)"),
    ArcadeStick_FGC UMETA(DisplayName = "FGC Arcade Stick / Leverless (LP, MP, HP, SK, GB)"),
    KeyboardMouse   UMETA(DisplayName = "PC Keyboard (WASD / UIJK / Space)")
};

/**
 * Mapeo de un comando abstracto o moción Numpad hacia los 4 perfiles de glifos.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FMultiPlatformGlyphMapping
{
    GENERATED_BODY()

    /** Token abstracto (ej. "LP", "MP", "HP", "SK", "GB", "236", "623", "41236") */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Glyphs")
    FName AbstractToken = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Glyphs")
    FName PS5GlyphID = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Glyphs")
    FName XboxGlyphID = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Glyphs")
    FName ArcadeFGCGlyphID = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Glyphs")
    FName KeyboardGlyphID = NAME_None;
};

/**
 * DataAsset de Glifos Multiplataforma y Traductor Instantáneo de Notación Numpad (ej. "236+SK" -> Iconos Visuales).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UFightingInputGlyphDataAsset : public UDataAsset
{
    GENERATED_BODY()

public:
    UFightingInputGlyphDataAsset();

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Glyphs")
    TArray<FMultiPlatformGlyphMapping> GlyphMappings;

    /**
     * Devuelve el ID de glifo (compatible con RichTextImageDecorator y SVG/SDF Atlas) para un token dado.
     */
    UFUNCTION(BlueprintPure, Category = "Combat|UI|Glyphs")
    FName ResolveGlyphIDForToken(FName AbstractToken, EFightingInputGlyphProfile Profile) const;

    /**
     * Traduce instantáneamente una secuencia Numpad (ej. "236+SK", "623+HP", "41236+LP+MP")
     * en una lista ordenada de IDs de glifos y una cadena RichText lista para UCommonRichTextBlock.
     */
    UFUNCTION(BlueprintPure, Category = "Combat|UI|Glyphs")
    void TranslateNumpadSequenceToGlyphs(
        const FString& NumpadNotation,
        EFightingInputGlyphProfile TargetProfile,
        TArray<FName>& OutGlyphSequenceIDs,
        FString& OutRichTextMarkup) const;
};

/**
 * Estado independiente de cada cursor (P1 y P2) en la pantalla de Selección de Leyendas y Escenarios.
 * Garantiza soporte Dual-Cursor sin que CommonUI robe el foco entre mandos locales.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FDualCursorPlayerSelectionState
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    int32 PlayerIndex = 0;

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    FVector2D NormalizedCursorUV = FVector2D(0.25f, 0.50f);

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    int32 HoveredRosterGridIndex = 0;

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    FName SelectedFighterID = NAME_None;

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    int32 SelectedKitColorPaletteIndex = 1; // 1..10 (Titular, Suplente, Retro 90s, Dorada...)

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    bool bIsLockedIn = false;

    UPROPERTY(BlueprintReadOnly, Category = "DualCursor")
    EFightingInputGlyphProfile ActiveGlyphProfile = EFightingInputGlyphProfile::PS5_DualSense;
};

/**
 * Estado de una de las 4 Canchas Simultáneas en el Lobby Social "La Concentración" (hasta 16 jugadores por sala).
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FLaConcentracionPitchStation
{
    GENERATED_BODY()

    /** Índice de cancha (0 = Potrero Central, 1 = Cancha Sur, 2 = Cancha Norte, 3 = Cancha techada) */
    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    int32 PitchStationIndex = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    FString Player1OnlineHandle;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    FString Player2OnlineHandle;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    int32 Player1WinStreak = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    int32 CurrentRoundScoreP1 = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    int32 CurrentRoundScoreP2 = 0;

    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    bool bIsMatchInProgress = false;

    /** Cola de retadores esperando turno ("Ganador queda en cancha") */
    UPROPERTY(BlueprintReadOnly, Category = "Lobby|LaConcentracion")
    TArray<FString> ChallengerQueueHandles;
};

/**
 * Telemetría pre-partida de Rival Encontrado (EOS Matchmaking) mostrada en el Layer 4 (SystemModalLayer).
 * Permite al jugador rechazar sin penalización conexiones Wi-Fi inestables o con alto Jitter.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FEOSMatchCandidateModalData
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    FString OpponentSessionID;

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    FName OpponentFederationBadgeID = FName(TEXT("Badge_ARG"));

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    int32 PingMilliseconds = 24;

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    int32 JitterMilliseconds = 2;

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    float PacketLossPercent = 0.0f;

    /** true = Cable Ethernet RJ45 (Icono LAN), false = Inalámbrico (Icono Wi-Fi + Alerta de Jitter) */
    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    bool bIsOpponentOnWiredEthernet = true;

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    bool bIsCrossplayMatch = false;

    UPROPERTY(BlueprintReadWrite, Category = "Matchmaking|EOS")
    int32 SuggestedRollbackDelayFrames = 1;
};

/**
 * Subsistema Maestro de UI/UX (CommonUI) para Unreal Engine 5.4+.
 * Administra:
 * - La Pila Jerárquica de 4 Capas (`UCommonActivatableWidgetStack`).
 * - El enrutamiento Dual-Cursor independiente para P1 y P2 en Selección de Leyendas.
 * - El estado de las 4 Canchas Simultáneas del Lobby de 16 jugadores ("La Concentración").
 * - Los Modales de Sistema de Capa 4 (Filtro Pre-Partida LAN vs Wi-Fi / Jitter y Desconexión de Mando en Torneo).
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UFightingUIManagerSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    // ========================================================================
    // 1. Gestión de la Pila Jerárquica de 4 Capas (CommonActivatableWidgetStack)
    // ========================================================================

    /**
     * Registra los 4 contenedores `UCommonActivatableWidgetStack` creados por el Primary Game Layout.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Layers")
    void RegisterRootLayerStack(EFightingUILayerID LayerID, UCommonActivatableWidgetStack* InWidgetStack);

    /**
     * Empuja y activa un `UCommonActivatableWidget` en la capa especificada (Layer 1..4).
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Layers")
    UCommonActivatableWidget* PushWidgetToLayer(
        EFightingUILayerID LayerID,
        TSubclassOf<UCommonActivatableWidget> WidgetClass);

    /**
     * Limpia todos los widgets activos en una capa específica.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Layers")
    void ClearLayerStack(EFightingUILayerID LayerID);

    // ========================================================================
    // 2. Enrutamiento Dual-Cursor Independiente (P1 y P2 simultáneos en Layer 2)
    // ========================================================================

    /**
     * Procesa el desplazamiento 2D y navegación por grilla de un jugador (0 = P1, 1 = P2)
     * sin interferir ni robar el foco del otro jugador en el Selector de Leyendas.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|DualCursor")
    void ProcessDualCursorNavigationStep(
        int32 PlayerIndex,
        FVector2D AnalogDelta,
        int32 GridColumnDelta,
        int32 GridRowDelta,
        int32 TotalColumns = 5,
        int32 TotalRows = 2);

    /**
     * Confirma o cancela la selección de personaje y paleta de camiseta (1..10), resolviendo colisiones de color espejo.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|DualCursor")
    bool SetDualCursorCharacterLockState(
        int32 PlayerIndex,
        FName CandidateFighterID,
        int32 PreferredKitPaletteIndex,
        bool bLockIn);

    UFUNCTION(BlueprintPure, Category = "Combat|UI|DualCursor")
    FDualCursorPlayerSelectionState GetDualCursorState(int32 PlayerIndex) const;

    UFUNCTION(BlueprintPure, Category = "Combat|UI|DualCursor")
    bool AreBothPlayersLockedIn() const;

    // ========================================================================
    // 3. Lobby de 16 Jugadores "La Concentración" (4 Canchas Simultáneas)
    // ========================================================================

    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Lobby")
    void UpdateLobbyPitchStation(const FLaConcentracionPitchStation& UpdatedStation);

    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Lobby")
    bool RequestJoinPitchStationQueue(int32 PitchStationIndex, const FString& PlayerOnlineHandle);

    UFUNCTION(BlueprintPure, Category = "Combat|UI|Lobby")
    TArray<FLaConcentracionPitchStation> GetAllLobbyPitchStations() const { return LobbyPitchStations; }

    // ========================================================================
    // 4. Layer 4 System Modals (EOS LAN vs Wi-Fi Match Filter & Tournament Pause)
    // ========================================================================

    /**
     * Evalúa si el jugador local tiene derecho a rechazar sin penalización de rango al rival encontrado por EOS
     * (Permitido si el rival usa Wi-Fi y el filtro exige cable LAN, o si Ping > MaxPingMs, o Jitter > 15ms).
     */
    UFUNCTION(BlueprintPure, Category = "Combat|UI|SystemModal")
    bool CanRejectEOSMatchCandidateWithoutPenalty(
        const FEOSMatchCandidateModalData& Candidate,
        bool bUserRequiresWiredLANOnly,
        int32 UserMaxAcceptablePingMs = 110) const;

    /**
     * Activa el modal de Capa 4 cuando un mando se desconecta a mitad de una pelea de torneo presencial.
     */
    UFUNCTION(BlueprintCallable, Category = "Combat|UI|SystemModal")
    void NotifyTournamentControllerConnectionChange(int32 AffectedPlayerIndex, bool bIsConnected);

    UFUNCTION(BlueprintPure, Category = "Combat|UI|SystemModal")
    bool IsTournamentPauseModalActive(int32& OutDisconnectedPlayerIndex) const;

    // ========================================================================
    // 5. Detección Instantánea de Perfil de Glifos (<1 Frame)
    // ========================================================================

    UFUNCTION(BlueprintCallable, Category = "Combat|UI|Glyphs")
    void NotifyPlayerHardwareInputDetected(int32 PlayerIndex, EFightingInputGlyphProfile DetectedProfile);

    UFUNCTION(BlueprintPure, Category = "Combat|UI|Glyphs")
    UFightingInputGlyphDataAsset* GetMasterGlyphDataAsset() const { return MasterGlyphDataAsset; }

private:
    UPROPERTY(Transient)
    TMap<EFightingUILayerID, TObjectPtr<UCommonActivatableWidgetStack>> RegisteredLayerStacks;

    UPROPERTY(Transient)
    TObjectPtr<UFightingInputGlyphDataAsset> MasterGlyphDataAsset = nullptr;

    FDualCursorPlayerSelectionState DualCursorStates[2];
    TArray<FLaConcentracionPitchStation> LobbyPitchStations;

    bool bTournamentControllerDisconnectedModalActive = false;
    int32 DisconnectedControllerPlayerIndex = -1;
};
