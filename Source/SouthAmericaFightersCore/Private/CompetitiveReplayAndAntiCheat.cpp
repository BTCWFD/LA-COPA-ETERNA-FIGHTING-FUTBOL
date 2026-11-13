// CompetitiveReplayAndAntiCheat.cpp - SouthAmericaFightersCore
#include "CompetitiveReplayAndAntiCheat.h"
#include "FightingInputParser.h"
#include "Misc/Compression.h"

TArray<uint8> UCompetitiveReplaySerializer::SerializeAndCompressMatchReplay(
    const FDeterministicReplayHeader& Header,
    const TArray<uint16>& RawP1Inputs,
    const TArray<uint16>& RawP2Inputs)
{
    TArray<FCompressedInputRun> RLEStream;
    const int32 TotalFrames = FMath::Min(RawP1Inputs.Num(), RawP2Inputs.Num());
    RLEStream.Reserve(TotalFrames / 4 + 1);

    for (int32 i = 0; i < TotalFrames; ++i)
    {
        if (RLEStream.Num() > 0 &&
            RLEStream.Last().P1InputBitmask == RawP1Inputs[i] &&
            RLEStream.Last().P2InputBitmask == RawP2Inputs[i] &&
            RLEStream.Last().RepeatFrames < 255)
        {
            RLEStream.Last().RepeatFrames++;
        }
        else
        {
            FCompressedInputRun NewRun;
            NewRun.P1InputBitmask = RawP1Inputs[i];
            NewRun.P2InputBitmask = RawP2Inputs[i];
            NewRun.RepeatFrames = 1;
            RLEStream.Add(NewRun);
        }
    }

    // Construir bloque binario sin comprimir: Header + Arreglo RLE
    const int32 UncompressedSize = sizeof(FDeterministicReplayHeader) + (RLEStream.Num() * sizeof(FCompressedInputRun));
    TArray<uint8> UncompressedBuffer;
    UncompressedBuffer.SetNumUninitialized(UncompressedSize);

    FDeterministicReplayHeader AdjustedHeader = Header;
    AdjustedHeader.TotalSimulatedFrames = static_cast<uint32>(TotalFrames);

    FMemory::Memcpy(UncompressedBuffer.GetData(), &AdjustedHeader, sizeof(FDeterministicReplayHeader));
    if (RLEStream.Num() > 0)
    {
        FMemory::Memcpy(
            UncompressedBuffer.GetData() + sizeof(FDeterministicReplayHeader),
            RLEStream.GetData(),
            RLEStream.Num() * sizeof(FCompressedInputRun)
        );
    }

    // Compresión Zlib rápida (Típico: 3 minutos de pelea = ~4.2 KB finales)
    int32 CompressedSize = FCompression::CompressMemoryBound(NAME_Zlib, UncompressedSize);
    TArray<uint8> CompressedPayload;
    // Prefijamos 4 bytes con el tamaño descomprimido exacto para reconstrucción segura
    CompressedPayload.SetNumUninitialized(sizeof(int32) + CompressedSize);
    FMemory::Memcpy(CompressedPayload.GetData(), &UncompressedSize, sizeof(int32));

    if (FCompression::CompressMemory(
            NAME_Zlib,
            CompressedPayload.GetData() + sizeof(int32),
            CompressedSize,
            UncompressedBuffer.GetData(),
            UncompressedSize))
    {
        CompressedPayload.SetNum(sizeof(int32) + CompressedSize, EAllowShrinking::No);
    }
    else
    {
        // Fallback sin compresión Zlib si el compresor de plataforma no está disponible
        const int32 NegativeMarker = -UncompressedSize;
        CompressedPayload.SetNumUninitialized(sizeof(int32) + UncompressedSize);
        FMemory::Memcpy(CompressedPayload.GetData(), &NegativeMarker, sizeof(int32));
        FMemory::Memcpy(CompressedPayload.GetData() + sizeof(int32), UncompressedBuffer.GetData(), UncompressedSize);
    }

    return CompressedPayload;
}

