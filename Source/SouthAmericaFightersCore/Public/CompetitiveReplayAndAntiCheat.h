// CompetitiveReplayAndAntiCheat.h - SouthAmericaFightersCore
// Serializador de Repeticiones Deterministas (.safreplay), Auditoría Anti-Cheat Heurística y Glicko-2 MMR
#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "CompetitiveReplayAndAntiCheat.generated.h"

#pragma pack(push, 1)
struct FDeterministicReplayHeader
{
    uint32 MagicNumber = 0x53414652; // "SAFR" (South America Fighters Replay)
    uint16 BalancePatchVersion = 104; // Ej. Parche v1.04
    FGuid MatchUUID;
    uint64 DeterministicRandomSeed = 0;
    uint8 Player1CharacterID = 0;
    uint8 Player2CharacterID = 0;
    uint8 StageID = 0;
    uint32 TotalSimulatedFrames = 0;
    uint32 FinalStateChecksum = 0;   // Fletcher-32 al terminar el KO
};

// Compresión RLE (Run-Length Encoding) de la cinta de inputs
struct FCompressedInputRun
{
    uint16 P1InputBitmask = 0;
    uint16 P2InputBitmask = 0;
    uint8 RepeatFrames = 1; // 1 a 255 frames idénticos consecutivos
};
#pragma pack(pop)

static_assert(sizeof(FCompressedInputRun) == 5, "FCompressedInputRun debe medir exactamente 5 bytes.");

USTRUCT(BlueprintType)
struct FAntiCheatAuditReport
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "AntiCheat")
    bool bSuspectedMacroScript = false;       // Desviación estándar = 0.0ms en secuencias complejas

    UPROPERTY(BlueprintReadOnly, Category = "AntiCheat")
    bool bSuspectedAutoParryBot = false;      // Reacción consistente en Frame 1 de impacto sin buffering previo

    UPROPERTY(BlueprintReadOnly, Category = "AntiCheat")
    bool bSuspectedLagSwitch = false;         // Picos de pérdida/jitter exclusivos cuando el jugador recibe un combo

    UPROPERTY(BlueprintReadOnly, Category = "AntiCheat")
    float InputTimingVariance = 1.0f;

    UPROPERTY(BlueprintReadOnly, Category = "AntiCheat")
    float LagDuringEnemyComboRatio = 0.0f;
};

UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UCompetitiveReplaySerializer : public UObject
{
    GENERATED_BODY()

public:
    static TArray<uint8> SerializeAndCompressMatchReplay(
        const FDeterministicReplayHeader& Header,
        const TArray<uint16>& RawP1Inputs,
        const TArray<uint16>& RawP2Inputs
    );

    static bool DecompressMatchReplay(
        const TArray<uint8>& CompressedPayload,
        FDeterministicReplayHeader& OutHeader,
        TArray<uint16>& OutRawP1Inputs,
        TArray<uint16>& OutRawP2Inputs
    );

    static FAntiCheatAuditReport AuditPlayerInputStream(
        const TArray<uint16>& PlayerInputs,
        const TArray<uint8>& NetworkRollbackSpikesPerFrame,
        const TArray<bool>& bWasPlayerInHitstunPerFrame,
        const TArray<bool>& bEnemyAttackActiveFrame1PerFrame
    );

    // Cálculo oficial de Master Rating (Glicko-2) para Ligas CONMEBOL
    static void CalculateGlicko2RatingUpdate(
        double& InOutPlayerRating,
        double& InOutRatingDeviation,
        double& InOutVolatility,
        double OpponentRating,
        double OpponentDeviation,
        double MatchScore // 1.0 = Victoria, 0.5 = Empate, 0.0 = Derrota
    );
};
