// FightingUIManagerSubsystem.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ - 4-Layer CommonUI Stack Architecture, Dual-Cursor Routing,
// 16-Player "La Concentracion" Lobby, EOS LAN/Wi-Fi Match Filter & Numpad Glyph Translator

#include "FightingUIManagerSubsystem.h"

UFightingInputGlyphDataAsset::UFightingInputGlyphDataAsset()
{
    auto AddGlyphRow = [this](const TCHAR* Token, const TCHAR* PS5, const TCHAR* Xbox, const TCHAR* FGC, const TCHAR* KB)
    {
        FMultiPlatformGlyphMapping Row;
        Row.AbstractToken = FName(Token);
        Row.PS5GlyphID = FName(PS5);
        Row.XboxGlyphID = FName(Xbox);
        Row.ArcadeFGCGlyphID = FName(FGC);
        Row.KeyboardGlyphID = FName(KB);
        GlyphMappings.Add(Row);
    };

    // Botones de ataque y mecánicas universales
    AddGlyphRow(TEXT("LP"), TEXT("PS5_Square"),   TEXT("XSX_X"),  TEXT("FGC_LP"), TEXT("KB_U"));
    AddGlyphRow(TEXT("MP"), TEXT("PS5_Triangle"), TEXT("XSX_Y"),  TEXT("FGC_MP"), TEXT("KB_I"));
    AddGlyphRow(TEXT("HP"), TEXT("PS5_R1"),       TEXT("XSX_RB"), TEXT("FGC_HP"), TEXT("KB_O"));
    AddGlyphRow(TEXT("LK"), TEXT("PS5_Cross"),    TEXT("XSX_A"),  TEXT("FGC_LK"), TEXT("KB_J"));
    AddGlyphRow(TEXT("HK"), TEXT("PS5_Circle"),   TEXT("XSX_B"),  TEXT("FGC_HK"), TEXT("KB_K"));
    AddGlyphRow(TEXT("SK"), TEXT("PS5_R1"),       TEXT("XSX_RB"), TEXT("FGC_SK"), TEXT("KB_L"));
    AddGlyphRow(TEXT("GB"), TEXT("PS5_R2"),       TEXT("XSX_RT"), TEXT("FGC_GB"), TEXT("KB_Space"));

    // Mociones direccionales Numpad y conectores
    AddGlyphRow(TEXT("236"),   TEXT("Motion_236_QCF"),   TEXT("Motion_236_QCF"),   TEXT("Motion_236_QCF"),   TEXT("Motion_236_QCF"));
    AddGlyphRow(TEXT("214"),   TEXT("Motion_214_QCB"),   TEXT("Motion_214_QCB"),   TEXT("Motion_214_QCB"),   TEXT("Motion_214_QCB"));
    AddGlyphRow(TEXT("623"),   TEXT("Motion_623_DP"),    TEXT("Motion_623_DP"),    TEXT("Motion_623_DP"),    TEXT("Motion_623_DP"));
    AddGlyphRow(TEXT("41236"), TEXT("Motion_41236_HCF"), TEXT("Motion_41236_HCF"), TEXT("Motion_41236_HCF"), TEXT("Motion_41236_HCF"));
    AddGlyphRow(TEXT("63214"), TEXT("Motion_63214_HCB"), TEXT("Motion_63214_HCB"), TEXT("Motion_63214_HCB"), TEXT("Motion_63214_HCB"));
    AddGlyphRow(TEXT("+"),     TEXT("Symbol_Plus"),      TEXT("Symbol_Plus"),      TEXT("Symbol_Plus"),      TEXT("Symbol_Plus"));
    AddGlyphRow(TEXT(">"),     TEXT("Symbol_NextCancel"),TEXT("Symbol_NextCancel"),TEXT("Symbol_NextCancel"),TEXT("Symbol_NextCancel"));
}

FName UFightingInputGlyphDataAsset::ResolveGlyphIDForToken(
    FName AbstractToken,
    EFightingInputGlyphProfile Profile) const
{
    for (const FMultiPlatformGlyphMapping& Row : GlyphMappings)
    {
        if (Row.AbstractToken == AbstractToken)
        {
            switch (Profile)
            {
            case EFightingInputGlyphProfile::PS5_DualSense:
                return Row.PS5GlyphID;
            case EFightingInputGlyphProfile::XSX_Gamepad:
                return Row.XboxGlyphID;
            case EFightingInputGlyphProfile::ArcadeStick_FGC:
                return Row.ArcadeFGCGlyphID;
            case EFightingInputGlyphProfile::KeyboardMouse:
            default:
                return Row.KeyboardGlyphID;
            }
        }
    }
    return AbstractToken;
}

