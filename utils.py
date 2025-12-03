import requests
import gc
import datetime
import locale
import time
import threading
import random
from kgs_customs_table import KGS_CUSTOMS_TABLE

HTTP_PROXY = "http://B01vby:GBno0x@45.118.250.2:8000"
proxies = {"http": HTTP_PROXY, "https": HTTP_PROXY}


def map_fuel_type_to_engine_code(fuel_type):
    """
    Maps fuel type to calcus.ru engine code.
    Supports Korean (from encar API) and Russian (from pan-auto.ru) fuel names.

    Engine codes:
    1 - Gasoline
    2 - Diesel
    4 - Electric
    5 - Sequential Hybrid (Последовательный гибрид)
    6 - Parallel Hybrid (Параллельный гибрид)
    """
    fuel_mapping = {
        # Korean fuel names (from encar.com API spec.fuelName)
        "가솔린": 1,  # Gasoline
        "디젤": 2,  # Diesel
        "전기": 4,  # Electric
        "하이브리드": 6,  # Hybrid (default to parallel)
        "LPG": 1,  # Treat LPG as gasoline
        # Russian fuel names (from pan-auto.ru API)
        "Бензин": 1,
        "Дизель": 2,
        "Электро": 4,
        "Электромобиль": 4,
        "Гибрид": 6,
        "Последовательный гибрид": 5,
        "Параллельный гибрид": 6,
    }
    return fuel_mapping.get(fuel_type, 1)  # Default to gasoline


def get_car_data_from_panauto(car_id):
    """
    Fetches car data from pan-auto.ru API.
    Returns dict with hp, fuel_type, and pre-calculated customs values if found.
    Returns None if car not found or API error.
    """
    url = f"https://zefir.pan-auto.ru/api/cars/{car_id}/"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en,ru;q=0.9",
        "Connection": "keep-alive",
        "Origin": "https://pan-auto.ru",
        "Referer": "https://pan-auto.ru/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            print(f"Car {car_id} not found on pan-auto.ru")
            return None
        response.raise_for_status()
        data = response.json()

        # Extract customs values from RUB costs
        rub_costs = data.get("costs", {}).get("RUB", {})

        result = {
            "hp": data.get("hp"),  # Horsepower
            "fuel_type": data.get("fuelType"),  # Russian fuel name
            "customs": {
                "sbor": rub_costs.get("clearanceCost", 0),  # Customs fee (сбор)
                "tax": rub_costs.get("customsDuty", 0),  # Customs duty (пошлина)
                "util": rub_costs.get("utilizationFee", 0),  # Utilization fee (утильсбор)
            },
        }

        print(
            f"Pan-auto.ru data for car {car_id}: HP={result['hp']}, fuel={result['fuel_type']}"
        )
        return result
    except requests.RequestException as e:
        print(f"Error fetching from pan-auto.ru: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching from pan-auto.ru: {e}")
        return None


# Enhanced rate limiting для calcus.ru - максимум 4 запроса в секунду для безопасности
_last_request_time = 0
_min_request_interval = 0.25  # 1/4 секунды между запросами (4 req/sec)
_rate_limit_lock = threading.Lock()  # Thread-safe rate limiting


def _rate_limit():
    """Применяет ограничение скорости запросов к calcus.ru с thread-safe механизмом"""
    global _last_request_time

    with _rate_limit_lock:
        current_time = time.time()
        time_since_last_request = current_time - _last_request_time

        if time_since_last_request < _min_request_interval:
            sleep_time = _min_request_interval - time_since_last_request
            time.sleep(sleep_time)

        _last_request_time = time.time()


# Очищение памяти
def clear_memory():
    gc.collect()


def clean_number(value):
    """Очищает строку от пробелов и преобразует в число"""
    return int(float(value.replace(" ", "").replace(",", ".")))


def get_customs_fees_russia(
    engine_volume, car_price, car_year, car_month, engine_type=1, horse_power=None
):
    """
    Запрашивает расчёт таможенных платежей с сайта calcus.ru с retry логикой.
    :param engine_volume: Объём двигателя (куб. см)
    :param car_price: Цена авто в вонах
    :param car_year: Год выпуска авто
    :param car_month: Месяц выпуска авто
    :param engine_type: Тип двигателя (1 - бензин, 2 - дизель, 4 - электро, 5 - послед. гибрид, 6 - парал. гибрид)
    :param horse_power: Мощность двигателя в л.с. (обязательно с декабря 2025)
    :return: JSON с результатами расчёта или None при ошибке
    """
    url = "https://calcus.ru/calculate/Customs"
    max_retries = 4
    base_delay = 1.0

    # Если мощность не указана, используем расчётную (объём / 15)
    if horse_power is None:
        horse_power = calculate_horse_power(engine_volume)
        print(f"HP not provided, using estimated value: {horse_power}")

    payload = {
        "owner": 1,  # Физлицо
        "age": calculate_age(car_year, car_month),  # Возрастная категория
        "engine": engine_type,  # Тип двигателя
        "power": int(horse_power),  # Мощность в л.с.
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

    for attempt in range(max_retries):
        try:
            _rate_limit()
            response = requests.post(url, data=payload, headers=headers, timeout=10)

            if response.status_code == 429:
                # Exponential backoff для 429 ошибок
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Получен 429 ответ от calcus.ru, ожидание {delay:.2f} секунд... (попытка {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue

            response.raise_for_status()
            result = response.json()

            # Проверяем что ответ содержит необходимые поля
            if result and isinstance(result, dict) and all(key in result for key in ["sbor", "tax", "util"]):
                print(f"Успешный запрос к calcus.ru (попытка {attempt + 1})")
                return result
            else:
                print(f"Неполный ответ от calcus.ru: {result}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay)
                    continue

        except requests.Timeout:
            print(f"Таймаут запроса к calcus.ru (попытка {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
                continue
        except requests.RequestException as e:
            print(f"Ошибка при запросе к calcus.ru (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue

    print("Все попытки запроса к calcus.ru исчерпаны")
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
