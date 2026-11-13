// BTTask_ExecuteVARRewind.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BossAIController.h"
#include "BTTask_ExecuteVARRewind.generated.h"

/**
 * Nodo de Behavior Tree para el Jefe Final "V.A.R. - ZERO".
 * Invoca la mecánica determinista V.A.R. Rewind rebobinando 90 frames (1.5s a 60 Hz) del Ring Buffer de combate.
 */
UCLASS(BlueprintType)
class SOUTHAMERICAFIGHTERSCORE_API UBTTask_ExecuteVARRewind : public UBTTaskNode
{
    GENERATED_BODY()

public:
    UBTTask_ExecuteVARRewind()
    {
        NodeName = TEXT("Execute V.A.R. Rewind (90 Frames)");
        bNotifyTick = false;
    }

    /** Cantidad de frames a rebobinar en el Ring Buffer del Jefe (por defecto 90 frames = 1.5s a 60 Hz). */
    UPROPERTY(EditAnywhere, Category = "VAR|Rewind", meta = (ClampMin = "1", ClampMax = "119"))
    int32 FramesToRewind = 90;

    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory) override
    {
        ABossAIController* BossAI = Cast<ABossAIController>(OwnerComp.GetAIOwner());
        if (!BossAI)
        {
            return EBTNodeResult::Failed;
        }

        const bool bRewindSucceeded = BossAI->TriggerVARRewind(FramesToRewind);
        return bRewindSucceeded ? EBTNodeResult::Succeeded : EBTNodeResult::Failed;
    }

    virtual FString GetStaticDescription() const override
    {
        return FString::Printf(TEXT("V.A.R. Rewind: Rebobina %d frames (%.2fs a 60 Hz)"),
            FramesToRewind, static_cast<float>(FramesToRewind) / 60.0f);
    }
};
