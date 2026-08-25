"""
Проверка локального расчёта таможенных платежей РФ (customs_ru.py).

Запуск: python test_customs_ru.py
Тесты не ходят в сеть — курсы ЦБ передаются явно, чтобы результаты были
воспроизводимыми.
"""

from customs_ru import (
    calculate_customs_duty_eur,
    calculate_customs_fee,
    calculate_customs_ru,
    calculate_excise_russia,
)
from util_table_ru import get_util_fee_ru

# Фиксированные курсы для воспроизводимости (близко к ЦБ на 26.08.2026)
EUR = 98.5182
KRW = 0.0611788

_failures = []


def check(name, actual, expected):
    if actual != expected:
        _failures.append(f"{name}: получено {actual!r}, ожидалось {expected!r}")
        print(f"  FAIL  {name}: {actual!r} != {expected!r}")
    else:
        print(f"  ok    {name} = {actual!r}")


def test_customs_fee_brackets():
    print("\nСбор за таможенные операции (границы диапазонов)")
    check("200 000 ₽", calculate_customs_fee(200_000), 1_231)
    check("200 000.01 ₽", calculate_customs_fee(200_000.01), 2_462)
    check("450 000 ₽", calculate_customs_fee(450_000), 2_462)
    check("450 000.01 ₽", calculate_customs_fee(450_000.01), 4_924)
    check("1 200 000 ₽", calculate_customs_fee(1_200_000), 4_924)
    check("1 200 000.01 ₽", calculate_customs_fee(1_200_000.01), 13_541)
    check("2 700 000 ₽", calculate_customs_fee(2_700_000), 13_541)
    check("2 700 000.01 ₽", calculate_customs_fee(2_700_000.01), 18_465)
    check("4 200 000 ₽", calculate_customs_fee(4_200_000), 18_465)
    check("4 200 000.01 ₽", calculate_customs_fee(4_200_000.01), 21_344)
    check("5 500 000 ₽", calculate_customs_fee(5_500_000), 21_344)
    check("5 500 000.01 ₽", calculate_customs_fee(5_500_000.01), 49_240)
    check("10 000 000 ₽", calculate_customs_fee(10_000_000), 49_240)
    check("10 000 000.01 ₽", calculate_customs_fee(10_000_000.01), 73_860)


def test_duty_under_3_years():
    print("\nПошлина до 3 лет: процент против минимума за см³")
    # 8 000 € / 1000 см³: 54 % = 4 320 €, минимум 2.5 × 1000 = 2 500 € → берём процент
    check("8000 €, 1000 см³ → процент", calculate_customs_duty_eur("0-3", 1000, 8_000), 4_320.0)
    # 8 000 € / 3000 см³: 54 % = 4 320 €, минимум 2.5 × 3000 = 7 500 € → берём минимум
    check("8000 €, 3000 см³ → минимум", calculate_customs_duty_eur("0-3", 3000, 8_000), 7_500.0)
    # Граница 8 500 € остаётся в первом диапазоне (54 %)
    check("8500 €, 1000 см³", calculate_customs_duty_eur("0-3", 1000, 8_500), 8_500 * 0.54)
    # 8 500.01 € уже во втором (48 %, минимум 3.5)
    check(
        "8500.01 €, 1000 см³",
        round(calculate_customs_duty_eur("0-3", 1000, 8_500.01), 4),
        round(max(8_500.01 * 0.48, 3_500.0), 4),
    )
    # G80 2.5T: 21 052 € / 2497 см³ → минимум 5.5 × 2497 = 13 733.5 € бьёт 48 %
    check("21052 €, 2497 см³", calculate_customs_duty_eur("0-3", 2497, 21_052), 13_733.5)


def test_duty_by_volume():
    print("\nПошлина 3–5 лет и старше 5 лет (границы объёма)")
    for age, rates in (
        ("3-5", [(1000, 1.5), (1500, 1.7), (1800, 2.5), (2300, 2.7), (3000, 3.0), (3001, 3.6)]),
        ("5-7", [(1000, 3.0), (1500, 3.2), (1800, 3.5), (2300, 4.8), (3000, 5.0), (3001, 5.7)]),
    ):
        for volume, rate in rates:
            check(f"{age}, {volume} см³", calculate_customs_duty_eur(age, volume, 0), volume * rate)
    # 7-0 считается по той же таблице, что и 5-7
    check("7-0 == 5-7", calculate_customs_duty_eur("7-0", 2199, 0), calculate_customs_duty_eur("5-7", 2199, 0))


