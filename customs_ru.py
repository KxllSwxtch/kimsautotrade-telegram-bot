"""
Расчёт таможенных платежей РФ для физического лица (личное пользование).

Полностью локальный расчёт — внешние калькуляторы (calcus.ru, pan-auto.ru) больше
не используются: они ограничивают частоту запросов, отдают 429 и превращают каждую
котировку в сетевой запрос, который может не ответить.

Источники ставок (сверено 26.08.2026):

* Пошлина — Решение Совета ЕЭК от 20.12.2017 № 107, Приложение 2 (ред. 24.02.2026).
  Единые ставки для товаров для личного пользования.
* Сбор за таможенные операции — ПП РФ от 23.10.2025 № 1638 (действует с 01.01.2026).
* Акциз — ставки с 01.01.2026.
* НДС — 22 % с 01.01.2026 (ФЗ № 425-ФЗ).
* Утильсбор — utils-2026.xlsx, см. util_table_ru.py.

ВАЖНО: ставки привязаны к датам. При изменении ЕЭК 107, ПП 1638, шкалы акциза или
коэффициентов утильсбора таблицы ниже надо пересматривать.

Кто что платит:
* ДВС / гибрид, физлицо — сбор + пошлина + утильсбор. Акциз и НДС НЕ платятся.
* Электромобиль — совокупный таможенный платёж: сбор + пошлина 15 % + акциз + НДС,
  плюс утильсбор. Категория владельца значения не имеет.
"""

from util_table_ru import get_util_fee_ru

# Коды типов двигателя (как в map_fuel_type_to_engine_code):
# 1 - бензин, 2 - дизель, 4 - электро, 5 - послед. гибрид, 6 - парал. гибрид
ELECTRIC_ENGINE_CODE = 4

# Ставка пошлины на электромобили — 15 % от таможенной стоимости.
EV_DUTY_RATE = 0.15

# НДС при ввозе, с 01.01.2026.
VAT_RATE = 0.22

# Сбор за таможенные операции: (верхняя граница таможенной стоимости в ₽, сбор в ₽).
# Границы включительные, последняя запись — «всё, что выше».
CUSTOMS_FEE_BRACKETS = [
    (200_000, 1_231),
    (450_000, 2_462),
    (1_200_000, 4_924),
    (2_700_000, 13_541),
    (4_200_000, 18_465),
    (5_500_000, 21_344),
    (10_000_000, 49_240),
    (float("inf"), 73_860),
]

# Пошлина для авто младше 3 лет: (верхняя граница стоимости в EUR, доля, минимум EUR/см³).
# Берётся большее из двух: процент от стоимости или минимум за объём.
DUTY_UNDER_3_YEARS = [
    (8_500, 0.54, 2.5),
    (16_700, 0.48, 3.5),
    (42_300, 0.48, 5.5),
    (84_500, 0.48, 7.5),
    (169_000, 0.48, 15.0),
    (float("inf"), 0.48, 20.0),
]

# Пошлина для авто 3–5 лет: (верхняя граница объёма в см³, EUR/см³).
DUTY_3_TO_5_YEARS = [
    (1_000, 1.5),
    (1_500, 1.7),
    (1_800, 2.5),
    (2_300, 2.7),
    (3_000, 3.0),
    (float("inf"), 3.6),
]

# Пошлина для авто старше 5 лет: (верхняя граница объёма в см³, EUR/см³).
DUTY_OVER_5_YEARS = [
    (1_000, 3.0),
    (1_500, 3.2),
    (1_800, 3.5),
    (2_300, 4.8),
    (3_000, 5.0),
    (float("inf"), 5.7),
]

# Акциз с 01.01.2026: (верхняя граница мощности в л.с., ₽ за 1 л.с.).
EXCISE_BRACKETS = [
    (90, 0),
    (150, 64),
    (200, 613),
    (300, 1_004),
    (400, 1_711),
    (500, 1_771),
    (float("inf"), 1_829),
]

# Возрастные категории, для которых пошлина считается по ставке «старше 5 лет».
_OVER_5_YEARS = {"5-7", "7-0"}

# Льготный утильсбор — 3 400 ₽ (до 3 лет) и 5 200 ₽ (старше 3 лет).
PREFERENTIAL_UTIL_FEES = {3_400, 5_200}