bool UCompetitiveReplaySerializer::DecompressMatchReplay(
    const TArray<uint8>& CompressedPayload,
    FDeterministicReplayHeader& OutHeader,
    TArray<uint16>& OutRawP1Inputs,
    TArray<uint16>& OutRawP2Inputs)
{
    if (CompressedPayload.Num() < static_cast<int32>(sizeof(int32)))
    {
        return false;
    }

    int32 StoredUncompressedSize = 0;
    FMemory::Memcpy(&StoredUncompressedSize, CompressedPayload.GetData(), sizeof(int32));

    TArray<uint8> UncompressedBuffer;
    if (StoredUncompressedSize > 0)
    {
        UncompressedBuffer.SetNumUninitialized(StoredUncompressedSize);
        if (!FCompression::UncompressMemory(
                NAME_Zlib,
                UncompressedBuffer.GetData(),
                StoredUncompressedSize,
                CompressedPayload.GetData() + sizeof(int32),
                CompressedPayload.Num() - sizeof(int32)))
        {
            return false;
        }
    }
    else if (StoredUncompressedSize < 0)
    {
        const int32 RawSize = -StoredUncompressedSize;
        if (CompressedPayload.Num() != static_cast<int32>(sizeof(int32)) + RawSize)
        {
            return false;
        }
        UncompressedBuffer.SetNumUninitialized(RawSize);
        FMemory::Memcpy(UncompressedBuffer.GetData(), CompressedPayload.GetData() + sizeof(int32), RawSize);
    }
    else
    {
        return false;
    }

    if (UncompressedBuffer.Num() < static_cast<int32>(sizeof(FDeterministicReplayHeader)))
    {
        return false;
    }

    FMemory::Memcpy(&OutHeader, UncompressedBuffer.GetData(), sizeof(FDeterministicReplayHeader));
    if (OutHeader.MagicNumber != 0x53414652)
    {
        return false;
    }

    const int32 RLEBytes = UncompressedBuffer.Num() - sizeof(FDeterministicReplayHeader);
    if (RLEBytes % sizeof(FCompressedInputRun) != 0)
    {
        return false;
    }

    const int32 NumRuns = RLEBytes / sizeof(FCompressedInputRun);
    const FCompressedInputRun* RunsPtr = reinterpret_cast<const FCompressedInputRun*>(
        UncompressedBuffer.GetData() + sizeof(FDeterministicReplayHeader)
    );

    OutRawP1Inputs.Reset();
    OutRawP2Inputs.Reset();
    OutRawP1Inputs.Reserve(OutHeader.TotalSimulatedFrames);
    OutRawP2Inputs.Reserve(OutHeader.TotalSimulatedFrames);

    for (int32 r = 0; r < NumRuns; ++r)
    {
        const FCompressedInputRun& Run = RunsPtr[r];
        for (uint8 step = 0; step < Run.RepeatFrames; ++step)
        {
            OutRawP1Inputs.Add(Run.P1InputBitmask);
            OutRawP2Inputs.Add(Run.P2InputBitmask);
        }
    }

    return true;
}

