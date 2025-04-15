import locale
import threading
import re

from telebot import types
from calculator import (
    calculate_cost,
    get_currency_rates,
    show_country_selection,
    get_nbk_currency_rates,
    get_nbkr_currency_rates,
    calculate_cost_manual,
)
from config import bot


# Переменные
user_data = {}
current_country = "Russia"
current_car_type = "sedan"

# Set locale for number formatting
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


# Обработчик callback
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global current_car_type, current_country

    user_id = call.message.chat.id

    if call.data == "calculate_another":
        # Сбрасываем данные пользователя
        user_data[user_id] = {}
        current_country = None
        current_car_type = None

        show_country_selection(user_id)
    elif call.data == "main_menu":
        main_menu(call.message)


# Функция для установки команд меню
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("cbr", "Курс ЦБ Российской Федерации"),
        types.BotCommand("nbk", "Курс Национального Банка Республики Казахстан"),
        types.BotCommand("nbkr", "Курс Национального Банка Республики Кыргызстан"),
    ]
    bot.set_my_commands(commands)


@bot.message_handler(commands=["nbkr"])
def nbkr_command(message):
    try:
        rates_text = get_nbkr_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(message.chat.id, rates_text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


@bot.message_handler(commands=["nbk"])
def nbk_command(message):
    try:
        rates_text = get_nbk_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(message.chat.id, rates_text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


@bot.message_handler(commands=["cbr"])
def cbr_command(message):
    try:
        rates_text = get_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "🔍 Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(message.chat.id, rates_text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


# Самый старт
@bot.message_handler(commands=["start"])
def start(message):
    user_name = message.from_user.first_name

    # Отправляем логотип компании
    bot.send_photo(
        message.chat.id,
        "https://res.cloudinary.com/pomegranitedesign/image/upload/v1739951461/kimsautotrade/logo.jpg",
    )

    # Приветственное сообщение
    greeting = f"👋 Здравствуйте, {user_name}!\n Я бот компании Kims Auto Trade для расчёта стоимости авто из Южной Кореи до стран СНГ! 🚗 \n\n💰 Пожалуйста, выберите действие из меню ниже:"

    # Создание кнопочного меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_calc = types.KeyboardButton("Расчёт")
    btn_instagram = types.KeyboardButton("Instagram")
    btn_whatsapp = types.KeyboardButton("WhatsApp")
    btn_telegram = types.KeyboardButton("Telegram-канал")
    btn_manager = types.KeyboardButton("Контакты")

    # Добавление кнопок в меню
    markup.add(btn_calc, btn_instagram, btn_whatsapp, btn_telegram, btn_manager)

    # Отправка приветствия с кнопочным меню
    bot.send_message(message.chat.id, greeting, reply_markup=markup)


# Главное меню
@bot.message_handler(func=lambda message: message.text == "Вернуться в главное меню")
def main_menu(message):
    user_id = message.chat.id

    user_data[user_id] = {}

    # Приветственное сообщение
    user_name = message.from_user.first_name
    greeting = f"Здравствуйте, {user_name}!\n Я бот компании Kims Auto Trade для расчёта стоимости авто из Южной Кореи до стран СНГ! 🚗 \n\n💰 Пожалуйста, выберите действие из меню ниже:"

    # Создание кнопочного меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_calc = types.KeyboardButton("Расчёт")
    btn_instagram = types.KeyboardButton("Instagram")
    btn_whatsapp = types.KeyboardButton("WhatsApp")
    btn_telegram = types.KeyboardButton("Telegram-канал")
    btn_manager = types.KeyboardButton("Контакты")

    # Добавление кнопок в меню
    markup.add(btn_calc, btn_instagram, btn_whatsapp, btn_telegram, btn_manager)

    # Отправка приветствия с кнопочным меню
    bot.send_message(message.chat.id, greeting, reply_markup=markup)


# Выбор страны для расчёта
@bot.message_handler(func=lambda message: message.text in ["Расчёт", "Изменить страну"])
def handle_calculation(message):
    show_country_selection(message.chat.id)


# Расчёт по ссылке с encar или kimsautotrade
@bot.message_handler(func=lambda message: message.text.startswith("http"))
def process_encar_link(message):
    # Проверяем, выбрана ли страна
    if message.chat.id not in user_data or "country" not in user_data[message.chat.id]:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите страну из меню перед отправкой ссылки на автомобиль.",
        )
        # Сразу показываем меню выбора страны
        show_country_selection(message.chat.id)
        return

    original_link = message.text
    link = original_link

    # Проверяем, является ли ссылка ссылкой на kimsautotrade.com
    if "kimsautotrade.com/export-catalog/" in link:
        # Извлекаем ID автомобиля из ссылки на kimsautotrade
        car_id_match = re.findall(r"export-catalog/(\d+)", link)
        if car_id_match:
            car_id = car_id_match[0]
            # Преобразуем ссылку в формат encar.com
            link = f"https://fem.encar.com/cars/detail/{car_id}"
        else:
            bot.send_message(
                message.chat.id,
                "🚫 Не удалось извлечь ID автомобиля из ссылки на kimsautotrade.com",
            )
            return
    # Проверяем, что ссылка содержит encar.com или fem.encar.com
    elif "encar.com" not in link and "fem.encar.com" not in link:
        bot.send_message(
            message.chat.id,
            "🚫 Введите корректную ссылку с kimsautotrade.com или encar.com",
        )
        return

    # Получаем выбранную страну
    country = user_data[message.chat.id]["country"]

    # Отправляем сообщение о начале обработки
    processing_message = bot.send_message(message.chat.id, "⏳ Обработка данных...")

    # Пытаемся рассчитать стоимость
    try:
        calculate_cost(country, message)
    except Exception as e:
        bot.send_message(
            message.chat.id,
            "🚫 Произошла ошибка при расчёте. Пожалуйста, попробуйте снова.",
        )
        print(f"Ошибка при расчёте: {e}")
    finally:
        # Удаляем сообщение о процессе
        bot.delete_message(message.chat.id, processing_message.message_id)


@bot.message_handler(func=lambda message: message.text == "По ссылке с encar")
def handle_link_input(message):
    bot.send_message(
        message.chat.id,
        "Отправьте ссылку на автомобиль с сайта kimsautotrade.com или encar.com",
    )


###############
# РОССИЯ НАЧАЛО
###############
@bot.message_handler(func=lambda message: message.text == "🇷🇺 Россия")
def handle_russia(message):
    global current_country

    current_country = "Russia"
    user_data[message.chat.id] = {"country": "Russia"}
    print(f"Сохранена страна: {user_data[message.chat.id]['country']}")  # Логирование

    # Создаем клавиатуру с кнопкой для возврата в главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_main_menu = types.KeyboardButton("Вернуться в главное меню")
    markup.add(btn_main_menu)

    # Просим пользователя отправить ссылку на автомобиль
    bot.send_message(
        message.chat.id,
        "Отправьте ссылку на автомобиль с сайта kimsautotrade.com или encar.com:",
        reply_markup=markup,
    )


###############
# РОССИЯ КОНЕЦ
###############


##############
# КАЗАХСТАН НАЧАЛО
##############
@bot.message_handler(func=lambda message: message.text == "🇰🇿 Казахстан")
def handle_kazakhstan(message):
    global current_country
    current_country = "Kazakhstan"
    user_data[message.chat.id] = {"country": "Kazakhstan"}
    print(f"Сохранена страна: {user_data[message.chat.id]['country']}")  # Логирование

    # Создаем клавиатуру с кнопкой для возврата в главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_main_menu = types.KeyboardButton("Вернуться в главное меню")
    markup.add(btn_main_menu)

    # Просим пользователя отправить ссылку на автомобиль
    bot.send_message(
        message.chat.id,
        "Отправьте ссылку на автомобиль с сайта kimsautotrade.com или encar.com:",
        reply_markup=markup,
    )


##############
# КАЗАХСТАН КОНЕЦ
##############


##############
# КЫРГЫЗСТАН НАЧАЛО
##############
@bot.message_handler(func=lambda message: message.text == "🇰🇬 Кыргызстан")
def handle_kyrgyzstan(message):
    global current_country

    current_country = "Kyrgyzstan"
    user_data[message.chat.id] = {"country": "Kyrgyzstan"}
    print(f"Сохранена страна: {user_data[message.chat.id]['country']}")  # Логирование

    # Создаем клавиатуру с кнопкой для возврата в главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_main_menu = types.KeyboardButton("Вернуться в главное меню")
    markup.add(btn_main_menu)

    # Просим пользователя отправить ссылку на автомобиль
    bot.send_message(
        message.chat.id,
        "Отправьте ссылку на автомобиль с сайта kimsautotrade.com или encar.com:",
        reply_markup=markup,
    )


##############
# КЫРГЫЗСТАН КОНЕЦ
##############


# Обработчики для других кнопок
@bot.message_handler(func=lambda message: message.text == "Instagram")
def handle_instagram(message):
    bot.send_message(
        message.chat.id,
        "Наш Instagram: https://www.instagram.com/kims_auto_trade_official",
    )


@bot.message_handler(func=lambda message: message.text == "WhatsApp")
def handle_whatsapp(message):
    ramis_whatsapp = "+82 10-8029-6232"

    # Формирование ссылки для WhatsApp:
    # Убираем символ "+", пробелы и тире, чтобы получить корректный формат номера для ссылки.
    ramis_link = "https://wa.me/" + ramis_whatsapp.replace("+", "").replace(
        " ", ""
    ).replace("-", "")

    result_message = f"Рамис: {ramis_whatsapp} {ramis_link}"

    bot.send_message(message.chat.id, result_message)


@bot.message_handler(func=lambda message: message.text == "Telegram-канал")
def handle_telegram_channel(message):
    bot.send_message(
        message.chat.id,
        "Наш Telegram-канал: https://t.me/avtokoreaRF",
    )


@bot.message_handler(func=lambda message: message.text == "Контакты")
def handle_manager(message):
    output_message = f"+82 10-8029-6232 - Рамис (Корея)"

    bot.send_message(message.chat.id, output_message)


def run_in_thread(target):
    """Запуск функции в отдельном потоке"""
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()


if __name__ == "__main__":
    # Запуск длительных задач в отдельных потоках
    run_in_thread(set_bot_commands)
    run_in_thread(get_nbkr_currency_rates)
    run_in_thread(get_nbk_currency_rates)
    run_in_thread(get_currency_rates)
    # Основной поток выполняет бот
    bot.polling(none_stop=True)
