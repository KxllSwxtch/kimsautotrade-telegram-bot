def get_insurance_total():
    global car_id_external

    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")

    driver = create_driver()
    url = f"http://fem.encar.com/cars/report/accident/{car_id_external}"

    try:
        # Запускаем WebDriver
        driver.get(url)
        time.sleep(5)

        try:
            report_accident_el = driver.find_element(
                By.CLASS_NAME, "ReportAccidentSummary_list_accident__q6vLx"
            )

            splitted_report = report_accident_el.text.split("\n")
            damage_to_my_car = splitted_report[4]
            damage_to_other_car = splitted_report[5]
        except NoSuchElementException:
            print("Элемент 'smlist' не найден.")
            return ["Нет данных", "Нет данных"]

        # Упрощенная функция для извлечения числа
        def extract_large_number(damage_text):
            if "없음" in damage_text:
                return "0"
            numbers = re.findall(r"[\d,]+(?=\s*원)", damage_text)
            return numbers[0] if numbers else "0"

        # Форматируем данные
        damage_to_my_car_formatted = extract_large_number(damage_to_my_car)
        damage_to_other_car_formatted = extract_large_number(damage_to_other_car)

        print(f"Выплаты по представленному автомобилю: {damage_to_my_car_formatted}")
        print(f"Выплаты другому автомобилю: {damage_to_other_car_formatted}")

        return [damage_to_my_car_formatted, damage_to_other_car_formatted]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return ["Ошибка при получении данных", ""]

    finally:
        driver.quit()
