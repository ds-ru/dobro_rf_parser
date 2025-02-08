import re
import csv

phone_pattern = re.compile(r'\b\d{11}\b')  # Ищем 11-значные номера телефонов
email_pattern = re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b')  # Ищем email-адреса

# Функция для извлечения данных из строки
def extract_data(line):
    emails = email_pattern.findall(line)
    phones = phone_pattern.findall(line)

    if not emails and not phones:
        return None

    result = []
    for email in emails:
        for phone in phones:
            result.append({'Email': email, 'Phone': phone, 'OriginalLine': line.strip()})
        if not phones:  # Если телефонов нет, добавляем только email
            result.append({'Email': email, 'Phone': '', 'OriginalLine': line.strip()})
    if not emails:  # Если email нет, добавляем только телефоны
        for phone in phones:
            result.append({'Email': '', 'Phone': phone, 'OriginalLine': line.strip()})

    return result

def process_file(input_file, output_file):
    data = []

    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            extracted = extract_data(line)
            if extracted:
                data.extend(extracted)

    with open(output_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Email', 'Phone', 'OriginalLine'])
        writer.writeheader()
        writer.writerows(data)

    print(f"Данные успешно сохранены в {output_file}")

process_file('txt.txt', 'output.csv')
