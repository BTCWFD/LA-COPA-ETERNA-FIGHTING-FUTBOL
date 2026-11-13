// FixedPointTypes.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include <compare>
#include "FixedPointTypes.generated.h"

/**
 * Representa un número real determinista en formato Q32.32 (64-bit entero con signo).
 * Garantiza 0 desincronización matemática entre Windows (MSVC), PS5 (Clang) y Xbox Series X/S.
 */
USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFixedPoint
{
    GENERATED_BODY()

    static constexpr int32 FractionalBits = 32;
    static constexpr int64 One = 1LL << FractionalBits;
    static constexpr int64 Half = 1LL << (FractionalBits - 1);

    UPROPERTY(SaveGame)
    int64 RawValue = 0;

    constexpr FFixedPoint() = default;
    explicit constexpr FFixedPoint(int64 InRawValue, bool bIsRaw) : RawValue(InRawValue) {}
    constexpr FFixedPoint(int32 IntVal) : RawValue(static_cast<int64>(IntVal) << FractionalBits) {}

    static constexpr FFixedPoint FromRaw(int64 InRaw)
    {
        return FFixedPoint(InRaw, true);
    }

    static constexpr FFixedPoint FromMillimeters(int64 Millimeters)
    {
        return FFixedPoint((Millimeters << FractionalBits) / 1000LL, true);
    }

    FORCEINLINE float ToFloatVisualOnly() const
    {
        return static_cast<float>(RawValue) / static_cast<float>(One);
    }

    FORCEINLINE constexpr int32 ToIntTruncated() const
    {
        return static_cast<int32>(RawValue >> FractionalBits);
    }

    constexpr FFixedPoint operator+(const FFixedPoint& Other) const { return FromRaw(RawValue + Other.RawValue); }
    constexpr FFixedPoint operator-(const FFixedPoint& Other) const { return FromRaw(RawValue - Other.RawValue); }
    constexpr FFixedPoint operator-() const { return FromRaw(-RawValue); }
    constexpr FFixedPoint& operator+=(const FFixedPoint& Other) { RawValue += Other.RawValue; return *this; }
    constexpr FFixedPoint& operator-=(const FFixedPoint& Other) { RawValue -= Other.RawValue; return *this; }

    constexpr FFixedPoint operator*(const FFixedPoint& Other) const
    {
#if defined(__SIZEOF_INT128__)
        __int128 Product = static_cast<__int128>(RawValue) * static_cast<__int128>(Other.RawValue);
        return FromRaw(static_cast<int64>(Product >> FractionalBits));
#else
        const int64 A_Hi = RawValue >> 32;
        const uint64 A_Lo = static_cast<uint64>(RawValue & 0xFFFFFFFFLL);
        const int64 B_Hi = Other.RawValue >> 32;
        const uint64 B_Lo = static_cast<uint64>(Other.RawValue & 0xFFFFFFFFLL);

        const uint64 LoLo = (A_Lo * B_Lo) >> 32;
        const int64 HiLo = A_Hi * static_cast<int64>(B_Lo);
        const int64 LoHi = static_cast<int64>(A_Lo) * B_Hi;
        const int64 HiHi = (A_Hi * B_Hi) << 32;

        return FromRaw(static_cast<int64>(LoLo) + HiLo + LoHi + HiHi);
#endif
    }

    constexpr FFixedPoint operator/(const FFixedPoint& Other) const
    {
        if (Other.RawValue == 0) return FromRaw(0);
#if defined(__SIZEOF_INT128__)
        __int128 Dividend = static_cast<__int128>(RawValue) << FractionalBits;
        return FromRaw(static_cast<int64>(Dividend / Other.RawValue));
#else
        return FromRaw((RawValue << 16) / (Other.RawValue >> 16));
#endif
    }

    constexpr auto operator<=>(const FFixedPoint& Other) const = default;

    static constexpr FFixedPoint Abs(FFixedPoint Val)
    {
        return Val.RawValue < 0 ? FromRaw(-Val.RawValue) : Val;
    }

    static constexpr FFixedPoint Clamp(FFixedPoint Val, FFixedPoint MinVal, FFixedPoint MaxVal)
    {
        return (Val < MinVal) ? MinVal : ((Val > MaxVal) ? MaxVal : Val);
    }
};

USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFixedVector2D
{
    GENERATED_BODY()

    UPROPERTY(SaveGame)
    FFixedPoint X;

    UPROPERTY(SaveGame)
    FFixedPoint Y;

    constexpr FFixedVector2D() = default;
    constexpr FFixedVector2D(FFixedPoint InX, FFixedPoint InY) : X(InX), Y(InY) {}
};

USTRUCT(BlueprintType)
struct SOUTHAMERICAFIGHTERSCORE_API FFixedAABB
{
    GENERATED_BODY()

    UPROPERTY(SaveGame)
    FFixedPoint MinX;

    UPROPERTY(SaveGame)
    FFixedPoint MaxX;

    UPROPERTY(SaveGame)
    FFixedPoint MinY;

    UPROPERTY(SaveGame)
    FFixedPoint MaxY;

    constexpr bool Intersects(const FFixedAABB& Other) const
    {
        return (MinX <= Other.MaxX && MaxX >= Other.MinX) &&
               (MinY <= Other.MaxY && MaxY >= Other.MinY);
    }
};
