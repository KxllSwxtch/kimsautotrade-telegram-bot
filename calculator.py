import time
import telebot
import psycopg2
import os
import re
import requests
import datetime
import logging
import xml.etree.ElementTree as ET
import urllib.parse

from telebot import types
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

# utils.py import
from config import bot
from utils import (
    clear_memory,
    format_number,
    print_message,
    calculate_age,
    calculate_customs_fee_kg,
    get_customs_fees_russia,
    clean_number,
)


load_dotenv()

CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH_LOCAL")
DATABASE_URL = "postgres://uea5qru3fhjlj:p44343a46d4f1882a5ba2413935c9b9f0c284e6e759a34cf9569444d16832d4fe@c97r84s7psuajm.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d9pr93olpfl9bj"


# Переменные
car_data = {}
car_id_external = None
vehicle_no = None
vehicle_id = None


# Для Казахстана
usd_rate_kz = 0
krw_rate_kz = 0

# Для Кыргызстана
usd_rate_krg = 0
krw_rate_krg = 0
usd_rate_krw = 0

last_error_message_id = {}

# Для России
usd_rub_rate = 0
krw_rub_rate = 0
eur_rub_rate = 0

usdt_krw_rate = 0
usdt_rub_rate = 0

current_country = ""
car_fuel_type = ""


def get_usdt_to_krw_rate_bithumb():
    try:
        # Используем API Bithumb для получения курса USDT-KRW
        url = "https://api.bithumb.com/v1/ticker?markets=KRW-USDT"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data and data[0] and data[0]["trade_price"]:
                # Получаем курс из ответа API и вычитаем 40 пунктов
                raw_rate = float(data[0]["trade_price"])
                adjusted_rate = raw_rate - 40

                # Форматируем до целого числа
                formatted_rate = round(adjusted_rate)

                print(f"Курс USDT к KRW (Bithumb) -> {formatted_rate}")
                return formatted_rate

        # Если не удалось получить данные, используем запасной метод
        print("Не удалось получить курс USDT-KRW с Bithumb, используем запасной метод")
        return get_usdt_to_krw_rate()
    except Exception as e:
        print(f"Ошибка при получении курса USDT-KRW с Bithumb: {e}")
        return get_usdt_to_krw_rate()


def get_usdt_to_rub_rate():
    try:
        # Используем API Coinbase для получения курса USDT-RUB
        url = "https://api.coinbase.com/v2/prices/USDT-RUB/spot"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data and data.get("data") and data["data"].get("amount"):
                # Получаем курс из ответа API
                rate = float(data["data"]["amount"])

                # Форматируем до двух знаков после запятой
                formatted_rate = float(round(rate, 2))

                # Добавляем 5% к курсу
                rate_with_five_percent = formatted_rate + formatted_rate * 0.05

                print(f"Курс USDT к RUB -> {rate_with_five_percent}")
                return rate_with_five_percent

        # Если не удалось получить данные, возвращаем запасное значение
        print("Не удалось получить курс USDT-RUB, используем запасное значение")
        return 90.0  # Запасное значение
    except Exception as e:
        print(f"Ошибка при получении курса USDT-RUB: {e}")
        return 90.0  # Запасное значение в случае ошибки


def get_usdt_to_krw_rate():
    # URL для получения курса USDT к KRW
    url = "https://api.coinbase.com/v2/exchange-rates?currency=USDT"
    response = requests.get(url)
    data = response.json()

    # Извлечение курса KRW
    krw_rate = data["data"]["rates"]["KRW"]

    print(f"Курс USDT к KRW -> {str(float(krw_rate) + 4)}")

    return float(krw_rate) + 4


def get_usd_to_krw_rate():
    url = "https://api.manana.kr/exchange/rate.json?base=KRW&code=KRW,USD,JPY"
    response = requests.get(url)
    if response.status_code == 200:
        rates = response.json()
        for rate in rates:
            if rate["name"] == "USDKRW=X":
                return rate["rate"]
    else:
        raise Exception("Не удалось получить курс валют.")


