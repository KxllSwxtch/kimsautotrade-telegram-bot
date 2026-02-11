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
    pending_calculations,
    complete_russia_calculation_with_hp,
    manual_calc_data,
    complete_manual_russia_calculation,
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
    btn_manual = types.KeyboardButton("Ручной расчёт")
    btn_instagram = types.KeyboardButton("Instagram")
    btn_whatsapp = types.KeyboardButton("WhatsApp")
    btn_telegram = types.KeyboardButton("Telegram-канал")
    btn_manager = types.KeyboardButton("Контакты")

    # Добавление кнопок в меню
    markup.add(btn_calc, btn_manual, btn_instagram, btn_whatsapp, btn_telegram, btn_manager)

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
    btn_manual = types.KeyboardButton("Ручной расчёт")
    btn_instagram = types.KeyboardButton("Instagram")
    btn_whatsapp = types.KeyboardButton("WhatsApp")
    btn_telegram = types.KeyboardButton("Telegram-канал")
    btn_manager = types.KeyboardButton("Контакты")

    # Добавление кнопок в меню
    markup.add(btn_calc, btn_manual, btn_instagram, btn_whatsapp, btn_telegram, btn_manager)

    # Очищаем состояние ручного расчёта
    if user_id in manual_calc_data:
        del manual_calc_data[user_id]

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
# РУЧНОЙ РАСЧЁТ (только Россия)
###############
@bot.message_handler(func=lambda message: message.text == "Ручной расчёт")
def handle_manual_calc(message):
    chat_id = message.chat.id
    manual_calc_data[chat_id] = {"step": "age"}

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("до 3 лет", callback_data="manual_age:0-3"),
        types.InlineKeyboardButton("от 3 до 5 лет", callback_data="manual_age:3-5"),
        types.InlineKeyboardButton("от 5 до 7 лет", callback_data="manual_age:5-7"),
        types.InlineKeyboardButton("более 7 лет", callback_data="manual_age:7-0"),
    )

    # Клавиатура с кнопкой возврата
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в главное меню"))
    bot.send_message(chat_id, "Выберите возраст автомобиля:", reply_markup=markup)
    bot.send_message(chat_id, "Возраст автомобиля:", reply_markup=keyboard)


def is_manual_calc_text_input(chat_id):
    """Проверяет, ожидает ли пользователь текстовый ввод в ручном расчёте"""
    mc = manual_calc_data.get(chat_id)
    return mc and mc.get("step") in ("horsepower", "price")


@bot.message_handler(func=lambda message: is_manual_calc_text_input(message.chat.id))
def handle_manual_calc_text_input(message):
    chat_id = message.chat.id
    mc = manual_calc_data.get(chat_id)

    if not mc:
        return

    if mc["step"] == "horsepower":
        try:
            hp = int(message.text.strip())
            if hp <= 0 or hp > 2000:
                raise ValueError("Invalid HP range")
        except ValueError:
            bot.send_message(
                chat_id,
                "❌ Пожалуйста, введите корректное значение мощности (число от 1 до 2000).\n"
                "Например: 150",
            )
            return

        mc["horsepower"] = hp
        mc["step"] = "price"
        bot.send_message(
            chat_id,
            "Введите стоимость автомобиля в корейских вонах (₩).\nНапример: 42500000",
        )

    elif mc["step"] == "price":
        try:
            price = int(message.text.strip().replace(" ", ""))
            if price <= 0:
                raise ValueError("Invalid price")
        except ValueError:
            bot.send_message(
                chat_id,
                "❌ Пожалуйста, введите корректную стоимость (положительное число).\n"
                "Например: 42500000",
            )
            return

        mc["price"] = price

        # Отправляем сообщение о процессе
        processing_msg = bot.send_message(chat_id, "⏳ Расчёт таможенных платежей...")

        try:
            complete_manual_russia_calculation(chat_id, mc)
        except Exception as e:
            bot.send_message(
                chat_id,
                "❌ Ошибка при расчёте. Пожалуйста, попробуйте снова.\n\n"
                "Для помощи напишите менеджеру: +82-10-8029-6232",
            )
            print(f"Ошибка при ручном расчёте: {e}")
        finally:
            try:
                bot.delete_message(chat_id, processing_msg.message_id)
            except Exception:
                pass
            # Очищаем состояние
            manual_calc_data.pop(chat_id, None)


###############
# ОБРАБОТКА ВВОДА HP (МОЩНОСТИ) ДЛЯ РОССИИ
###############
def is_awaiting_hp_input(chat_id):
    """Проверяет, ожидает ли пользователь ввода HP"""
    return chat_id in pending_calculations


@bot.message_handler(func=lambda message: is_awaiting_hp_input(message.chat.id))
def handle_hp_input(message):
    """Обработчик ввода мощности двигателя (HP) для расчёта таможни"""
    chat_id = message.chat.id

    # Проверяем, что пользователь ввёл число
    try:
        hp = int(message.text.strip())
        if hp <= 0 or hp > 2000:
            raise ValueError("Invalid HP range")
    except ValueError:
        bot.send_message(
            chat_id,
            "❌ Пожалуйста, введите корректное значение мощности (число от 1 до 2000).\n"
            "Например: 132",
        )
        return

    # Получаем данные незавершённого расчёта
    pending = pending_calculations.pop(chat_id, None)
    if not pending:
        bot.send_message(chat_id, "❌ Ошибка: данные расчёта не найдены. Попробуйте снова.")
        return

    # Отправляем сообщение о процессе
    processing_msg = bot.send_message(chat_id, "⏳ Расчёт таможенных платежей...")

    try:
        # Завершаем расчёт с указанным HP
        complete_russia_calculation_with_hp(chat_id, pending, hp)
    except Exception as e:
        bot.send_message(
            chat_id,
            "❌ Ошибка при расчёте. Пожалуйста, попробуйте снова.\n\n"
            "Для помощи напишите менеджеру: +82-10-8029-6232",
        )
        print(f"Ошибка при расчёте с HP: {e}")
    finally:
        # Удаляем сообщение о процессе
        try:
            bot.delete_message(chat_id, processing_msg.message_id)
        except Exception:
            pass


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