void UFightingInputGlyphDataAsset::TranslateNumpadSequenceToGlyphs(
    const FString& NumpadNotation,
    EFightingInputGlyphProfile TargetProfile,
    TArray<FName>& OutGlyphSequenceIDs,
    FString& OutRichTextMarkup) const
{
    OutGlyphSequenceIDs.Reset();
    OutRichTextMarkup.Reset();

    if (NumpadNotation.IsEmpty())
    {
        return;
    }

    // Tokenizar por '+' y '>' preservando los delimitadores como glifos conectores
    FString CurrentToken;
    auto FlushToken = [&](const FString& TokenStr)
    {
        const FString Trimmed = TokenStr.TrimStartAndEnd();
        if (Trimmed.IsEmpty())
        {
            return;
        }
        const FName ResolvedGlyph = ResolveGlyphIDForToken(FName(*Trimmed), TargetProfile);
        OutGlyphSequenceIDs.Add(ResolvedGlyph);
        OutRichTextMarkup.Appendf(TEXT("<img id=\"%s\"/>"), *ResolvedGlyph.ToString());
    };

    for (int32 CharIdx = 0; CharIdx < NumpadNotation.Len(); ++CharIdx)
    {
        const TCHAR Ch = NumpadNotation[CharIdx];
        if (Ch == TEXT('+') || Ch == TEXT('>'))
        {
            FlushToken(CurrentToken);
            CurrentToken.Reset();

            const FString DelimStr = FString::Chr(Ch);
            FlushToken(DelimStr);
        }
        else
        {
            CurrentToken.AppendChar(Ch);
        }
    }
    FlushToken(CurrentToken);
}

// ============================================================================
// UFightingUIManagerSubsystem
// ============================================================================

void UFightingUIManagerSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    MasterGlyphDataAsset = NewObject<UFightingInputGlyphDataAsset>(this);

    // Inicializar cursores independientes P1 y P2
    DualCursorStates[0] = FDualCursorPlayerSelectionState();
    DualCursorStates[0].PlayerIndex = 0;
    DualCursorStates[0].NormalizedCursorUV = FVector2D(0.25f, 0.50f);
    DualCursorStates[0].HoveredRosterGridIndex = 0;
    DualCursorStates[0].SelectedKitColorPaletteIndex = 1;
    DualCursorStates[0].ActiveGlyphProfile = EFightingInputGlyphProfile::PS5_DualSense;

    DualCursorStates[1] = FDualCursorPlayerSelectionState();
    DualCursorStates[1].PlayerIndex = 1;
    DualCursorStates[1].NormalizedCursorUV = FVector2D(0.75f, 0.50f);
    DualCursorStates[1].HoveredRosterGridIndex = 1;
    DualCursorStates[1].SelectedKitColorPaletteIndex = 2;
    DualCursorStates[1].ActiveGlyphProfile = EFightingInputGlyphProfile::PS5_DualSense;

    // Inicializar las 4 canchas simultáneas de "La Concentración" (Lobby para 16 jugadores)
    LobbyPitchStations.SetNum(4);
    for (int32 StationIdx = 0; StationIdx < 4; ++StationIdx)
    {
        LobbyPitchStations[StationIdx].PitchStationIndex = StationIdx;
        LobbyPitchStations[StationIdx].bIsMatchInProgress = false;
    }

    bTournamentControllerDisconnectedModalActive = false;
    DisconnectedControllerPlayerIndex = -1;
}

void UFightingUIManagerSubsystem::Deinitialize()
{
    RegisteredLayerStacks.Empty();
    LobbyPitchStations.Empty();
    Super::Deinitialize();
}

void UFightingUIManagerSubsystem::RegisterRootLayerStack(
    EFightingUILayerID LayerID,
    UCommonActivatableWidgetStack* InWidgetStack)
{
    if (IsValid(InWidgetStack))
    {
        RegisteredLayerStacks.Add(LayerID, InWidgetStack);
    }
}

