// CopaEternaArcadeLadder.cpp - SouthAmericaFightersCore
// Unreal Engine 5.4+ C++20 - Deterministic 5-Match CONMEBOL Arcade Ladder & Post-Match Telemetry Implementation
#include "CopaEternaArcadeLadder.h"

namespace CopaEternaRosterConstants
{
    static const FName AllPlayableFighters[16] = {
        TEXT("FENOMENO_BR"),
        TEXT("BRUXO_BR"),
        TEXT("CANON_AR"),
        TEXT("PULGA_AR"),
        TEXT("PIBE_CO"),
        TEXT("LOCO_CO"),
        TEXT("PISTOLERO_UY"),
        TEXT("MATADOR_UY"),
        TEXT("BAMBAM_CL"),
        TEXT("REY_CL"),
        TEXT("BULLDOG_PY"),
        TEXT("MAESTRO_PE"),
        TEXT("TREN_EC"),
        TEXT("HURACAN_VE"),
        TEXT("DIABLO_BO"),
        TEXT("GENERAL_FR")
    };

    static const FName BossFighterID = TEXT("BOSS_VAR_ZERO");
}

void UCopaEternaArcadeLadderSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    InitializeDeterministicLadder(TEXT("FENOMENO_BR"), 19301950U);
}

void UCopaEternaArcadeLadderSubsystem::InitializeDeterministicLadder(FName InPlayerFighterID, uint32 InDeterministicSeed)
{
    SelectedPlayerFighterID = InPlayerFighterID.IsNone() ? FName(TEXT("FENOMENO_BR")) : InPlayerFighterID;
    ActiveDeterministicSeed = (InDeterministicSeed == 0U) ? 19301950U : InDeterministicSeed;
    CurrentMatchIndex = 0;
    CurrentStage = ECopaLadderStage::OctavosDeFinal;
    TotalRoundsLostInTournament = 0;
    TotalRankSCount = 0;
    ContinuesUsed = 0;
    bSecretBossPhase2Unlocked = false;

    const FName CanonicalRivalID = ResolveCanonicalRivalForFighter(SelectedPlayerFighterID);

    // Construir bolsa de candidatos para Octavos, Cuartos y Semifinal excluyendo al propio jugador y a su Rival de Gran Final
    TArray<FName, TInlineAllocator<16>> CandidatePool;
    for (const FName& FighterID : CopaEternaRosterConstants::AllPlayableFighters)
    {
        if (FighterID != SelectedPlayerFighterID && FighterID != CanonicalRivalID)
        {
            CandidatePool.Add(FighterID);
        }
    }

    // Mezcla Fisher-Yates 100% determinista usando Xorshift32 + hash del nombre del jugador
    uint32 RngState = ActiveDeterministicSeed ^ GetTypeHash(SelectedPlayerFighterID);
    if (RngState == 0U)
    {
        RngState = 0x9E3779B9U;
    }

    for (int32 i = CandidatePool.Num() - 1; i > 0; --i)
    {
        const uint32 RandVal = NextDeterministicRandom(RngState);
        const int32 SwapIdx = static_cast<int32>(RandVal % static_cast<uint32>(i + 1));
        CandidatePool.Swap(i, SwapIdx);
    }

    LadderNodes.Reset(TotalLadderMatches);
    LadderNodes.SetNum(TotalLadderMatches);

    // Match 1: Octavos de Final
    LadderNodes[0].Stage = ECopaLadderStage::OctavosDeFinal;
    LadderNodes[0].OpponentFighterID = CandidatePool[0];
    LadderNodes[0].StageArenaID = ResolveHomeStageForFighter(CandidatePool[0]);
    LadderNodes[0].bIsClassicRivalryMatch = false;

    // Match 2: Cuartos de Final
    LadderNodes[1].Stage = ECopaLadderStage::CuartosDeFinal;
    LadderNodes[1].OpponentFighterID = CandidatePool[1];
    LadderNodes[1].StageArenaID = ResolveHomeStageForFighter(CandidatePool[1]);
    LadderNodes[1].bIsClassicRivalryMatch = false;

    // Match 3: Semifinal Continental
    LadderNodes[2].Stage = ECopaLadderStage::Semifinal;
    LadderNodes[2].OpponentFighterID = CandidatePool[2];
    LadderNodes[2].StageArenaID = ResolveHomeStageForFighter(CandidatePool[2]);
    LadderNodes[2].bIsClassicRivalryMatch = false;

    // Match 4: Gran Final CONMEBOL (Rivalidad Clásica)
    LadderNodes[3].Stage = ECopaLadderStage::GranFinalCONMEBOL;
    LadderNodes[3].OpponentFighterID = CanonicalRivalID;
    LadderNodes[3].StageArenaID = ResolveHomeStageForFighter(CanonicalRivalID);
    LadderNodes[3].bIsClassicRivalryMatch = true;

    // Match 5: Desafío Supremo - El Juez Supremo (V.A.R. - ZERO)
    LadderNodes[4].Stage = ECopaLadderStage::DesafioSupremo_VARZero;
    LadderNodes[4].OpponentFighterID = CopaEternaRosterConstants::BossFighterID;
    LadderNodes[4].StageArenaID = ((NextDeterministicRandom(RngState) & 1U) == 0U)
        ? FName(TEXT("STAGE_MARACANA"))
        : FName(TEXT("STAGE_BOMBONERA"));
    LadderNodes[4].bIsClassicRivalryMatch = false;
    LadderNodes[4].bSecretBossPhase2Unlocked = false;
}

