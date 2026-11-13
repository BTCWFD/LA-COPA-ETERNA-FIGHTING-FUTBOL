// EOSGGPONetworkBridge.cpp - SouthAmericaFightersCore
#include "EOSGGPONetworkBridge.h"
#include "Containers/StringConv.h"

bool UEOSGGPONetworkBridge::InitializeP2PSession(
    void* InEOSPlatformHandle,
    const FString& LocalAccountIdStr,
    const FString& OpponentAccountIdStr,
    const FString& SocketName)
{
    CachedSocketName = SocketName;
    LastRemoteFrameAcked = 0;
    HighestLocalFrameSent = 0;
    LocalFrameAdvantage = 0.0f;
    SimulatedLoopbackQueue.Reset();

    for (int32 i = 0; i < ChecksumHistorySize; ++i)
    {
        LocalFrameNumbers[i] = UINT32_MAX;
        LocalFrameChecksums[i] = 0;
    }

#if WITH_EOS_SDK
    if (!InEOSPlatformHandle)
    {
        return false;
    }

    EOS_HPlatform PlatformHandle = static_cast<EOS_HPlatform>(InEOSPlatformHandle);
    P2PHandle = EOS_Platform_GetP2PInterface(PlatformHandle);
    if (!P2PHandle)
    {
        return false;
    }

    LocalUserId = EOS_ProductUserId_FromString(TCHAR_TO_UTF8(*LocalAccountIdStr));
    OpponentUserId = EOS_ProductUserId_FromString(TCHAR_TO_UTF8(*OpponentAccountIdStr));

    FMemory::Memzero(&CombatSocketId, sizeof(CombatSocketId));
    CombatSocketId.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;
    FCStringAnsi::Strncpy(CombatSocketId.SocketName, TCHAR_TO_UTF8(*SocketName), EOS_P2P_SOCKETID_SOCKETNAME_SIZE - 1);

    // Forzar uso de Relay AWS (Sao Paulo sa-east-1 / Santiago) para proteger IP del jugador y evitar ataques DDoS
    EOS_P2P_SetRelayControlOptions RelayOpts = {};
    RelayOpts.ApiVersion = EOS_P2P_SETRELAYCONTROL_API_LATEST;
    RelayOpts.RelayControl = EOS_ERelayControl::EOS_RC_ForceRelays;
    EOS_P2P_SetRelayControl(P2PHandle, &RelayOpts);

    // Pre-aceptar la conexión entrante del oponente para eliminar el retardo del handshake inicial
    EOS_P2P_AcceptConnectionOptions AcceptOpts = {};
    AcceptOpts.ApiVersion = EOS_P2P_ACCEPTCONNECTION_API_LATEST;
    AcceptOpts.LocalUserId = LocalUserId;
    AcceptOpts.RemoteUserId = OpponentUserId;
    AcceptOpts.SocketId = &CombatSocketId;
    EOS_P2P_AcceptConnection(P2PHandle, &AcceptOpts);

    bIsSessionInitialized = (EOS_ProductUserId_IsValid(LocalUserId) == EOS_TRUE) &&
                            (EOS_ProductUserId_IsValid(OpponentUserId) == EOS_TRUE);
    return bIsSessionInitialized;
#else
    // Fallback limpio cuando se compila en modo Editor/Headless sin el binario de EOS SDK vinculado
    (void)InEOSPlatformHandle;
    bIsSessionInitialized = !LocalAccountIdStr.IsEmpty() && !OpponentAccountIdStr.IsEmpty();
    return bIsSessionInitialized;
#endif
}

void UEOSGGPONetworkBridge::ShutdownP2PSession()
{
#if WITH_EOS_SDK
    if (P2PHandle && LocalUserId && OpponentUserId)
    {
        EOS_P2P_CloseConnectionOptions CloseOpts = {};
        CloseOpts.ApiVersion = EOS_P2P_CLOSECONNECTION_API_LATEST;
        CloseOpts.LocalUserId = LocalUserId;
        CloseOpts.RemoteUserId = OpponentUserId;
        CloseOpts.SocketId = &CombatSocketId;
        EOS_P2P_CloseConnection(P2PHandle, &CloseOpts);
    }
    P2PHandle = nullptr;
    LocalUserId = nullptr;
    OpponentUserId = nullptr;
#endif
    bIsSessionInitialized = false;
    SimulatedLoopbackQueue.Reset();
}

void UEOSGGPONetworkBridge::RecordLocalFrameChecksum(uint32 Frame, uint16 Checksum16)
{
    const int32 Slot = static_cast<int32>(Frame % ChecksumHistorySize);
    LocalFrameNumbers[Slot] = Frame;
    LocalFrameChecksums[Slot] = Checksum16;
}

