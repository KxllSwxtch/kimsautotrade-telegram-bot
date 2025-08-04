def get_car_info(url):
    global car_id_external

    driver = create_driver()

    car_id_match = re.findall(r"\d+", url)
    car_id = car_id_match[0]
    car_id_external = car_id

    try:
        # solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

        is_recaptcha_solved = True

        driver.get(url)
        time.sleep(3)

        if is_recaptcha_solved:
            # Достаём данные об авто после решения капчи
            car_date, car_price, car_engine_displacement, car_type = "", "", "", ""

            price_el = driver.find_element(By.CLASS_NAME, "DetailLeadCase_point__vdG4b")
            car_price = re.sub(r"\D", "", price_el.text)
            time.sleep(3)

            button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), '자세히')]")
                )
            )
            button.click()
            time.sleep(2)

            content = driver.find_element(
                By.CLASS_NAME,
                "BottomSheet-module_bottom_sheet__LeljN",
            )
            splitted_content = content.text.split("\n")
            car_engine_displacement = re.sub(r"\D", "", splitted_content[9])

            car_date = splitted_content[5]

            year = re.sub(r"\D", "", car_date.split(" ")[0])
            month = re.sub(r"\D", "", car_date.split(" ")[1])
            formatted_car_date = f"01{month}{year}"

            car_type = splitted_content[15]
            formatted_car_type = "crossover" if car_type == "SUV" else "sedan"

            print_message(
                f"ID: {car_id}\nType: {formatted_car_type}\nDate: {formatted_car_date}\nCar Engine Displacement: {car_engine_displacement}\nPrice: {car_price} KRW"
            )

            # Сохранение данных в базу
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO car_info (car_id, date, engine_volume, price, car_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (date, engine_volume, price) DO UPDATE 
                    SET car_id = EXCLUDED.car_id, car_type = EXCLUDED.car_type
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
                print("Автомобиль был сохранён в базе данных")
            except psycopg2.Error as e:
                print(f"Ошибка при сохранении в базу данных: {e}")
                conn.rollback()
            finally:
                cursor.close()
                conn.close()

            driver.quit()
            return [car_date, car_price, car_engine_displacement, formatted_car_type]

    except WebDriverException as e:
        print(f"Ошибка Selenium: {e}")
        driver.quit()
        return ["", "Произошла ошибка получения данных...", "", ""]

    return ["", "", "", ""]
