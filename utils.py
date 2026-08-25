import datetime
import gc
import locale

import requests

from kgs_customs_table import KGS_CUSTOMS_TABLE

# Каталог характеристик Encar. Отдаёт мощность (mxPwrPs) по кодам модели из
# карточки автомобиля. ВНИМАНИЕ: ответ в кодировке cp949 (EUC-KR), не UTF-8.
ENCAR_SPEC_URL = "https://m.encar.com/mocha/rel.do?method=modelSpecificationByJson"

# Правдоподобный диапазон мощности легкового авто. Всё, что вне — считаем мусором
# и просим пользователя ввести мощность вручную: заниженная мощность даёт льготный
# утильсбор вместо коммерческого и занижает смету в разы.
_MIN_PLAUSIBLE_HP = 20
_MAX_PLAUSIBLE_HP = 2000


def map_fuel_type_to_engine_code(fuel_type):
    """
    Преобразует название типа топлива в код двигателя.

    Коды двигателя:
    1 - бензин
    2 - дизель
    4 - электро
    5 - последовательный гибрид
    6 - параллельный гибрид
    """
    fuel_mapping = {
        # Корейские названия (encar.com API, spec.fuelName)
        "가솔린": 1,  # бензин
        "디젤": 2,  # дизель
        "전기": 4,  # электро
        "하이브리드": 6,  # гибрид (по умолчанию параллельный)
        "가솔린+전기": 6,  # бензин + электро (так encar называет гибрид)
        "디젤+전기": 6,  # дизель + электро
        "LPG": 1,  # LPG считаем бензином
        # Русские названия (ручной расчёт)
        "Бензин": 1,
        "Дизель": 2,
        "Электро": 4,
        "Электромобиль": 4,
        "Гибрид": 6,
        "Последовательный гибрид": 5,
        "Параллельный гибрид": 6,
    }
    return fuel_mapping.get(fuel_type, 1)  # По умолчанию бензин


def get_car_power_from_encar(manufacturer_cd, model_cd, form_year, grade_cd):
    """
    Мощность двигателя (л.с.) из каталога характеристик Encar.

    Коды берутся из блока `category` карточки автомобиля (api.encar.com):
    manufacturerCd, modelCd, formYear, gradeCd.

    :return: мощность в л.с. (int) или None, если данных нет — тогда мощность
             нужно запросить у пользователя.
    """
    if not all([manufacturer_cd, model_cd, form_year, grade_cd]):
        print("Encar: не хватает кодов модели для запроса мощности")
        return None

    url = (
        f"{ENCAR_SPEC_URL}"
        f"&mnfccd={manufacturer_cd}"
        f"&mdlcd={model_cd}"
        f"&year={form_year}"
        f"&clshdcd={grade_cd}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://m.encar.com/",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Ответ приходит в cp949 (EUC-KR); без явной кодировки .json() падает
        # на корейских названиях полей.
        response.encoding = "cp949"
        data = response.json()

        # Для неизвестных комплектаций Encar отдаёт value = "-", а не ошибку.
        raw_power = (data.get("mxPwrPs") or {}).get("value")
        power = int(float(raw_power))

        if not _MIN_PLAUSIBLE_HP <= power <= _MAX_PLAUSIBLE_HP:
            print(f"Encar: неправдоподобная мощность {power} л.с., игнорируем")
            return None

        print(f"Encar: мощность {power} л.с. (коды {manufacturer_cd}/{model_cd}/{form_year}/{grade_cd})")
        return power
    except requests.RequestException as e:
        print(f"Encar: ошибка запроса характеристик: {e}")
        return None
    except (TypeError, ValueError, AttributeError, KeyError) as e:
        print(f"Encar: мощность не определена в ответе каталога: {e}")
        return None


# Очищение памяти
def clear_memory():
    gc.collect()


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


def calculate_age(year, month):
    """
    Рассчитывает возрастную категорию автомобиля.

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