UCommonActivatableWidget* UFightingUIManagerSubsystem::PushWidgetToLayer(
    EFightingUILayerID LayerID,
    TSubclassOf<UCommonActivatableWidget> WidgetClass)
{
    if (!WidgetClass)
    {
        return nullptr;
    }

    if (const TObjectPtr<UCommonActivatableWidgetStack>* FoundStack = RegisteredLayerStacks.Find(LayerID))
    {
        if (IsValid(*FoundStack))
        {
            return (*FoundStack)->AddWidget<UCommonActivatableWidget>(WidgetClass);
        }
    }
    return nullptr;
}

void UFightingUIManagerSubsystem::ClearLayerStack(EFightingUILayerID LayerID)
{
    if (const TObjectPtr<UCommonActivatableWidgetStack>* FoundStack = RegisteredLayerStacks.Find(LayerID))
    {
        if (IsValid(*FoundStack))
        {
            (*FoundStack)->ClearWidgets();
        }
    }
}

void UFightingUIManagerSubsystem::ProcessDualCursorNavigationStep(
    int32 PlayerIndex,
    FVector2D AnalogDelta,
    int32 GridColumnDelta,
    int32 GridRowDelta,
    int32 TotalColumns,
    int32 TotalRows)
{
    if (PlayerIndex < 0 || PlayerIndex > 1)
    {
        return;
    }

    FDualCursorPlayerSelectionState& Cursor = DualCursorStates[PlayerIndex];
    if (Cursor.bIsLockedIn)
    {
        return;
    }

    // 1. Actualizar coordenadas UV libres del cursor virtual
    Cursor.NormalizedCursorUV.X = FMath::Clamp(Cursor.NormalizedCursorUV.X + AnalogDelta.X, 0.02f, 0.98f);
    Cursor.NormalizedCursorUV.Y = FMath::Clamp(Cursor.NormalizedCursorUV.Y + AnalogDelta.Y, 0.02f, 0.98f);

    // 2. Navegación discreta con D-Pad / Stick por la grilla de 10 Leyendas Sudamericanas (5 columnas x 2 filas)
    const int32 SafeCols = FMath::Max(1, TotalColumns);
    const int32 SafeRows = FMath::Max(1, TotalRows);
    const int32 TotalSlots = SafeCols * SafeRows;

    if (GridColumnDelta != 0 || GridRowDelta != 0)
    {
        int32 CurrentCol = Cursor.HoveredRosterGridIndex % SafeCols;
        int32 CurrentRow = Cursor.HoveredRosterGridIndex / SafeCols;

        CurrentCol = (CurrentCol + GridColumnDelta + SafeCols) % SafeCols;
        CurrentRow = (CurrentRow + GridRowDelta + SafeRows) % SafeRows;

        Cursor.HoveredRosterGridIndex = FMath::Clamp(CurrentRow * SafeCols + CurrentCol, 0, TotalSlots - 1);
    }
}

bool UFightingUIManagerSubsystem::SetDualCursorCharacterLockState(
    int32 PlayerIndex,
    FName CandidateFighterID,
    int32 PreferredKitPaletteIndex,
    bool bLockIn)
{
    if (PlayerIndex < 0 || PlayerIndex > 1)
    {
        return false;
    }

    FDualCursorPlayerSelectionState& TargetCursor = DualCursorStates[PlayerIndex];
    const FDualCursorPlayerSelectionState& OtherCursor = DualCursorStates[1 - PlayerIndex];

    if (!bLockIn)
    {
        TargetCursor.bIsLockedIn = false;
        return true;
    }

    if (CandidateFighterID.IsNone())
    {
        return false;
    }

    int32 ResolvedPalette = FMath::Clamp(PreferredKitPaletteIndex, 1, 10);

    // Regla FIFA/CONMEBOL de Contraste en Mirror Match:
    // Si ambos jugadores eligen el mismo personaje con la misma camiseta, asignar automáticamente la equipación Suplente/Alternativa
    if (OtherCursor.bIsLockedIn &&
        OtherCursor.SelectedFighterID == CandidateFighterID &&
        OtherCursor.SelectedKitColorPaletteIndex == ResolvedPalette)
    {
        ResolvedPalette = (ResolvedPalette == 1) ? 2 : 1;
    }

    TargetCursor.SelectedFighterID = CandidateFighterID;
    TargetCursor.SelectedKitColorPaletteIndex = ResolvedPalette;
    TargetCursor.bIsLockedIn = true;
    return true;
}