def test_util_fee_boundaries():
    print("\nУтильсбор: пороги 160 л.с. и 3.0 л, возрасты старше 3 лет")
    check("160 л.с., 1998 см³, 0-3", get_util_fee_ru(1998, 160, "0-3", 1), 3_400)
    check("161 л.с., 1998 см³, 0-3", get_util_fee_ru(1998, 161, "0-3", 1), 900_000)
    check("160 л.с., 1998 см³, 3-5", get_util_fee_ru(1998, 160, "3-5", 1), 5_200)
    # Раньше здесь возвращалось None и расчёт срывался
    check("128 л.с., 1582 см³, 5-7", get_util_fee_ru(1582, 128, "5-7", 1), 5_200)
    check("128 л.с., 1582 см³, 7-0", get_util_fee_ru(1582, 128, "7-0", 1), 5_200)
    check("3000 см³, 150 л.с., 0-3", get_util_fee_ru(3000, 150, "0-3", 1), 3_400)
    check("3001 см³, 150 л.с., 0-3", get_util_fee_ru(3001, 150, "0-3", 1), 2_584_000)
    check("3600 см³, 400 л.с., 3-5", get_util_fee_ru(3600, 400, "3-5", 1), 5_558_400)
    check("электро 80 л.с., 0-3", get_util_fee_ru(111, 80, "0-3", 4), 3_400)
    check("электро 81 л.с., 0-3", get_util_fee_ru(111, 81, "0-3", 4), 991_200)


def test_excise():
    print("\nАкциз (ставки 2026)")
    check("90 л.с.", calculate_excise_russia(90), 0)
    check("91 л.с.", calculate_excise_russia(91), 91 * 64)
    check("150 л.с.", calculate_excise_russia(150), 150 * 64)
    check("151 л.с.", calculate_excise_russia(151), 151 * 613)
    check("300 л.с.", calculate_excise_russia(300), 300 * 1_004)
    check("501 л.с.", calculate_excise_russia(501), 501 * 1_829)


def test_full_ice():
    print("\nПолный расчёт: бензин 1998 см³, 150 л.с., 3-5 лет, 20 000 000 ₩")
    r = calculate_customs_ru(1998, 20_000_000, "3-5", 1, 150, KRW, EUR)
    check("таможенная стоимость, ₽", r["value_rub"], round(20_000_000 * KRW))
    check("пошлина, ₽", r["tax"], round(1998 * 2.7 * EUR))
    check("сбор, ₽", r["sbor"], 13_541)
    check("утильсбор, ₽", r["util"], 5_200)
    check("утиль льготный", r["util_preferential"], True)
    check("акциз (не платится)", r["excise"], 0)
    check("НДС (не платится)", r["vat"], 0)


def test_full_ice_commercial_util():
    print("\nПолный расчёт: 304 л.с. → коммерческий утильсбор")
    r = calculate_customs_ru(2497, 33_900_000, "0-3", 1, 304, KRW, EUR)
    check("пошлина, ₽", r["tax"], round(2497 * 5.5 * EUR))
    check("утильсбор, ₽", r["util"], 2_620_800)  # блок 2.0-3.0 л, 280-310 л.с., до 3 лет
    check("утиль льготный", r["util_preferential"], False)


def test_full_electric():
    print("\nПолный расчёт: электромобиль 229 л.с., 0-3 лет, 40 000 000 ₩")
    r = calculate_customs_ru(111, 40_000_000, "0-3", 4, 229, KRW, EUR)
    value = 40_000_000 * KRW
    duty = value * 0.15
    excise = 229 * 1_004
    check("таможенная стоимость, ₽", r["value_rub"], round(value))
    check("пошлина 15 %, ₽", r["tax"], round(duty))
    check("акциз, ₽", r["excise"], excise)
    check("НДС 22 %, ₽", r["vat"], round((value + duty + excise) * 0.22))
    check("утильсбор (по мощности), ₽", r["util"], 2_599_200)  # электро, 220-250 л.с., до 3 лет
    check("объём не влияет на электро", r["tax"], calculate_customs_ru(3500, 40_000_000, "0-3", 4, 229, KRW, EUR)["tax"])


def test_invalid_input_raises():
    print("\nНекорректные данные не должны давать нулевую смету")
    for name, args in (
        ("нулевой курс KRW", (1998, 20_000_000, "3-5", 1, 150, 0, EUR)),
        ("нулевой курс EUR", (1998, 20_000_000, "3-5", 1, 150, KRW, 0)),
        ("нулевая мощность", (1998, 20_000_000, "3-5", 1, 0, KRW, EUR)),
        ("нулевая цена", (1998, 0, "3-5", 1, 150, KRW, EUR)),
        ("нулевой объём (ДВС)", (0, 20_000_000, "3-5", 1, 150, KRW, EUR)),
        ("неизвестный возраст", (1998, 20_000_000, "10-15", 1, 150, KRW, EUR)),
    ):
        try:
            calculate_customs_ru(*args)
            check(name, "не было исключения", "ValueError")
        except ValueError:
            print(f"  ok    {name} → ValueError")


if __name__ == "__main__":
    test_customs_fee_brackets()
    test_duty_under_3_years()
    test_duty_by_volume()
    test_util_fee_boundaries()
    test_excise()
    test_full_ice()
    test_full_ice_commercial_util()
    test_full_electric()
    test_invalid_input_raises()

    print("\n" + "=" * 60)
    if _failures:
        print(f"ПРОВАЛЕНО: {len(_failures)}")
        for f in _failures:
            print("  " + f)
        raise SystemExit(1)
    print("Все проверки пройдены")