# Функция для отправки меню выбора страны
def show_country_selection(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_russia = types.KeyboardButton("🇷🇺 Россия")
    btn_kazakhstan = types.KeyboardButton("🇰🇿 Казахстан")
    btn_kyrgyzstan = types.KeyboardButton("🇰🇬 Кыргызстан")

    # Добавление кнопок в меню
    markup.add(btn_russia, btn_kazakhstan, btn_kyrgyzstan)

    # Отправка сообщения с меню выбора страны
    bot.send_message(
        chat_id, "Пожалуйста, выберите страну для расчёта:", reply_markup=markup
    )


# Курс валют для Кыргызстана
def get_nbkr_currency_rates():
    global usd_rate_krg, krw_rate_krg

    clear_memory()

    print_message("[КУРС] КЫРГЫЗСТАН")

    url = "https://www.nbkr.kg/XML/daily.xml"
    weekly_url = "https://www.nbkr.kg/XML/weekly.xml"

    try:
        # Запрос к API НБКР
        response = requests.get(url)
        response.raise_for_status()

        # Парсинг XML-ответа
        root = ET.fromstring(response.content)

        # Словарь для хранения курсов валют
        currency_rates = {}

        # Валюты, которые нам нужны
        target_currencies = {"USD", "EUR", "RUB", "CNY"}

        # Дата курса
        rates_date = root.get("Date")

        for item in root.findall("./Currency"):
            code = item.get("ISOCode")
            rate_element = item.find("Value")

            if code in target_currencies and rate_element is not None:
                rate = float(rate_element.text.replace(",", "."))
                currency_rates[code] = rate

        usd_rate_krg = currency_rates["USD"]

        try:
            response_weekly = requests.get(weekly_url)
            response_weekly.raise_for_status()

            root = ET.fromstring(response_weekly.content)

            for item in root.findall("./Currency"):
                # Получаем ISOCode из атрибута Currency
                code = item.get("ISOCode")
                rate_element = item.find("Value")

                if code == "KRW":
                    krw_rate_krg = float(rate_element.text.replace(",", "."))
                    break
        except:
            print("Error...")

        rates_text = (
            f"Курс Валют Национального Банка Республики Кыргызстан ({rates_date}):\n\n"
            f"EUR: {currency_rates['EUR']:.2f} KGS\n"
            f"USD: {currency_rates['USD']:.2f} KGS\n"
            f"RUB: {currency_rates['RUB']:.2f} KGS\n"
            f"CNY: {currency_rates['CNY']:.2f} KGS\n"
        )

        return rates_text

    except requests.RequestException as e:
        print(f"Ошибка при подключении к НБКР API: {e}")
        return None
    except ET.ParseError as e:
        print(f"Ошибка при разборе XML: {e}")
        return None


# Курс валют для Казахстана
def get_nbk_currency_rates():
    print_message("[КУРС] КАЗАХСТАН")

    clear_memory()

    global usd_rate_kz, krw_rate_kz

    url = "https://nationalbank.kz/rss/rates_all.xml"

    try:
        # Запрос к API НБК
        response = requests.get(url)
        response.raise_for_status()

        # Парсинг XML-ответа
        root = ET.fromstring(response.content)

        # Словарь для хранения курсов валют
        currency_rates = {}

        # Валюты, которые нам нужны
        target_currencies = {"USD", "EUR", "KRW", "CNY"}

        # Дата курса
        rates_date = ""

        # Номиналы
        nominals = {}

        # Поиск нужных валют в XML-дереве
        for item in root.findall("./channel/item"):
            title = item.find("title").text  # Код валюты (например, "USD")
            description = item.find("description").text  # Курс к тенге
            rates_date = item.find("pubDate").text
            nominal = item.find("quant").text

            if title in target_currencies:
                # Сохранение курса в словарь, преобразуем курс в float
                currency_rates[title] = float(description)
                nominals[title] = float(nominal)

        usd_rate_kz = float(currency_rates["USD"])
        krw_rate_kz = float(currency_rates["KRW"]) / nominals["KRW"]

        rates_text = (
            f"Курс Валют Национального Банка Республики Казахстан ({rates_date}):\n\n"
            f"EUR: {currency_rates['EUR']:.2f} ₸\n"
            f"USD: {currency_rates['USD']:.2f} ₸\n"
            f"KRW: {currency_rates['KRW']:.2f} ₸\n"
            f"CNY: {currency_rates['CNY']:.2f} ₸\n"
        )

        return rates_text

    except requests.RequestException as e:
        print(f"Ошибка при подключении к НБК API: {e}")
        return None
    except ET.ParseError as e:
        print(f"Ошибка при разборе XML: {e}")
        return None


# Курс валют для России
def get_currency_rates():
    global krw_rub_rate, eur_rub_rate, usd_rub_rate

    print_message("[КУРС] РОССИЯ")

    url = "https://www.cbr-xml-daily.ru/daily_json.js"

    try:
        response = requests.get(url, timeout=5)  # Добавил timeout
        response.raise_for_status()  # Если статус код не 200, выбросит ошибку

        data = response.json()

        # Дата курса
        rates_date = datetime.datetime.now().strftime("%d.%m.%Y")

        # Проверяем, есть ли нужные ключи в JSON
        if "Valute" not in data or "USD" not in data["Valute"]:
            print("Ошибка: Данные о валюте отсутствуют!")
            return "Ошибка: Не удалось получить курс валют."

        # Получаем курсы валют
        eur_rate = data["Valute"]["EUR"]["Value"]
        usd_rate_local = data["Valute"]["USD"]["Value"] + 6
        krw_rate = data["Valute"]["KRW"]["Value"] / data["Valute"]["KRW"]["Nominal"]
        cny_rate = data["Valute"]["CNY"]["Value"]

        # Сохраняем в глобальные переменные для будущих расчётов
        krw_rub_rate = krw_rate
        eur_rub_rate = eur_rate
        usd_rub_rate = usd_rate_local + 6

        # Форматируем текст
        rates_text = (
            f"Курс валют ЦБ ({rates_date}):\n\n"
            f"EUR {eur_rate:.2f} ₽\n"
            f"USD {usd_rate_local:.2f} ₽\n"
            f"KRW {krw_rate:.2f} ₽\n"
            f"CNY {cny_rate:.2f} ₽"
        )

        return rates_text

    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return "Ошибка: Не удалось подключиться к серверу."


def send_error_message(message, error_text):
    global last_error_message_id

    # Проверяем наличие предыдущего сообщения об ошибке и пытаемся удалить его
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Ошибка при удалении предыдущего сообщения: {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при удалении сообщения: {e}")

    # Отправляем новое сообщение с ошибкой и сохраняем его ID
    try:
        error_message = bot.reply_to(message, error_text)
        last_error_message_id[message.chat.id] = error_message.id
        logging.error(f"Ошибка отправлена пользователю {message.chat.id}: {error_text}")
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(
            f"Ошибка при отправке сообщения пользователю {message.chat.id}: {e}"
        )
    except Exception as e:
        logging.error(
            f"Непредвиденная ошибка при отправке сообщения пользователю {message.chat.id}: {e}"
        )


def get_car_info(url):
    global car_id_external, vehicle_no, vehicle_id

    # driver = create_driver()

    car_id_match = re.findall(r"\d+", url)
    car_id = car_id_match[0]
    car_id_external = car_id

    url = f"https://api.encar.com/v1/readside/vehicle/{car_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "http://www.encar.com/",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
    }

    response = requests.get(url, headers=headers).json()

    # Получаем все необходимые данные по автомобилю
    car_price = str(response["advertisement"]["price"])
    car_date = response["category"]["yearMonth"]
    year = car_date[2:4]
    month = car_date[4:]
    car_engine_displacement = str(response["spec"]["displacement"])
    car_type = response["spec"]["bodyName"]

    # Для получения данных по страховым выплатам
    vehicle_no = response["vehicleNo"]
    vehicle_id = response["vehicleId"]

    # Форматируем
    formatted_car_date = f"01{month}{year}"
    formatted_car_type = "crossover" if car_type == "SUV" else "sedan"

    print_message(
        f"ID: {car_id}\nType: {formatted_car_type}\nDate: {formatted_car_date}\nCar Engine Displacement: {car_engine_displacement}\nPrice: {car_price} KRW"
    )

    # Сохранение данных в базу
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO car_info (car_id, date, engine_volume, price, car_type)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (car_id) DO NOTHING
        """,
        (
            car_id,
            formatted_car_date,
            car_engine_displacement,
            car_price,
            formatted_car_type,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
    print("Автомобиль был сохранён в базе данных")

    return [formatted_car_date, car_price, car_engine_displacement, formatted_car_type]


def calculate_cost(country, message):
    global car_data, car_id_external, util_fee, current_country, krw_rub_rate, eur_rub_rate, usd_rate_kz, usd_rate_krg, krw_rate_krg, usd_rate_krw, usd_rub_rate, usdt_rub_rate, usdt_krw_rate

    print_message("ЗАПРОС НА РАСЧЁТ АВТОМОБИЛЯ")

    # Сохраняем текущую страну что бы выводить детали расчёта
    current_country = country

    car_id = None
    car_date, car_engine_displacement, car_price, car_type = (
        None,
        None,
        None,
        None,
    )
    link = message.text

    # Проверяем, является ли ссылка ссылкой на kimsautotrade.com
    if "kimsautotrade.com/export-catalog/" in link:
        # Извлекаем ID автомобиля из ссылки на kimsautotrade
        car_id_match = re.findall(r"export-catalog/(\d+)", link)
        if car_id_match:
            car_id = car_id_match[0]
            car_id_external = car_id
            # Преобразуем ссылку в формат encar.com
            link = f"https://fem.encar.com/cars/detail/{car_id}"
        else:
            send_error_message(
                message,
                "🚫 Не удалось извлечь ID автомобиля из ссылки на kimsautotrade.com",
            )
            return
    # Проверка ссылки на мобильную версию
    elif "fem.encar.com" in link:
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            car_id_external = car_id
            link = f"https://fem.encar.com/cars/detail/{car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return
    else:
        # Извлекаем carid с URL encar
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]

    result = get_car_info(link)
    car_date, car_price, car_engine_displacement, car_type = result

    # Обработка ошибки получения данных
    if not car_date or not car_price or not car_engine_displacement:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Написать менеджеру Рамису", url="https://wa.me/821080296232"
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        bot.send_message(
            message.chat.id, car_title, parse_mode="HTML", reply_markup=keyboard
        )
        bot.delete_message(message.chat.id, processing_message.message_id)
        return

    # Если есть новая ссылка
    if car_price and car_date and car_engine_displacement:
        # Обработка расчёта для России
        if current_country == "Russia":
            print_message("Выполняется расчёт стоимости для России")

            year, month = 0, 0
            if len(car_date) > 6:
                year = int(f"20{re.sub(r"\D", "", car_date.split(" ")[0])}")
                month = int(re.sub(r"\D", "", car_date.split(" ")[1]))
            else:
                year = int(f"20{car_date[-2:]}")
                month = int(car_date[2:4])

            age = calculate_age(year, month)
            age_formatted = (
                "до 3 лет"
                if age == "0-3"
                else (
                    "от 3 до 5 лет"
                    if age == "3-5"
                    else "от 5 до 7 лет" if age == "5-7" else "от 7 лет"
                )
            )

            engine_volume_formatted = f"{format_number(car_engine_displacement)} cc"

            # Получаем курс USDT-KRW
            usdt_krw_rate = get_usdt_to_krw_rate_bithumb()
            # Получаем курс USDT-RUB
            usdt_rub_rate = get_usdt_to_rub_rate()

            usd_rate_krw = get_usd_to_krw_rate()
            price_krw = int(car_price) * 10000
            car_price_rub = price_krw * krw_rub_rate

            response = get_customs_fees_russia(
                car_engine_displacement, price_krw, year, month, engine_type=1
            )

            # Таможенный сбор
            customs_fee = clean_number(response["sbor"])

            # Таможенная пошлина
            customs_duty = clean_number(response["tax"])

            # Рассчитываем утилизационный сбор
            recycling_fee = clean_number(response["util"])

            excise = (
                2040000
                if int(car_engine_displacement) < 2000
                else 2040000 + (200 * usd_rate_krw)
            )

            total_korea_costs = price_krw + excise

            # Расчеты в USDT
            total_korea_costs_usdt = total_korea_costs / usdt_krw_rate

            total_korea_costs_usd = total_korea_costs / usd_rate_krw
            total_korea_costs_rub = total_korea_costs_usd * usd_rub_rate

            total_russia_costs = (
                customs_duty + recycling_fee + customs_fee + 120000 + 250000
            )
            total_russia_costs_usdt = (
                customs_duty + recycling_fee + customs_fee + 120000 + 250000
            ) / usdt_rub_rate

            total_cost = total_korea_costs_rub + total_russia_costs

            total_cost_usdt = total_korea_costs_usdt + total_russia_costs_usdt
            total_cost_usdt_rub = (
                total_korea_costs_usdt + total_russia_costs_usdt
            ) * usdt_rub_rate

            car_data["price_rub"] = car_price_rub
            car_data["duty"] = customs_fee
            car_data["recycling_fee"] = recycling_fee
            car_data["total_price"] = total_cost
            car_data["customs_duty_fee"] = customs_duty

            preview_link = f"https://fem.encar.com/cars/detail/{car_id}"

            # Формирование сообщения результата
            result_message = (
                f"Возраст: {age_formatted}\n"
                f"Объём двигателя: {engine_volume_formatted}\n\n"
                # f"Примерная стоимость автомобиля под ключ до Владивостока: \n<b>{format_number(total_cost)} ₽</b>\n\n"
                f"<b>Расходы по Корее</b>:\n"
                f"Стоимость автомобиля + акциза (инвойс):\n{format_number(total_korea_costs)} ₩ | ${format_number(total_korea_costs_usd)} | {format_number(total_korea_costs_rub)} ₽\n\n"
                f"Стоимость автомобиля + акциза (USDT):\n${format_number(total_korea_costs_usdt)}\n\n"
                f"Расходы по России:\n"
                f"Таможенные платежи (ЕТС, пошлина, утильсбор) + Услуги Брокера + Автовоз:\n{format_number(total_russia_costs)} ₽\n\n"
                f"<b>Итого стоимость автомобиля под ключ (инвойс)</b>:\n{format_number(total_cost)} ₽\n\n"
                f"<b>Итого стоимость автомобиля под ключ (USDT)</b>:\n${format_number(total_cost_usdt)} | {format_number(total_cost_usdt_rub)} ₽\n\n"
                f"🔗 <a href='{preview_link}'>Ссылка на автомобиль</a>\n\n"
                "Если данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у нашего менеджера:\nРамис - +82 10-8029-6232\n\n"
                "🔗 <a href='https://t.me/avtokoreaRF'>Официальный телеграм канал</a>\n"
            )

            # Клавиатура с дальнейшими действиями
            keyboard = types.InlineKeyboardMarkup()
            # keyboard.add(
            #     types.InlineKeyboardButton(
            #         "📊 Детализация расчёта", callback_data="detail"
            #     )
            # )
            keyboard.add(
                types.InlineKeyboardButton(
                    "📝 Технический отчёт об автомобиле",
                    callback_data="technical_report",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "✉️ Связаться с менеджером Рамисом", url="https://wa.me/821080296232"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "🔍 Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )

            bot.send_message(
                message.chat.id,
                result_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        elif current_country == "Kazakhstan":
            print_message("Выполняется расчёт стоимости для Казахстана")

            # Получаем курс USDT-KRW
            usdt_krw_rate = get_usdt_to_krw_rate_bithumb()

            usd_rate_krw = get_usd_to_krw_rate()

            # Определение года и месяца выпуска авто
            year, month = 0, 0
            if len(car_date) > 6:
                year = int(f"20{re.sub(r'\D', '', car_date.split(' ')[0])}")
                month = int(re.sub(r"\D", "", car_date.split(" ")[1]))
            else:
                year = int(f"20{car_date[-2:]}")
                month = int(car_date[2:4])

            # Конвертация стоимости авто в тенге (KZT)
            car_price_krw = int(car_price) * 10000
            car_price_kzt = car_price_krw * krw_rate_kz

            # Логистика и документация в Корее (KZT)
            korea_container_usd = 1900
            korea_container_kzt = korea_container_usd * usd_rate_kz

            korea_transfer_usd = 440000 / usd_rate_krw
            korea_transfer_kzt = korea_transfer_usd * usd_rate_kz

            korea_documentation_usd = 150000 / usd_rate_krw
            korea_documentation_kzt = korea_documentation_usd * usd_rate_kz

            total_korea_kzt = (
                korea_container_kzt + korea_transfer_kzt + korea_documentation_kzt
            )

            # Таможенные платежи
            customs_fee_kzt = car_price_kzt * 0.15
            excise_fee_kzt = (
                int(car_engine_displacement) * 100
                if int(car_engine_displacement) >= 3000
                else 0
            )
            vat_kzt = (car_price_kzt + 20000 + excise_fee_kzt) * 0.12

            # Утильсбор (KZT)
            if 1001 <= int(car_engine_displacement) <= 2000:
                utilization_fee_kzt = 603750
            elif 2001 <= int(car_engine_displacement) <= 3000:
                utilization_fee_kzt = 862500
            else:
                utilization_fee_kzt = 1983750

            # Регистрационный сбор (KZT)
            current_year = datetime.datetime.now().year
            if current_year - year > 3:
                registration_fee_kzt = 1725000
            elif current_year - year < 2:
                registration_fee_kzt = 863
            else:
                registration_fee_kzt = 172500

            # Общие расходы
            total_customs_kzt = customs_fee_kzt + vat_kzt + excise_fee_kzt
            total_expenses_kzt = (
                total_customs_kzt + utilization_fee_kzt + registration_fee_kzt
            )

            # Итоговая стоимость авто в тенге (KZT)
            final_cost_kzt = car_price_kzt + total_expenses_kzt + total_korea_kzt
            final_cost_usd = final_cost_kzt / usd_rate_kz

            # Добавляем расчет в USDT
            car_price_krw = int(car_price) * 10000
            car_price_usdt = car_price_krw / usdt_krw_rate
            final_cost_usdt = final_cost_kzt / (
                usd_rate_kz * usdt_krw_rate / usd_rate_krw
            )

            car_data["korea_container_kzt"] = korea_container_kzt
            car_data["korea_transfer_kzt"] = korea_transfer_kzt
            car_data["korea_documentation_kzt"] = korea_documentation_kzt
            car_data["price_kzt"] = car_price_kzt
            car_data["customs_fee_kzt"] = customs_fee_kzt
            car_data["vat_kzt"] = vat_kzt
            car_data["excise_fee_kzt"] = excise_fee_kzt
            car_data["utilization_fee_kzt"] = utilization_fee_kzt
            car_data["registration_fee_kzt"] = registration_fee_kzt
            car_data["total_customs_kzt"] = total_customs_kzt
            car_data["total_expenses_kzt"] = total_expenses_kzt
            car_data["final_cost_kzt"] = final_cost_kzt
            car_data["final_cost_usd"] = final_cost_usd
            car_data["final_cost_usdt"] = final_cost_usdt

            # Форматирование сообщения с расчётом
            result_message = (
                f"🚗 <b>Расчёт стоимости автомобиля для Казахстана</b>\n\n"
                f"📆 Год выпуска: {year}/{month}\n"
                f"🔧 Объём двигателя: {format_number(car_engine_displacement)} cc\n"
                f"💰 Стоимость авто в Корее: {format_number(car_price_krw)} ₩\n\n"
                f"📦 <b>Расходы в Корее:</b>\n"
                f"- Транспортировка: {format_number(korea_transfer_kzt)} ₸\n"
                f"- Документы: {format_number(korea_documentation_kzt)} ₸\n"
                f"- Логистика (контейнер): {format_number(korea_container_kzt)} ₸\n"
                f"🔹 Всего в Корее: {format_number(total_korea_kzt)} ₸\n\n"
                f"📑 <b>Таможенные платежи:</b>\n"
                f"- Таможенная пошлина (15%): {format_number(customs_fee_kzt)} ₸\n"
                f"- Акцизный сбор: {format_number(excise_fee_kzt)} ₸\n"
                f"- НДС (12%): {format_number(vat_kzt)} ₸\n"
                f"🔹 Всего таможенных платежей: {format_number(total_customs_kzt)} ₸\n\n"
                f"🛠 <b>Дополнительные расходы:</b>\n"
                f"- Утилизационный сбор: {format_number(utilization_fee_kzt)} ₸\n"
                f"- Регистрационный сбор: {format_number(registration_fee_kzt)} ₸\n"
                f"🔹 Всего расходов: {format_number(total_expenses_kzt)} ₸\n\n"
                f"💲 <b>Итоговая стоимость автомобиля под ключ:</b>\n"
                f"🇰🇿 В тенге: <b>{format_number(final_cost_kzt)} ₸</b>\n"
                f"💵 В долларах: <b>{format_number(final_cost_usd)} $</b>\n"
                f"💎 В USDT: <b>{format_number(final_cost_usdt)} USDT</b>\n\n"
                f"🔗 <a href='https://fem.encar.com/cars/detail/{car_id}'>Ссылка на автомобиль</a>\n"
            )

            # Клавиатура с дальнейшими действиями
            keyboard = types.InlineKeyboardMarkup()
            # keyboard.add(
            #     types.InlineKeyboardButton(
            #         "📊 Детализация расчёта", callback_data="detail"
            #     )
            # )
            keyboard.add(
                types.InlineKeyboardButton(
                    "📝 Технический отчёт об автомобиле",
                    callback_data="technical_report",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "✉️ Связаться с менеджером", url="https://wa.me/821080296232"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "🔍 Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )

            bot.send_message(
                message.chat.id,
                result_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        elif current_country == "Kyrgyzstan":
            print_message("Выполняется расчёт стоимости для Кыргызстана")

            # Получаем курс USDT-KRW
            usdt_krw_rate = get_usdt_to_krw_rate_bithumb()

            # Конвертируем цену в KGS
            car_price_krw = int(car_price) * 10000
            price_kgs = car_price_krw * krw_rate_krg

            # Рассчитываем таможенную пошлину
            if len(car_date) > 6:
                car_year = int(f"20{re.sub(r"\D", "", car_date.split(" ")[0])}")
            else:
                car_year = int(f"20{car_date[-2:]}")

            customs_fee_kgs_usd = calculate_customs_fee_kg(
                car_engine_displacement, car_year
            )

            customs_fee_kgs = customs_fee_kgs_usd * usd_rate_krg

            # Брокерские услуги
            broker_fee = 100000

            # Доставка (в зависимости от типа авто)
            if car_type == "sedan":
                delivery_fee = 2400 * usd_rate_krg
            elif car_type == "crossover":
                delivery_fee = 2500 * usd_rate_krg
            else:
                delivery_fee = 2600 * usd_rate_krg

            # Полная стоимость
            total_cost_kgs = (
                price_kgs + customs_fee_kgs + delivery_fee + (440000 * krw_rate_krg)
            )

            # Добавляем расчет в USDT
            car_price_krw = int(car_price) * 10000
            total_cost_usdt = total_cost_kgs / usd_rate_krg

            car_data["price_kgs"] = price_kgs
            car_data["customs_fee_kgs"] = customs_fee_kgs
            car_data["delivery_fee_kgs"] = delivery_fee
            car_data["total_price_kgs"] = total_cost_kgs
            car_data["total_cost_usdt"] = total_cost_usdt

            year, month = 0, 0
            if len(car_date) > 6:
                year = int(f"20{re.sub(r"\D", "", car_date.split(" ")[0])}")
                month = int(re.sub(r"\D", "", car_date.split(" ")[1]))
            else:
                year = int(f"20{car_date[-2:]}")
                month = int(car_date[2:4])

            age = calculate_age(year, month)
            age_formatted = (
                "до 3 лет"
                if age == "0-3"
                else (
                    "от 3 до 5 лет"
                    if age == "3-5"
                    else "от 5 до 7 лет" if age == "5-7" else "от 7 лет"
                )
            )
            engine_volume_formatted = f"{format_number(car_engine_displacement)} cc"

            preview_link = f"https://fem.encar.com/cars/detail/{car_id}"

            # Формирование сообщения результата
            result_message = (
                f"Возраст: {age_formatted}\n"
                f"Стоимость автомобиля в Корее: {format_number(car_price_krw)} ₩\n"
                f"Объём двигателя: {engine_volume_formatted}\n\n"
                f"Примерная стоимость автомобиля под ключ до Бишкека: \n<b>{format_number(total_cost_kgs)} KGS</b>\n"
                f"В USDT: <b>{format_number(total_cost_usdt)} USDT</b>\n\n"
                f"🔗 <a href='{preview_link}'>Ссылка на автомобиль</a>\n\n"
                "Если данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у нашего менеджера:\nРамис - +82 10-8029-6232\n\n"
                "🔗 <a href='https://t.me/avtokoreaRF'>Официальный телеграм канал</a>\n"
            )

            # Клавиатура с дальнейшими действиями
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "📊 Детализация расчёта", callback_data="detail"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "📝 Технический отчёт об автомобиле",
                    callback_data="technical_report",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "✉️ Связаться с менеджером Рамисом", url="https://wa.me/821080296232"
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "🔍 Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )

            bot.send_message(
                message.chat.id,
                result_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            time.sleep(3)

        else:
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
            bot.delete_message(message.chat.id, processing_message.message_id)


def get_insurance_total():
    global car_id_external, vehicle_no, vehicle_id

    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")

    formatted_vehicle_no = urllib.parse.quote(str(vehicle_no).strip())
    url = f"https://api.encar.com/v1/readside/record/vehicle/{str(vehicle_id)}/open?vehicleNo={formatted_vehicle_no}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "http://www.encar.com/",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
        }

        response = requests.get(url, headers)
        json_response = response.json()

        # Форматируем данные
        damage_to_my_car = json_response["myAccidentCost"]
        damage_to_other_car = json_response["otherAccidentCost"]

        print(
            f"Выплаты по представленному автомобилю: {format_number(damage_to_my_car)}"
        )
        print(f"Выплаты другому автомобилю: {format_number(damage_to_other_car)}")

        return [format_number(damage_to_my_car), format_number(damage_to_other_car)]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return ["Ошибка при получении данных", ""]


# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global car_data, car_id_external, current_country, usd_rate_kz, krw_rate_krg

    if call.data.startswith("detail"):
        detail_message = ""

        if current_country == "Russia":
            print_message("[РОССИЯ] ДЕТАЛИЗАЦИЯ РАСЧËТА")

            # Construct cost breakdown message
            detail_message = (
                "📝 Детализация расчёта:\n\n"
                f"Стомость автомобиля: {format_number(car_data['price_rub'])} ₽\n\n"
                f"Таможенный cбор: {format_number(car_data['duty'])} ₽\n\n"
                f"Таможенная пошлина: {format_number(car_data['customs_duty_fee'])} ₽\n\n"
                f"Утилизационный сбор: {format_number(car_data['recycling_fee'])} ₽\n\n"
                # f"Акциза: {format_number(car_data['excise'])} ₽\n\n"
                f"Логистика до Владивостока: 110,000 ₽\n\n"
                f"Услуги брокера: 120,000 ₽\n\n"
                f"<b>Итоговая стоимость автомобиля: {format_number(car_data['total_price'])} ₽</b>\n\n"
                f"<b>ПРИМЕЧАНИЕ: ЦЕНА НА АВТОМОБИЛЬ ЗАВИСИТ ОТ ТЕКУЩЕГО КУРСА, ДЛЯ БОЛЕЕ ТОЧНОЙ ИНФОРМАЦИИ НАПИШИТЕ НАШЕМУ МЕНЕДЖЕРУ +82-10-8029-6232</b>"
            )

        if current_country == "Kazakhstan":
            print_message("[КАЗАХСТАН] ДЕТАЛИЗАЦИЯ РАСЧËТА")

            detail_message = (
                "📝 Детализация расчёта:\n\n"
                f"Стоимость авто: <b>{format_number(car_data['price_kzt'])} ₸</b>\n\n"
                f"НДС (12%): <b>{format_number(car_data['vat_kzt'])} ₸</b>\n\n"
                f"Таможенная пошлина: <b>{format_number(car_data['customs_fee_kzt'])} ₸</b>\n\n"
                f"Таможенная декларация: <b>{format_number(car_data['customs_declaration_fee_kzt'])} ₸</b>\n\n"
                f"Утильсбор: <b>{format_number(car_data['utilization_fee_kzt'])} ₸</b>\n\n"
                f"Первичная регистрация: <b>{format_number(car_data['first_registration_fee_kzt'])} ₸</b>\n\n"
                f"Акциз: <b>{format_number(car_data['excise_fee_kzt'])} ₸</b>\n\n"
                f"Итоговая стоимость под ключ до Алматы: <b>{format_number(car_data['total_price_kzt'])} ₸</b>\n\n"
                f"<b>ПРИМЕЧАНИЕ: ЦЕНА НА АВТОМОБИЛЬ ЗАВИСИТ ОТ ТЕКУЩЕГО КУРСА, ДЛЯ БОЛЕЕ ТОЧНОЙ ИНФОРМАЦИИ НАПИШИТЕ НАШЕМУ МЕНЕДЖЕРУ +82-10-8029-6232 (Рамис)</b>"
            )

        if current_country == "Kyrgyzstan":
            print_message("[КЫРГЫЗСТАН] ДЕТАЛИЗАЦИЯ РАСЧËТА")

            detail_message = (
                "📝 Детализация расчёта:\n\n"
                f"Стоимость авто в сомах: <b>{format_number(car_data['price_kgs'])} KGS</b>\n\n"
                f"Услуги KimsAutoTrade: <b>{format_number(440000 * krw_rate_krg)} KGS</b>\n\n"
                f"Таможенная пошлина: <b>{format_number(car_data['customs_fee_kgs'])}</b> KGS\n\n"
                f"Доставка до Бишкека: <b>{format_number(car_data['delivery_fee_kgs'])}</b> KGS\n\n"
                f"Общая стоимость автомобиля под ключ до Бишкека: \n<b>{format_number(car_data["total_price_kgs"])} KGS</b>\n\n"
                f"<b>ПРИМЕЧАНИЕ: ЦЕНА НА АВТОМОБИЛЬ ЗАВИСИТ ОТ ТЕКУЩЕГО КУРСА, ДЛЯ БОЛЕЕ ТОЧНОЙ ИНФОРМАЦИИ НАПИШИТЕ НАШЕМУ МЕНЕДЖЕРУ +82-10-8029-6232 (Рамис)</b>"
            )

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Связаться с менеджером Рамисом", url="https://wa.me/821080296232"
            )
        )

        bot.send_message(
            call.message.chat.id,
            detail_message,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    elif call.data == "technical_report":
        bot.send_message(
            call.message.chat.id,
            "Получаем технический отчёт об автомобиле. Пожалуйста подождите ⏳",
        )

        # Retrieve insurance information
        insurance_info = get_insurance_total()

        # Проверка на наличие ошибки
        if "Ошибка" in insurance_info[0] or "Ошибка" in insurance_info[1]:
            error_message = (
                "Страховая история недоступна. \n\n"
                f'<a href="https://fem.encar.com/cars/detail/{car_id_external}">🔗 Ссылка на автомобиль 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/MANAGER"
                )
            )

            # Отправка сообщения об ошибке
            bot.send_message(
                call.message.chat.id,
                error_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            current_car_insurance_payments = (
                "0" if len(insurance_info[0]) == 0 else insurance_info[0]
            )
            other_car_insurance_payments = (
                "0" if len(insurance_info[1]) == 0 else insurance_info[1]
            )

            # Construct the message for the technical report
            tech_report_message = (
                f"Страховые выплаты по представленному автомобилю: \n<b>{current_car_insurance_payments} ₩</b>\n\n"
                f"Страховые выплаты другим участникам ДТП: \n<b>{other_car_insurance_payments} ₩</b>\n\n"
                f'<a href="https://fem.encar.com/cars/report/inspect/{car_id_external}">🔗 Ссылка на схему повреждений кузовных элементов 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/MANAGER"
                )
            )

            bot.send_message(
                call.message.chat.id,
                tech_report_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    elif call.data == "calculate_another":
        show_country_selection(call.message.chat.id)


# Расчёты для ручного ввода
def calculate_cost_manual(country, year, month, engine_volume, price, car_type):
    global eur_rub_rate, usdt_krw_rate, usdt_rub_rate

    if country == "Russia":
        print_message("Выполняется ручной расчёт стоимости для России")

        # Получаем курс USDT-KRW и USDT-RUB
        usdt_krw_rate = get_usdt_to_krw_rate_bithumb()
        usdt_rub_rate = get_usdt_to_rub_rate()
        usd_rate_krw = get_usd_to_krw_rate()

        # Конвертируем стоимость авто в рубли
        price_krw = int(price)
        car_price_rub = price_krw * krw_rub_rate

        response = get_customs_fees_russia(
            engine_volume, price_krw, year, month, engine_type=1
        )
        customs_duty = clean_number(response["tax"])
        customs_fee = clean_number(response["sbor"])
        recycling_fee = clean_number(response["util"])

        # Рассчитываем акциз
        excise = (
            2040000 if int(engine_volume) < 2000 else 2040000 + (200 * usd_rate_krw)
        )

        # Расходы в Корее
        total_korea_costs = price_krw + excise
        total_korea_costs_usdt = total_korea_costs / usdt_krw_rate
        total_korea_costs_usd = total_korea_costs / usd_rate_krw
        total_korea_costs_rub = total_korea_costs_usd * usd_rub_rate

        # Расходы в России
        total_russia_costs = (
            customs_duty + recycling_fee + customs_fee + 120000 + 250000
        )
        total_russia_costs_usdt = total_russia_costs / usdt_rub_rate

        # Итоговая стоимость
        total_cost = total_korea_costs_rub + total_russia_costs
        total_cost_usdt = total_korea_costs_usdt + total_russia_costs_usdt
        total_cost_usdt_rub = total_cost_usdt * usdt_rub_rate

        result_message = (
            f"Расчёты для автомобиля:\n\n"
            f"Дата: <i>{str(year)}/{str(month)}</i>\nОбъём: <b>{format_number(engine_volume)} cc</b>\nЦена в Корее: <b>{format_number(price)} ₩</b>\n\n"
            f"<b>Расходы по Корее</b>:\n"
            f"Стоимость автомобиля + акциза (инвойс):\n{format_number(total_korea_costs)} ₩ | ${format_number(total_korea_costs_usd)} | {format_number(total_korea_costs_rub)} ₽\n\n"
            f"Стоимость автомобиля + акциза (USDT):\n${format_number(total_korea_costs_usdt)}\n\n"
            f"<b>Расходы по России</b>:\n"
            f"Таможенные платежи (ЕТС, пошлина, утильсбор) + Услуги Брокера + Автовоз:\n{format_number(total_russia_costs)} ₽\n\n"
            f"<b>Итого стоимость автомобиля под ключ (инвойс)</b>:\n{format_number(total_cost)} ₽\n\n"
            f"<b>Итого стоимость автомобиля под ключ (USDT)</b>:\n${format_number(total_cost_usdt)} | {format_number(total_cost_usdt_rub)} ₽\n\n"
            f"Цены могут варьироваться в зависимости от курса, для более подробной информации пишите +82-10-8029-6232"
        )

        return result_message
    elif country == "Kazakhstan":
        print_message("Выполняется ручной расчёт стоимости для Казахстана")

        # Получаем курс USDT-KRW
        usdt_krw_rate = get_usdt_to_krw_rate_bithumb()
        usd_rate_krw = get_usd_to_krw_rate()

        # Конвертируем цену авто в тенге
        car_price_krw = int(price)
        car_price_kzt = car_price_krw * krw_rate_kz

        # НДС (12%)
        vat_kzt = car_price_kzt * 0.12

        # Таможенная пошлина (15%)
        customs_fee_kzt = car_price_kzt * 0.15

        # Таможенная декларация
        customs_declaration_fee_kzt = 25152

        # Утильсбор
        engine_volume_int = int(engine_volume)
        base_utilization_fee_kzt = 200000  # Базовая ставка

        # Определяем коэффициент
        if engine_volume_int <= 1000:
            coefficient = 0.5
        elif engine_volume_int <= 2000:
            coefficient = 1.0
        elif engine_volume_int <= 3000:
            coefficient = 2.0
        elif engine_volume_int <= 4000:
            coefficient = 3.0
        else:
            coefficient = 4.0

        # Рассчитываем утильсбор
        utilization_fee_kzt = base_utilization_fee_kzt * coefficient

        # Акцизный сбор
        excise_fee_kzt = (
            (engine_volume_int - 3000) * 100 if engine_volume_int > 3000 else 0
        )

        # Услуги Kims Auto Trade
        kims_auto_trade_fees_kzt = 450000 * krw_rate_kz

        # Услуги брокера
        broker_fee_kzt = 100000

        # Доставка (логистика по Корее + до Алматы)
        delivery_fee_kzt = 2500 * usd_rate_kz
        fraht_fee_kzt = 500 * usd_rate_kz

        # Сертификация (СБКТС)
        sbkts_fee_kzt = 60000

        # Расчет первичной регистрации
        mpr = 3932  # Минимальный расчетный показатель в тенге на 2025 год

        if year >= datetime.datetime.now().year - 2:
            registration_fee_kzt = 0.25 * mpr  # До 2 лет
        elif year >= datetime.datetime.now().year - 3:
            registration_fee_kzt = 50 * mpr  # От 2 до 3 лет
        else:
            registration_fee_kzt = 500 * mpr  # Старше 3 лет

        # Итоговая стоимость
        total_cost_kzt = (
            car_price_kzt
            + vat_kzt
            + customs_fee_kzt
            + customs_declaration_fee_kzt
            + excise_fee_kzt
            + kims_auto_trade_fees_kzt
            + broker_fee_kzt
            + delivery_fee_kzt
            + fraht_fee_kzt
            + sbkts_fee_kzt
            + utilization_fee_kzt
            + registration_fee_kzt
        )

        # Расчет в USDT и USD
        total_cost_usd = total_cost_kzt / usd_rate_kz
        total_cost_usdt = total_cost_kzt / (usd_rate_kz * usdt_krw_rate / usd_rate_krw)

        result_message = (
            f"Расчёты для автомобиля:\n\n"
            f"Дата: <i>{str(year)}/{str(month)}</i>\nОбъём: <b>{format_number(engine_volume)} cc</b>\nЦена в Корее: <b>{format_number(price)} ₩</b>\n"
            f"Под ключ до Алматы:\n"
            f"<b>{format_number(total_cost_kzt)} ₸</b>\n"
            f"<b>{format_number(total_cost_usd)} $</b>\n"
            f"<b>{format_number(total_cost_usdt)} USDT</b>\n\n"
            f"Цены могут варьироваться в зависимости от курса, для более подробной информации пишите +82-10-8029-6232"
        )

        return result_message
    elif country == "Kyrgyzstan":
        print_message("Выполняется ручной расчёт стоимости для Кыргызстана")

        # Получаем курс USDT-KRW
        usdt_krw_rate = get_usdt_to_krw_rate_bithumb()

        # Расчеты в KGS
        price_kgs = int(price) * krw_rate_krg
        customs_fee_kgs_usd = calculate_customs_fee_kg(engine_volume, year)
        customs_fee_kgs = customs_fee_kgs_usd * usd_rate_krg

        # Доставка в зависимости от типа авто
        if car_type == "sedan":
            delivery_fee = 2400 * usd_rate_krg
        elif car_type == "crossover":
            delivery_fee = 2500 * usd_rate_krg
        else:
            delivery_fee = 2600 * usd_rate_krg

        # Полная стоимость
        total_cost_kgs = (
            price_kgs + customs_fee_kgs + delivery_fee + (440000 * krw_rate_krg)
        )

        # Расчет в USDT
        total_cost_usdt = total_cost_kgs / usd_rate_krg

        result_message = (
            f"Расчёты для автомобиля:\n\n"
            f"Дата: <i>{str(year)}/{str(month)}</i>\nОбъём: <b>{format_number(engine_volume)} cc</b>\nЦена в Корее: <b>{format_number(price)} ₩</b>\n"
            f"Под ключ до Бишкека:\n"
            f"<b>{format_number(total_cost_kgs)} KGS</b>\n"
            f"<b>{format_number(total_cost_usdt)} USDT</b>\n\n"
            f"Цены могут варьироваться в зависимости от курса, для более подробной информации пишите +82-10-8029-6232"
        )

        return result_message
    else:
        return "🚫 Неизвестная страна."