FDualCursorPlayerSelectionState UFightingUIManagerSubsystem::GetDualCursorState(int32 PlayerIndex) const
{
    const int32 SafeIdx = FMath::Clamp(PlayerIndex, 0, 1);
    return DualCursorStates[SafeIdx];
}

bool UFightingUIManagerSubsystem::AreBothPlayersLockedIn() const
{
    return DualCursorStates[0].bIsLockedIn && DualCursorStates[1].bIsLockedIn;
}

void UFightingUIManagerSubsystem::UpdateLobbyPitchStation(const FLaConcentracionPitchStation& UpdatedStation)
{
    if (UpdatedStation.PitchStationIndex >= 0 && UpdatedStation.PitchStationIndex < LobbyPitchStations.Num())
    {
        LobbyPitchStations[UpdatedStation.PitchStationIndex] = UpdatedStation;
    }
}

bool UFightingUIManagerSubsystem::RequestJoinPitchStationQueue(
    int32 PitchStationIndex,
    const FString& PlayerOnlineHandle)
{
    if (PitchStationIndex < 0 || PitchStationIndex >= LobbyPitchStations.Num() || PlayerOnlineHandle.IsEmpty())
    {
        return false;
    }

    FLaConcentracionPitchStation& Station = LobbyPitchStations[PitchStationIndex];

    // Capacidad máxima de 16 jugadores en el lobby
    if (Station.Player1OnlineHandle.IsEmpty())
    {
        Station.Player1OnlineHandle = PlayerOnlineHandle;
        return true;
    }

    if (Station.Player2OnlineHandle.IsEmpty() && Station.Player1OnlineHandle != PlayerOnlineHandle)
    {
        Station.Player2OnlineHandle = PlayerOnlineHandle;
        Station.bIsMatchInProgress = true;
        return true;
    }

    if (!Station.ChallengerQueueHandles.Contains(PlayerOnlineHandle) &&
        Station.Player1OnlineHandle != PlayerOnlineHandle &&
        Station.Player2OnlineHandle != PlayerOnlineHandle)
    {
        Station.ChallengerQueueHandles.Add(PlayerOnlineHandle);
        return true;
    }

    return false;
}

bool UFightingUIManagerSubsystem::CanRejectEOSMatchCandidateWithoutPenalty(
    const FEOSMatchCandidateModalData& Candidate,
    bool bUserRequiresWiredLANOnly,
    int32 UserMaxAcceptablePingMs) const
{
    // 1. Si el rival está en Wi-Fi y el jugador activó el filtro "Solo Cable LAN" o siempre en Ranked Competitivo
    if (!Candidate.bIsOpponentOnWiredEthernet && bUserRequiresWiredLANOnly)
    {
        return true;
    }

    // 2. Si el Ping supera el umbral configurado por el usuario (por defecto 110ms)
    if (Candidate.PingMilliseconds > UserMaxAcceptablePingMs)
    {
        return true;
    }

    // 3. Si el Jitter supera 15ms o la pérdida de paquetes supera 2.0%
    if (Candidate.JitterMilliseconds > 15 || Candidate.PacketLossPercent > 2.0f)
    {
        return true;
    }

    return false;
}

void UFightingUIManagerSubsystem::NotifyTournamentControllerConnectionChange(
    int32 AffectedPlayerIndex,
    bool bIsConnected)
{
    if (!bIsConnected)
    {
        bTournamentControllerDisconnectedModalActive = true;
        DisconnectedControllerPlayerIndex = AffectedPlayerIndex;
    }
    else if (DisconnectedControllerPlayerIndex == AffectedPlayerIndex)
    {
        bTournamentControllerDisconnectedModalActive = false;
        DisconnectedControllerPlayerIndex = -1;
    }
}

bool UFightingUIManagerSubsystem::IsTournamentPauseModalActive(int32& OutDisconnectedPlayerIndex) const
{
    OutDisconnectedPlayerIndex = DisconnectedControllerPlayerIndex;
    return bTournamentControllerDisconnectedModalActive;
}

void UFightingUIManagerSubsystem::NotifyPlayerHardwareInputDetected(
    int32 PlayerIndex,
    EFightingInputGlyphProfile DetectedProfile)
{
    if (PlayerIndex >= 0 && PlayerIndex <= 1)
    {
        DualCursorStates[PlayerIndex].ActiveGlyphProfile = DetectedProfile;
    }
}