void UEOSGGPONetworkBridge::SendFrameInputToOpponent(uint32 CurrentFrame, uint16 InputBitmask, uint16 StateChecksum16)
{
    if (!bIsSessionInitialized)
    {
        return;
    }

    RecordLocalFrameChecksum(CurrentFrame, StateChecksum16);
    HighestLocalFrameSent = FMath::Max(HighestLocalFrameSent, CurrentFrame);

    FGGPOUDPNetworkPacket Packet;
    Packet.SequenceFrame = CurrentFrame;
    Packet.LastAckedFrame = LastRemoteFrameAcked;
    Packet.LocalInputBitmask = InputBitmask;
    Packet.ChecksumFletcher16 = StateChecksum16;

#if WITH_EOS_SDK
    if (P2PHandle)
    {
        EOS_P2P_SendPacketOptions SendOpts = {};
        SendOpts.ApiVersion = EOS_P2P_SENDPACKET_API_LATEST;
        SendOpts.LocalUserId = LocalUserId;
        SendOpts.RemoteUserId = OpponentUserId;
        SendOpts.SocketId = &CombatSocketId;
        SendOpts.Channel = CombatP2PChannel;
        SendOpts.DataLengthBytes = sizeof(FGGPOUDPNetworkPacket);
        SendOpts.Data = &Packet;
        SendOpts.bAllowDelayedDelivery = EOS_FALSE; // Descartar paquetes obsoletos inmediatamente en combate
        SendOpts.Reliability = EOS_EPacketReliability::EOS_PR_UnreliableUnordered; // Puro UDP para GGPO
        SendOpts.bDisableAutoAcceptConnection = EOS_FALSE;

        EOS_P2P_SendPacket(P2PHandle, &SendOpts);
    }
#endif
}

void UEOSGGPONetworkBridge::PollIncomingPackets()
{
    if (!bIsSessionInitialized)
    {
        return;
    }

#if WITH_EOS_SDK
    if (P2PHandle)
    {
        EOS_P2P_ReceivePacketOptions RecvOpts = {};
        RecvOpts.ApiVersion = EOS_P2P_RECEIVEPACKET_API_LATEST;
        RecvOpts.LocalUserId = LocalUserId;
        RecvOpts.MaxDataSizeBytes = sizeof(FGGPOUDPNetworkPacket);
        const uint8 TargetChannel = CombatP2PChannel;
        RecvOpts.RequestedChannel = &TargetChannel;

        EOS_ProductUserId SenderId = nullptr;
        EOS_P2P_SocketId RecvSocket = {};
        uint8 Channel = 0;
        FGGPOUDPNetworkPacket IncomingPacket;
        uint32 BytesRead = 0;

        while (EOS_P2P_ReceivePacket(
                   P2PHandle,
                   &RecvOpts,
                   &SenderId,
                   &RecvSocket,
                   &Channel,
                   &IncomingPacket,
                   &BytesRead) == EOS_EResult::EOS_Success)
        {
            if (BytesRead == sizeof(FGGPOUDPNetworkPacket))
            {
                ProcessIncomingPacket(IncomingPacket);
            }
        }
    }
#endif

    // Drenar paquetes inyectados en simulaciones o tests locales
    for (const FGGPOUDPNetworkPacket& SimPacket : SimulatedLoopbackQueue)
    {
        ProcessIncomingPacket(SimPacket);
    }
    SimulatedLoopbackQueue.Reset();
}

void UEOSGGPONetworkBridge::InjectSimulatedPacketForTesting(const FGGPOUDPNetworkPacket& SimulatedPacket)
{
    SimulatedLoopbackQueue.Add(SimulatedPacket);
}

void UEOSGGPONetworkBridge::ProcessIncomingPacket(const FGGPOUDPNetworkPacket& IncomingPacket)
{
    if (IncomingPacket.SequenceFrame > LastRemoteFrameAcked)
    {
        LastRemoteFrameAcked = IncomingPacket.SequenceFrame;
    }

    // Cálculo de ventaja de reloj (Time Sync / Rift Synchronization de GGPO)
    // Compara el frame remoto recibido contra el frame que el rival nos confirmó haber recibido
    const float RawFrameDelta = static_cast<float>( static_cast<int64>(IncomingPacket.LastAckedFrame) - static_cast<int64>(IncomingPacket.SequenceFrame) );
    LocalFrameAdvantage = FMath::Lerp(LocalFrameAdvantage, RawFrameDelta * 0.5f, 0.2f);

    // Verificación inmediata de integridad de estado (Detección de Desync en vivo)
    const int32 Slot = static_cast<int32>(IncomingPacket.SequenceFrame % ChecksumHistorySize);
    if (LocalFrameNumbers[Slot] == IncomingPacket.SequenceFrame)
    {
        const uint16 ExpectedLocalChecksum = LocalFrameChecksums[Slot];
        if (ExpectedLocalChecksum != IncomingPacket.ChecksumFletcher16)
        {
            OnNetworkDesyncDetected.ExecuteIfBound(
                IncomingPacket.SequenceFrame,
                ExpectedLocalChecksum,
                IncomingPacket.ChecksumFletcher16
            );
        }
    }

    OnRemoteFrameInputReceived.ExecuteIfBound(
        IncomingPacket.SequenceFrame,
        IncomingPacket.LocalInputBitmask,
        IncomingPacket.ChecksumFletcher16
    );
}

uint16 UEOSGGPONetworkBridge::ComputeFletcher16(const uint8* Data, SIZE_T Length)
{
    uint16 Sum1 = 0xFF;
    uint16 Sum2 = 0xFF;

    while (Length > 0)
    {
        SIZE_T Tlen = Length > 20 ? 20 : Length;
        Length -= Tlen;
        do
        {
            Sum1 += *Data++;
            Sum2 += Sum1;
        } while (--Tlen);

        Sum1 = (Sum1 & 0xFF) + (Sum1 >> 8);
        Sum2 = (Sum2 & 0xFF) + (Sum2 >> 8);
    }

    Sum1 = (Sum1 & 0xFF) + (Sum1 >> 8);
    Sum2 = (Sum2 & 0xFF) + (Sum2 >> 8);
    return static_cast<uint16>((Sum2 << 8) | Sum1);
}
