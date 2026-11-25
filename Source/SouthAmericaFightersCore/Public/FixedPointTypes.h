// FixedPointTypes.h - SouthAmericaFightersCore
#pragma once

#include "CoreMinimal.h"
#include <compare>
#include <type_traits>
#if defined(_MSC_VER) && defined(_M_X64)
#include <intrin.h>
#endif
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
        const bool bNegative = Millimeters < 0;
        const uint64 AbsMm = bNegative
            ? (0ULL - static_cast<uint64>(Millimeters))
            : static_cast<uint64>(Millimeters);
        const uint64 RawMag = (AbsMm << FractionalBits) / 1000ULL;
        const int64 SignedRaw = bNegative
            ? static_cast<int64>(0ULL - RawMag)
            : static_cast<int64>(RawMag);
        return FFixedPoint(SignedRaw, true);
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
    constexpr FFixedPoint operator-() const
    {
        return FromRaw(static_cast<int64>(0ULL - static_cast<uint64>(RawValue)));
    }
    constexpr FFixedPoint& operator+=(const FFixedPoint& Other) { RawValue += Other.RawValue; return *this; }
    constexpr FFixedPoint& operator-=(const FFixedPoint& Other) { RawValue -= Other.RawValue; return *this; }

    static constexpr uint64 DivU128ByU64Constexpr(uint64 DividendHi, uint64 DividendLo, uint64 Divisor)
    {
        // Precondition: Divisor != 0 && DividendHi < Divisor (so exact quotient fits in uint64)
        uint64 Remainder = DividendHi;
        uint64 Quotient = 0ULL;
        for (int32 Bit = 63; Bit >= 0; --Bit)
        {
            const uint64 Carry = Remainder >> 63;
            Remainder = (Remainder << 1) | ((DividendLo >> Bit) & 1ULL);
            if (Carry != 0ULL || Remainder >= Divisor)
            {
                Remainder -= Divisor;
                Quotient |= (1ULL << Bit);
            }
        }
        return Quotient;
    }

    constexpr FFixedPoint operator*(const FFixedPoint& Other) const
    {
#if defined(__SIZEOF_INT128__)
        const __int128 Product = static_cast<__int128>(RawValue) * static_cast<__int128>(Other.RawValue);
        return FromRaw(static_cast<int64>(Product >> FractionalBits));
#else
#if defined(_MSC_VER) && defined(_M_X64)
        if (!std::is_constant_evaluated())
        {
            int64 HighProduct = 0;
            const int64 LowProduct = _mul128(RawValue, Other.RawValue, &HighProduct);
            const uint64 Shifted = (static_cast<uint64>(LowProduct) >> 32) | (static_cast<uint64>(HighProduct) << 32);
            return FromRaw(static_cast<int64>(Shifted));
        }
#endif
        const int64 A_Hi = RawValue >> 32;
        const uint64 A_Lo = static_cast<uint64>(RawValue) & 0xFFFFFFFFULL;
        const int64 B_Hi = Other.RawValue >> 32;
        const uint64 B_Lo = static_cast<uint64>(Other.RawValue) & 0xFFFFFFFFULL;

        const uint64 LoLo = (A_Lo * B_Lo) >> 32;
        const uint64 HiLo = static_cast<uint64>(A_Hi) * B_Lo;
        const uint64 LoHi = A_Lo * static_cast<uint64>(B_Hi);
        const uint64 HiHi = (static_cast<uint64>(A_Hi) * static_cast<uint64>(B_Hi)) << 32;

        return FromRaw(static_cast<int64>(LoLo + HiLo + LoHi + HiHi));
#endif
    }

    constexpr FFixedPoint operator/(const FFixedPoint& Other) const
    {
        if (Other.RawValue == 0 || RawValue == 0)
        {
            return FromRaw(0);
        }

        const bool bNegative = (RawValue < 0) != (Other.RawValue < 0);
        const uint64 AbsNum = (RawValue < 0)
            ? (0ULL - static_cast<uint64>(RawValue))
            : static_cast<uint64>(RawValue);
        const uint64 AbsDen = (Other.RawValue < 0)
            ? (0ULL - static_cast<uint64>(Other.RawValue))
            : static_cast<uint64>(Other.RawValue);

        // 128-bit unsigned dividend = AbsNum << 32 = (DividendHi * 2^64) + DividendLo
        const uint64 DividendHi = AbsNum >> FractionalBits;
        const uint64 DividendLo = AbsNum << FractionalBits;

        constexpr int64 MaxRawInt64 = 9223372036854775807LL;
        constexpr int64 MinRawInt64 = -9223372036854775807LL - 1LL;

        // Guard against 64-bit unsigned quotient overflow (prevents hardware #DE trap in _udiv128)
        if (DividendHi >= AbsDen)
        {
            return FromRaw(bNegative ? MinRawInt64 : MaxRawInt64);
        }

        uint64 QuotientMag = 0ULL;
#if defined(__SIZEOF_INT128__)
        const unsigned __int128 Dividend128 =
            (static_cast<unsigned __int128>(DividendHi) << 64) | static_cast<unsigned __int128>(DividendLo);
        QuotientMag = static_cast<uint64>(Dividend128 / static_cast<unsigned __int128>(AbsDen));
#elif defined(_MSC_VER) && defined(_M_X64) && (_MSC_VER >= 1920)
        if (!std::is_constant_evaluated())
        {
            uint64 Remainder = 0ULL;
            QuotientMag = _udiv128(DividendHi, DividendLo, AbsDen, &Remainder);
        }
        else
        {
            QuotientMag = DivU128ByU64Constexpr(DividendHi, DividendLo, AbsDen);
        }
#else
        QuotientMag = DivU128ByU64Constexpr(DividendHi, DividendLo, AbsDen);
#endif

        if (!bNegative)
        {
            if (QuotientMag > static_cast<uint64>(MaxRawInt64))
            {
                return FromRaw(MaxRawInt64);
            }
            return FromRaw(static_cast<int64>(QuotientMag));
        }
        else
        {
            constexpr uint64 MaxNegMag = 0x8000000000000000ULL;
            if (QuotientMag >= MaxNegMag)
            {
                return FromRaw(MinRawInt64);
            }
            return FromRaw(static_cast<int64>(0ULL - QuotientMag));
        }
    }

    constexpr FFixedPoint& operator*=(const FFixedPoint& Other) { *this = *this * Other; return *this; }
    constexpr FFixedPoint& operator/=(const FFixedPoint& Other) { *this = *this / Other; return *this; }

    constexpr auto operator<=>(const FFixedPoint& Other) const = default;

    static constexpr FFixedPoint Abs(FFixedPoint Val)
    {
        if (Val.RawValue >= 0)
        {
            return Val;
        }
        constexpr int64 MinRawInt64 = -9223372036854775807LL - 1LL;
        constexpr int64 MaxRawInt64 = 9223372036854775807LL;
        return (Val.RawValue == MinRawInt64) ? FromRaw(MaxRawInt64) : FromRaw(-Val.RawValue);
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
