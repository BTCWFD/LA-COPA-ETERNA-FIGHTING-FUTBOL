// EOSGGPONetworkBridge.h - SouthAmericaFightersCore
// Subsistema de Red Determinista P2P: Epic Online Services (EOS) + GGPO Rollback Netcode
#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"

#if WITH_EOS_SDK
#include "eos_sdk.h"
#include "eos_p2p.h"
#endif

#include "EOSGGPONetworkBridge.generated.h"

#pragma pack(push, 1)
struct FGGPOUDPNetworkPacket
{
    uint32 SequenceFrame = 0;       // Frame del motor local
    uint32 LastAckedFrame = 0;      // Último frame confirmado del rival
    uint16 LocalInputBitmask = 0;   // Input actual comprimido (9 bits activos)
    uint16 ChecksumFletcher16 = 0;  // Hash rápido para detección temprana de Desync
};
#pragma pack(pop)

static_assert(sizeof(FGGPOUDPNetworkPacket) == 12, "FGGPOUDPNetworkPacket debe tener exactamente 12 bytes sin padding.");

DECLARE_DELEGATE_ThreeParams(FOnRemoteFrameInputReceived, uint32 /*Frame*/, uint16 /*InputBitmask*/, uint16 /*RemoteChecksum*/);
DECLARE_DELEGATE_ThreeParams(FOnNetworkDesyncDetected, uint32 /*Frame*/, uint16 /*LocalChecksum*/, uint16 /*RemoteChecksum*/);

UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UEOSGGPONetworkBridge : public UObject
{
    GENERATED_BODY()

public:
    static constexpr int32 MaxRollbackFrames = 8;
    static constexpr uint8 CombatP2PChannel = 0;

    bool InitializeP2PSession(
        void* InEOSPlatformHandle,
        const FString& LocalAccountIdStr,
        const FString& OpponentAccountIdStr,
        const FString& SocketName = TEXT("SAF_GGPO_COMBAT_V1")
    );

    void ShutdownP2PSession();

    void SendFrameInputToOpponent(uint32 CurrentFrame, uint16 InputBitmask, uint16 StateChecksum16);
    void PollIncomingPackets();

    // Retorna cuántos frames de ventaja lleva el cliente local frente al remoto (Time Sync GGPO)
    float GetTimeSyncFrameAdvantage() const { return LocalFrameAdvantage; }

    // Determina si el motor debe pausar 1 tick (~16.6ms) para re-sincronizar los relojes de simulación
    bool ShouldStallSimulationForRiftSync() const { return LocalFrameAdvantage >= 0.75f; }

    void RecordLocalFrameChecksum(uint32 Frame, uint16 Checksum16);
    uint32 GetLastConfirmedRemoteFrame() const { return LastRemoteFrameAcked; }
    bool IsSessionActive() const { return bIsSessionInitialized; }

    // Inyección directa para pruebas unitarias o simulación Headless sin hardware de red
    void InjectSimulatedPacketForTesting(const FGGPOUDPNetworkPacket& SimulatedPacket);

    FOnRemoteFrameInputReceived OnRemoteFrameInputReceived;
    FOnNetworkDesyncDetected OnNetworkDesyncDetected;

    static uint16 ComputeFletcher16(const uint8* Data, SIZE_T Length);

private:
#if WITH_EOS_SDK
    EOS_HP2P P2PHandle = nullptr;
    EOS_ProductUserId LocalUserId = nullptr;
    EOS_ProductUserId OpponentUserId = nullptr;
    EOS_P2P_SocketId CombatSocketId{};
#endif

    FString CachedSocketName;
    bool bIsSessionInitialized = false;
    uint32 LastRemoteFrameAcked = 0;
    uint32 HighestLocalFrameSent = 0;
    float LocalFrameAdvantage = 0.0f;

    // Historial circular de Checksums locales (últimos 256 frames) para auditoría cruzada de Desync
    static constexpr int32 ChecksumHistorySize = 256;
    TStaticArray<uint32, ChecksumHistorySize> LocalFrameNumbers;
    TStaticArray<uint16, ChecksumHistorySize> LocalFrameChecksums;

    // Cola loopback para modo sin EOS_SDK o testeo determinista local
    TArray<FGGPOUDPNetworkPacket> SimulatedLoopbackQueue;

    void ProcessIncomingPacket(const FGGPOUDPNetworkPacket& Packet);
};