FFixedPoint UCopaEternaArcadeLadderSubsystem::ComputeFixedPointPerformanceScore(const FPostMatchTelemetry& Telemetry)
{
    // Cálculo 100% determinista en punto fijo Q32.32:
    // + Diferencial neto de daño: (P1DamageDealt - P2DamageDealt / 2) * 0.45
    // + MaxCombo * 320
    // + PerfectParries (Gambetas Perfectas) * 1500
    // + WallBreaks * 1200
    // + RemainingFrames * 1.25 (5/4)
    // - Penalización por rondas perdidas: RoundsLostByPlayer * 2500

    const int32 ClampedP1Dmg = FMath::Max(0, Telemetry.P1DamageDealt);
    const int32 ClampedP2Dmg = FMath::Max(0, Telemetry.P2DamageDealt);
    const int32 NetDamageComponent = FMath::Max(0, ClampedP1Dmg - (ClampedP2Dmg / 2));

    const FFixedPoint DamageScore = FFixedPoint(NetDamageComponent) * FFixedPoint::FromMillimeters(450);
    const FFixedPoint ComboScore = FFixedPoint(FMath::Clamp(Telemetry.MaxCombo, 0, 99) * 320);
    const FFixedPoint ParryScore = FFixedPoint(FMath::Clamp(Telemetry.PerfectParries, 0, 20) * 1500);
    const FFixedPoint WallBreakScore = FFixedPoint(FMath::Clamp(Telemetry.WallBreaks, 0, 5) * 1200);
    const FFixedPoint TimeBonusScore = FFixedPoint(FMath::Clamp(Telemetry.RemainingFrames, 0, 5940)) * FFixedPoint::FromMillimeters(1250);
    const FFixedPoint RoundLossPenalty = FFixedPoint(FMath::Max(0, Telemetry.RoundsLostByPlayer) * 2500);

    const FFixedPoint TotalScore = DamageScore + ComboScore + ParryScore + WallBreakScore + TimeBonusScore - RoundLossPenalty;
    return (TotalScore < FFixedPoint(0)) ? FFixedPoint(0) : TotalScore;
}

