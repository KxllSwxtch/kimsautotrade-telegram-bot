import requests
import gc
import datetime
import locale
from kgs_customs_table import KGS_CUSTOMS_TABLE


# Очищение памяти
def clear_memory():
    gc.collect()


def clean_number(value):
    """Очищает строку от пробелов и преобразует в число"""
    return int(float(value.replace(" ", "").replace(",", ".")))


def get_customs_fees_russia(
    engine_volume, car_price, car_year, car_month, engine_type=1
):
    """
    Запрашивает расчёт таможенных платежей с сайта calcus.ru.
    :param engine_volume: Объём двигателя (куб. см)
    :param car_price: Цена авто в вонах
    :param car_year: Год выпуска авто
    :param engine_type: Тип двигателя (1 - бензин, 2 - дизель, 3 - гибрид, 4 - электромобиль)
    :return: JSON с результатами расчёта
    """
    url = "https://calcus.ru/calculate/Customs"

    payload = {
        "owner": 1,  # Физлицо
        "age": calculate_age(car_year, car_month),  # Возрастная категория
        "engine": engine_type,  # Тип двигателя (по умолчанию 1 - бензин)
        "power": 1,  # Лошадиные силы (можно оставить 1)
        "power_unit": 1,  # Тип мощности (1 - л.с.)
        "value": int(engine_volume),  # Объём двигателя
        "price": int(car_price),  # Цена авто в KRW
        "curr": "KRW",  # Валюта
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://calcus.ru/",
        "Origin": "https://calcus.ru",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к calcus.ru: {e}")
        return None


def calculate_customs_fee_kg(engine_volume, car_year):
    """
    Рассчитывает таможенную пошлину для Кыргызстана на основе таблицы KGS_CUSTOMS_TABLE.

    :param engine_volume: Объём двигателя в см³.
    :param car_year: Год выпуска автомобиля.
    :return: Таможенная пошлина в KGS.
    """

    engine_volume = int(engine_volume)

    # Если год не найден, подбираем ближайший предыдущий год
    while car_year not in KGS_CUSTOMS_TABLE:
        car_year -= 1
        if car_year < min(KGS_CUSTOMS_TABLE.keys()):
            raise ValueError("Год выпуска автомобиля слишком старый для расчёта.")

    year_table = KGS_CUSTOMS_TABLE[car_year]

    # Найти соответствующий диапазон объёма двигателя
    for volume_limit in sorted(year_table.keys()):
        if engine_volume <= volume_limit:
            return year_table[volume_limit]

    # Если объём двигателя превышает все лимиты
    return year_table[max(year_table.keys())]


def calculate_excise_russia(horse_power):
    """
    Расчет акциза на автомобиль на основе мощности двигателя в л.с.
    """
    if horse_power <= 90:
        return 0
    elif horse_power <= 150:
        return horse_power * 61
    elif horse_power <= 200:
        return horse_power * 583
    elif horse_power <= 300:
        return horse_power * 955
    elif horse_power <= 400:
        return horse_power * 1628
    elif horse_power <= 500:
        return horse_power * 1685
    else:
        return horse_power * 1740


# Акциза с помощью объёма авто
def calculate_excise_by_volume(engine_volume):
    """
    Рассчитывает акцизный сбор на основе объёма двигателя в куб. см.
    """
    engine_volume_liters = engine_volume / 1000  # Переводим в литры

    if engine_volume_liters <= 1.0:
        return 0
    elif 1.0 < engine_volume_liters <= 1.5:
        return 61 * engine_volume_liters * 100  # Примерное количество л.с.
    elif 1.5 < engine_volume_liters <= 2.0:
        return 583 * engine_volume_liters * 100
    elif 2.0 < engine_volume_liters <= 3.0:
        return 955 * engine_volume_liters * 100
    elif 3.0 < engine_volume_liters <= 4.0:
        return 1628 * engine_volume_liters * 100
    elif 4.0 < engine_volume_liters <= 5.0:
        return 1685 * engine_volume_liters * 100
    else:
        return 1740 * engine_volume_liters * 100


# Утильсбор
def calculate_recycling_fee(engine_volume, age):
    """
    Рассчитывает утилизационный сбор в России для физических лиц.

    :param engine_volume: Объём двигателя в куб. см.
    :param age: Возраст автомобиля.
    :return: Утилизационный сбор в рублях.
    """
    base_rate = 20000  # Базовая ставка для легковых авто

    # Проверяем возраст автомобиля и устанавливаем соответствующий коэффициент
    if age == "до 3 лет":
        if engine_volume <= 1000:
            coefficient = 0.17
        elif engine_volume <= 2000:
            coefficient = 0.17
        elif engine_volume <= 3000:
            coefficient = 0.17
        elif engine_volume <= 3500:
            coefficient = 89.73
        else:
            coefficient = 114.26
    else:  # Для автомобилей старше 3 лет
        if engine_volume <= 1000:
            coefficient = 0.26
        elif engine_volume <= 2000:
            coefficient = 0.26
        elif engine_volume <= 3000:
            coefficient = 0.26
        elif engine_volume <= 3500:
            coefficient = 137.36
        else:
            coefficient = 150.2

    # Рассчитываем утилизационный сбор
    recycling_fee = base_rate * coefficient
    return round(recycling_fee, 2)


# Таможенный сбор
def calculate_customs_fee(car_price_rub):
    """
    Рассчитывает таможенный сбор в зависимости от стоимости автомобиля в рублях.
    """
    if car_price_rub <= 200000:
        return 1067
    elif car_price_rub <= 450000:
        return 2134
    elif car_price_rub <= 1200000:
        return 4269
    elif car_price_rub <= 2700000:
        return 11746
    elif car_price_rub <= 4200000:
        return 16524
    elif car_price_rub <= 5500000:
        return 21344
    elif car_price_rub <= 7000000:
        return 27540
    else:
        return 30000


def calculate_horse_power(engine_volume):
    """
    Рассчитывает мощность двигателя в лошадиных силах (л.с.).
    """
    engine_volume = int(engine_volume)
    horse_power = round(engine_volume / 15)
    return horse_power


# Функция для расчёта возраста автомобиля для расчёта утильсбора
def calculate_age_for_utilization_fee(year):
    current_year = datetime.datetime.now().year
    age = current_year - int(year)
    return age


def calculate_age(year, month):
    """
    Рассчитывает возрастную категорию автомобиля по классификации calcus.ru.

    :param year: Год выпуска автомобиля
    :param month: Месяц выпуска автомобиля
    :return: Возрастная категория ("0-3", "3-5", "5-7", "7-0")
    """
    # Убираем ведущий ноль у месяца, если он есть
    month = int(month.lstrip("0")) if isinstance(month, str) else int(month)

    current_date = datetime.datetime.now()
    car_date = datetime.datetime(year=int(year), month=month, day=1)

    age_in_months = (
        (current_date.year - car_date.year) * 12 + current_date.month - car_date.month
    )

    if age_in_months < 36:
        return "0-3"
    elif 36 <= age_in_months < 60:
        return "3-5"
    elif 60 <= age_in_months < 84:
        return "5-7"
    else:
        return "7-0"


def format_number(number):
    number = float(number) if isinstance(number, str) else number
    return locale.format_string("%d", number, grouping=True)


def print_message(message: str):
    print("\n\n#######################")
    print(message)
    print("#######################\n\n")
    return None
