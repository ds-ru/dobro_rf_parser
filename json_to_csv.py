import json
import re
import csv
from datetime import datetime


# Функция для исправления даты
def fix_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y/%m/%d").strftime("%Y/%m/%d")
    except ValueError:
        return None


# Функция для исправления номера телефона
def fix_phone(phone):
    phone = re.sub(r"[^0-9]", "", phone)
    return phone if len(phone) >= 10 else None


# Функция для исправления email
def fix_email(email):
    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email):
        return email
    return None


# Функция для загрузки JSON и исправления некорректных символов
def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        raw_data = file.read()
    raw_data = raw_data.replace("\\", "\\\\")
    raw_data = re.sub(r'"/', '', raw_data)
    raw_data = re.sub(r'/"', '', raw_data)
    raw_data = raw_data.replace(",]", "]")
    raw_data = raw_data.replace("[,", "[")
    raw_data = re.sub(r'[\x00-\x1F\x7F\n\r]+', '', raw_data)

    try:
        return json.loads(raw_data)
    except json.JSONDecodeError:
        print("Ошибка при парсинге JSON.")
        return []


# Функция для исправления данных и сохранения их в новый файл
def fix_json(filename):
    data = load_json(filename)
    fixed_data = []

    for entry in data:
        fixed_entry = {}
        for key, value in entry.items():
            if key == "dob":
                fixed_entry[key] = fix_date(value)
            elif key == "t":
                fixed_entry[key] = fix_phone(str(value))
            elif key == "e":
                fixed_entry[key] = fix_email(value)
            else:
                fixed_entry[key] = value

        fixed_data.append(fixed_entry)

    # Сохранение исправленных данных в JSON
    with open("fixed_json.json", "w", encoding="utf-8") as file:
        json.dump(fixed_data, file, indent=4)

    print("Данные успешно сохранены в fixed_json.json")

    # Конвертация в CSV
    save_as_csv(fixed_data)


# Функция для сохранения данных в CSV
def save_as_csv(data):
    if not data:
        print("Нет данных для сохранения в CSV.")
        return

    # Собираем все уникальные ключи из данных
    keys = sorted({key for entry in data for key in entry.keys()})

    with open("csv.csv", mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    print("Данные успешно сохранены в csv.csv")


# Запуск обработки
fix_json("json.json")