ECombatStyleRank UCopaEternaArcadeLadderSubsystem::CalculateStyleRank(const FPostMatchTelemetry& Telemetry)
{
    const FFixedPoint FixedScore = ComputeFixedPointPerformanceScore(Telemetry);
    const int32 TruncatedScore = FixedScore.ToIntTruncated();

    if (TruncatedScore >= ThresholdRankS)
    {
        return ECombatStyleRank::Rank_S;
    }
    if (TruncatedScore >= ThresholdRankA)
    {
        return ECombatStyleRank::Rank_A;
    }
    if (TruncatedScore >= ThresholdRankB)
    {
        return ECombatStyleRank::Rank_B;
    }
    return ECombatStyleRank::Rank_C;
}

bool UCopaEternaArcadeLadderSubsystem::AdvanceLadder(bool bPlayerWon, const FPostMatchTelemetry& Telemetry)
{
    if (!LadderNodes.IsValidIndex(CurrentMatchIndex))
    {
        return false;
    }

    FPostMatchTelemetry EvaluatedTelemetry = Telemetry;
    EvaluatedTelemetry.ComputedPerformanceScore = ComputeFixedPointPerformanceScore(Telemetry);
    EvaluatedTelemetry.StyleRank = CalculateStyleRank(EvaluatedTelemetry);

    TotalRoundsLostInTournament += FMath::Max(0, EvaluatedTelemetry.RoundsLostByPlayer);

    if (!bPlayerWon)
    {
        ++ContinuesUsed;
        LadderNodes[CurrentMatchIndex].RecordedTelemetry = EvaluatedTelemetry;
        return false;
    }

    if (EvaluatedTelemetry.StyleRank == ECombatStyleRank::Rank_S)
    {
        ++TotalRankSCount;
    }

    FArcadeLadderMatchNode& CurrentNode = LadderNodes[CurrentMatchIndex];
    CurrentNode.RecordedTelemetry = EvaluatedTelemetry;
    CurrentNode.bIsCompleted = true;

    // Evaluar condición secreta al completar la Gran Final CONMEBOL (Match Index 3):
    // Desbloquea la Fase 2 secreta de V.A.R. - ZERO ("Tiempo de Descuento Infinito" + Rewind 90f)
    // si el jugador llegó a la final sin perder un solo round (0 rondas perdidas y 0 continues)
    // O si logró calificación Rank_S en la Gran Final.
    if (CurrentNode.Stage == ECopaLadderStage::GranFinalCONMEBOL)
    {
        const bool bFlawlessRun = (TotalRoundsLostInTournament == 0 && ContinuesUsed == 0);
        const bool bGrandFinalRankS = (EvaluatedTelemetry.StyleRank == ECombatStyleRank::Rank_S);

        bSecretBossPhase2Unlocked = (bFlawlessRun || bGrandFinalRankS);
        if (LadderNodes.IsValidIndex(4))
        {
            LadderNodes[4].bSecretBossPhase2Unlocked = bSecretBossPhase2Unlocked;
        }
    }

    ++CurrentMatchIndex;

    if (CurrentMatchIndex >= TotalLadderMatches)
    {
        CurrentStage = ECopaLadderStage::ChampionCrowned;
        OnArcadeTournamentCompleted.Broadcast(EvaluatedTelemetry.StyleRank);
        return true;
    }

    CurrentStage = LadderNodes[CurrentMatchIndex].Stage;
    OnArcadeStageAdvanced.Broadcast(CurrentStage, LadderNodes[CurrentMatchIndex]);
    return true;
}

bool UCopaEternaArcadeLadderSubsystem::GetCurrentMatchNode(FArcadeLadderMatchNode& OutNode) const
{
    if (!LadderNodes.IsValidIndex(CurrentMatchIndex))
    {
        return false;
    }
    OutNode = LadderNodes[CurrentMatchIndex];
    return true;
}