def calculate_customs_fee(value_rub):
    """Сбор за таможенные операции по таможенной стоимости в рублях."""
    for limit, fee in CUSTOMS_FEE_BRACKETS:
        if value_rub <= limit:
            return fee


def calculate_excise_russia(horse_power):
    """Акциз в рублях по мощности двигателя в л.с."""
    for limit, rate_per_hp in EXCISE_BRACKETS:
        if horse_power <= limit:
            return round(horse_power * rate_per_hp)


def calculate_customs_duty_eur(age, engine_volume, value_eur):
    """
    Таможенная пошлина в ЕВРО для ДВС и гибридов (единая ставка для физлиц).

    :param age: "0-3" | "3-5" | "5-7" | "7-0"
    :param engine_volume: объём двигателя в см³
    :param value_eur: таможенная стоимость в евро
    """
    if age == "0-3":
        for limit, percent, min_per_cc in DUTY_UNDER_3_YEARS:
            if value_eur <= limit:
                return max(value_eur * percent, engine_volume * min_per_cc)

    table = DUTY_OVER_5_YEARS if age in _OVER_5_YEARS else DUTY_3_TO_5_YEARS
    for limit, rate_per_cc in table:
        if engine_volume <= limit:
            return engine_volume * rate_per_cc


def calculate_customs_ru(
    engine_volume,
    price_krw,
    age,
    engine_code,
    horse_power,
    krw_rub_rate,
    eur_rub_rate,
):
    """
    Полный расчёт таможенных платежей РФ для физлица (личное пользование).

    :param engine_volume: объём двигателя в см³ (для электромобилей не используется)
    :param price_krw: стоимость авто в вонах
    :param age: возрастная категория "0-3" | "3-5" | "5-7" | "7-0"
    :param engine_code: 1=бензин, 2=дизель, 4=электро, 5=послед.гибрид, 6=парал.гибрид
    :param horse_power: мощность в л.с. (обязательна — от неё зависит утильсбор и акциз)
    :param krw_rub_rate: курс ЦБ, рублей за 1 вону
    :param eur_rub_rate: курс ЦБ, рублей за 1 евро
    :return: dict со всеми платежами в рублях (int) и вспомогательными полями
    :raises ValueError: если входные данные не позволяют посчитать платёж
    """
    try:
        engine_volume = int(float(engine_volume))
        price_krw = float(price_krw)
        horse_power = int(float(horse_power))
        engine_code = int(engine_code)
        krw_rub_rate = float(krw_rub_rate)
        eur_rub_rate = float(eur_rub_rate)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Некорректные данные для расчёта таможни: {e}")

    if price_krw <= 0:
        raise ValueError("Стоимость автомобиля должна быть больше нуля")
    if horse_power <= 0:
        raise ValueError("Мощность двигателя должна быть больше нуля")
    if krw_rub_rate <= 0 or eur_rub_rate <= 0:
        raise ValueError("Курсы ЦБ недоступны — расчёт таможни невозможен")

    is_electric = engine_code == ELECTRIC_ENGINE_CODE

    if not is_electric and engine_volume <= 0:
        raise ValueError("Объём двигателя должен быть больше нуля")

    value_rub = price_krw * krw_rub_rate
    value_eur = value_rub / eur_rub_rate

    customs_fee = calculate_customs_fee(value_rub)

    if is_electric:
        # Совокупный таможенный платёж: пошлина 15 % + акциз + НДС.
        customs_duty = value_rub * EV_DUTY_RATE
        excise = calculate_excise_russia(horse_power)
        vat = (value_rub + customs_duty + excise) * VAT_RATE
    else:
        customs_duty = calculate_customs_duty_eur(age, engine_volume, value_eur) * eur_rub_rate
        excise = 0
        vat = 0

    util_fee = get_util_fee_ru(engine_volume, horse_power, age, engine_code)
    if util_fee is None:
        raise ValueError(
            f"Утильсбор не определён: объём={engine_volume} см³, "
            f"мощность={horse_power} л.с., возраст={age}, двигатель={engine_code}"
        )

    return {
        "sbor": int(round(customs_fee)),
        "tax": int(round(customs_duty)),
        "util": int(round(util_fee)),
        "excise": int(round(excise)),
        "vat": int(round(vat)),
        "value_rub": int(round(value_rub)),
        "value_eur": int(round(value_eur)),
        "util_preferential": util_fee in PREFERENTIAL_UTIL_FEES,
    }