FAntiCheatAuditReport UCompetitiveReplaySerializer::AuditPlayerInputStream(
    const TArray<uint16>& PlayerInputs,
    const TArray<uint8>& NetworkRollbackSpikesPerFrame,
    const TArray<bool>& bWasPlayerInHitstunPerFrame,
    const TArray<bool>& bEnemyAttackActiveFrame1PerFrame)
{
    FAntiCheatAuditReport Report;

    const int32 TotalFrames = PlayerInputs.Num();
    if (TotalFrames < 120)
    {
        return Report;
    }

    // 1. Detección de Lag Switching Asimétrico
    // Comparamos los picos de rollback ( pérdida de paquetes > 4 frames ) durante combos enemigos vs neutral
    int32 TotalLagSpikes = 0;
    int32 LagSpikesWhileBeingComboed = 0;
    const int32 SafeNetFrames = FMath::Min3(TotalFrames, NetworkRollbackSpikesPerFrame.Num(), bWasPlayerInHitstunPerFrame.Num());

    for (int32 i = 0; i < SafeNetFrames; ++i)
    {
        if (NetworkRollbackSpikesPerFrame[i] >= 5)
        {
            TotalLagSpikes++;
            if (bWasPlayerInHitstunPerFrame[i])
            {
                LagSpikesWhileBeingComboed++;
            }
        }
    }

    if (TotalLagSpikes >= 8)
    {
        Report.LagDuringEnemyComboRatio = static_cast<float>(LagSpikesWhileBeingComboed) / static_cast<float>(TotalLagSpikes);
        // Si >= 80% de las caídas severas de red ocurren exactamente mientras el jugador está recibiendo un combo:
        if (Report.LagDuringEnemyComboRatio >= 0.80f)
        {
            Report.bSuspectedLagSwitch = true;
        }
    }

    // 2. Detección de Auto-Parry / Gambeta Bot (Lectura de memoria de Frame 1)
    int32 EnemyAttacksFaced = 0;
    int32 FramePerfectParries = 0;
    const int32 SafeParryFrames = FMath::Min(TotalFrames, bEnemyAttackActiveFrame1PerFrame.Num());

    for (int32 i = 3; i < SafeParryFrames; ++i)
    {
        if (bEnemyAttackActiveFrame1PerFrame[i])
        {
            EnemyAttacksFaced++;
            const bool bParryPressedNow = (PlayerInputs[i] & ECombatInputBits::GB) != 0;
            const bool bParryBufferedBefore = (PlayerInputs[i - 1] & ECombatInputBits::GB) != 0 ||
                                              (PlayerInputs[i - 2] & ECombatInputBits::GB) != 0 ||
                                              (PlayerInputs[i - 3] & ECombatInputBits::GB) != 0;
            if (bParryPressedNow && !bParryBufferedBefore)
            {
                FramePerfectParries++;
            }
        }
    }

    if (EnemyAttacksFaced >= 10 && (static_cast<float>(FramePerfectParries) / EnemyAttacksFaced) > 0.65f)
    {
        Report.bSuspectedAutoParryBot = true;
    }

    // 3. Detección de Macros de Comandos Complejos (Varianza de duración por dirección = 0.0)
    // Medimos la duración en frames de cada transición direccional en secuencias rápidas (QCF/DP/HCF)
    TArray<int32> DirectionalHoldDurations;
    uint16 CurrentDirMask = PlayerInputs[0] & 0x000F;
    int32 CurrentHoldCount = 1;

    for (int32 i = 1; i < TotalFrames; ++i)
    {
        const uint16 DirMask = PlayerInputs[i] & 0x000F;
        if (DirMask == CurrentDirMask)
        {
            CurrentHoldCount++;
        }
        else
        {
            // Transiciones rápidas de comandos especiales (entre 1 y 6 frames por diagonal/cardinal)
            if (CurrentDirMask != 0 && CurrentHoldCount >= 1 && CurrentHoldCount <= 6)
            {
                DirectionalHoldDurations.Add(CurrentHoldCount);
            }
            CurrentDirMask = DirMask;
            CurrentHoldCount = 1;
        }
    }

    if (DirectionalHoldDurations.Num() >= 16)
    {
        double Mean = 0.0;
        for (int32 Hold : DirectionalHoldDurations)
        {
            Mean += static_cast<double>(Hold);
        }
        Mean /= static_cast<double>(DirectionalHoldDurations.Num());

        double VarianceAccum = 0.0;
        for (int32 Hold : DirectionalHoldDurations)
        {
            const double Diff = static_cast<double>(Hold) - Mean;
            VarianceAccum += Diff * Diff;
        }
        Report.InputTimingVariance = static_cast<float>(VarianceAccum / static_cast<double>(DirectionalHoldDurations.Num()));

        if (Report.InputTimingVariance < 0.001f)
        {
            Report.bSuspectedMacroScript = true;
        }
    }

    return Report;
}

void UCompetitiveReplaySerializer::CalculateGlicko2RatingUpdate(
    double& InOutPlayerRating,
    double& InOutRatingDeviation,
    double& InOutVolatility,
    double OpponentRating,
    double OpponentDeviation,
    double MatchScore)
{
    constexpr double GlickoScale = 173.7178;
    constexpr double Tau = 0.5; // Constante del sistema para restringir volatilidad extrema

    const double Mu = (InOutPlayerRating - 1500.0) / GlickoScale;
    const double Phi = InOutRatingDeviation / GlickoScale;
    const double MuJ = (OpponentRating - 1500.0) / GlickoScale;
    const double PhiJ = OpponentDeviation / GlickoScale;

    const double gPhiJ = 1.0 / FMath::Sqrt(1.0 + 3.0 * (PhiJ * PhiJ) / (PI * PI));
    const double EVal = 1.0 / (1.0 + FMath::Exp(-gPhiJ * (Mu - MuJ)));

    // Varianza estimada v
    const double V = 1.0 / (gPhiJ * gPhiJ * EVal * (1.0 - EVal));

    // Actualización de volatilidad simplificada convergente (Illinois Algorithm step)
    const double Delta = V * gPhiJ * (MatchScore - EVal);
    const double NewSigma = FMath::Clamp(
        InOutVolatility * (1.0 + (Delta * Delta - Phi * Phi - V) * 0.005 * Tau),
        0.03,
        0.12
    );

    const double PhiStar = FMath::Sqrt(Phi * Phi + NewSigma * NewSigma);
    const double NewPhi = 1.0 / FMath::Sqrt((1.0 / (PhiStar * PhiStar)) + (1.0 / V));
    const double NewMu = Mu + (NewPhi * NewPhi) * gPhiJ * (MatchScore - EVal);

    InOutPlayerRating = 1500.0 + GlickoScale * NewMu;
    InOutRatingDeviation = FMath::Clamp(GlickoScale * NewPhi, 30.0, 350.0);
    InOutVolatility = NewSigma;
}