uint32 UCopaEternaArcadeLadderSubsystem::NextDeterministicRandom(uint32& InOutState)
{
    uint32 X = InOutState;
    X ^= X << 13;
    X ^= X >> 17;
    X ^= X << 5;
    InOutState = (X == 0U) ? 0x6D2B79F5U : X;
    return InOutState;
}

FName UCopaEternaArcadeLadderSubsystem::ResolveCanonicalRivalForFighter(FName PlayerFighterID)
{
    // Las 5 Rivalidades Clásicas del GDD + emparejamientos canónicos para los 16 luchadores
    if (PlayerFighterID == TEXT("FENOMENO_BR"))  return TEXT("CANON_AR");
    if (PlayerFighterID == TEXT("CANON_AR"))     return TEXT("FENOMENO_BR");
    if (PlayerFighterID == TEXT("PULGA_AR"))     return TEXT("PISTOLERO_UY");
    if (PlayerFighterID == TEXT("PISTOLERO_UY")) return TEXT("PULGA_AR");
    if (PlayerFighterID == TEXT("BRUXO_BR"))     return TEXT("PIBE_CO");
    if (PlayerFighterID == TEXT("PIBE_CO"))      return TEXT("BRUXO_BR");
    if (PlayerFighterID == TEXT("LOCO_CO"))      return TEXT("BULLDOG_PY");
    if (PlayerFighterID == TEXT("BULLDOG_PY"))   return TEXT("LOCO_CO");
    if (PlayerFighterID == TEXT("REY_CL"))       return TEXT("MAESTRO_PE");
    if (PlayerFighterID == TEXT("MAESTRO_PE"))   return TEXT("REY_CL");
    if (PlayerFighterID == TEXT("BAMBAM_CL"))    return TEXT("MATADOR_UY");
    if (PlayerFighterID == TEXT("MATADOR_UY"))   return TEXT("BAMBAM_CL");
    if (PlayerFighterID == TEXT("TREN_EC"))      return TEXT("HURACAN_VE");
    if (PlayerFighterID == TEXT("HURACAN_VE"))   return TEXT("TREN_EC");
    if (PlayerFighterID == TEXT("DIABLO_BO"))    return TEXT("GENERAL_FR");
    if (PlayerFighterID == TEXT("GENERAL_FR"))   return TEXT("DIABLO_BO");

    return TEXT("CANON_AR");
}

FName UCopaEternaArcadeLadderSubsystem::ResolveHomeStageForFighter(FName FighterID)
{
    if (FighterID == TEXT("FENOMENO_BR") || FighterID == TEXT("BRUXO_BR"))     return TEXT("STAGE_MARACANA");
    if (FighterID == TEXT("CANON_AR")    || FighterID == TEXT("PULGA_AR"))     return TEXT("STAGE_BOMBONERA");
    if (FighterID == TEXT("PISTOLERO_UY")|| FighterID == TEXT("MATADOR_UY"))   return TEXT("STAGE_CENTENARIO");
    if (FighterID == TEXT("PIBE_CO")     || FighterID == TEXT("LOCO_CO"))      return TEXT("STAGE_METROPOLITANO");
    if (FighterID == TEXT("BAMBAM_CL")   || FighterID == TEXT("REY_CL"))       return TEXT("STAGE_NUNOA");
    if (FighterID == TEXT("BULLDOG_PY"))                                        return TEXT("STAGE_DEFENSORES");
    if (FighterID == TEXT("MAESTRO_PE"))                                        return TEXT("STAGE_NACIONAL_LIMA");
    if (FighterID == TEXT("TREN_EC"))                                           return TEXT("STAGE_ATAHUALPA");
    if (FighterID == TEXT("HURACAN_VE"))                                        return TEXT("STAGE_AVILA");
    if (FighterID == TEXT("DIABLO_BO")   || FighterID == TEXT("GENERAL_FR"))   return TEXT("STAGE_HERNANDO_SILES");

    return TEXT("STAGE_MARACANA");
}
