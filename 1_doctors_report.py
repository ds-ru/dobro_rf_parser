import pandas as pd

# Загрузка данных
report = pd.read_excel("Задание 1.xlsx", sheet_name="Отчет")
data = pd.read_excel("Задание 1.xlsx", sheet_name="Данные от врачей")

# Разделение ФИО на компоненты
data[['Фамилия', 'Имя', 'Отчество']] = data['ФИО'].str.split(n=2, expand=True)

# Приведение данных к нижнему регистру и удаление пробелов
data[['Фамилия', 'Имя', 'Отчество']] = data[['Фамилия', 'Имя', 'Отчество']].apply(lambda x: x.str.strip().str.lower())
report[['Фамилия', 'Имя', 'Отчество']] = report[['Фамилия', 'Имя', 'Отчество']].apply(lambda x: x.str.strip().str.lower())

# Преобразование дат
data['ДР'] = pd.to_datetime(data['ДР']).dt.strftime('%d.%m.%Y')
data['Дата Осмотра'] = pd.to_datetime(data['Дата Осмотра']).dt.strftime('%d.%m.%Y')
report['ДР'] = pd.to_datetime(report['ДР']).dt.strftime('%d.%m.%Y')

# Создание составного ключа
data['key'] = data['Фамилия'] + data['Имя'] + data['Отчество'] + data['ДР']
report['key'] = report['Фамилия'] + report['Имя'] + report['Отчество'] + report['ДР']

# Создание словаря
doctor_dict = {}
for _, row in data.iterrows():
    key = row['key']
    date = row['Дата Осмотра']
    state = row['Состояние'].strip().lower()
    if key not in doctor_dict:
        doctor_dict[key] = {}
    doctor_dict[key][date] = state


dates = {
    '10 окт': '10.10.2020',
    '12 окт': '12.10.2020',
    '20 окт': '20.10.2020'
}


for report_col, target_date in dates.items():
    report[report_col] = report['key'].apply(
        lambda x: doctor_dict.get(x, {}).get(target_date, 'здоров')
    )

# Сохранение результата
report.to_excel('Задание 1_обновленный.xlsx', index=False)
print("Отчет успешно сохранен в файл 'Задание 1_обновленный.xlsx'")

# Загрузка данных
report = pd.read_excel("Задание 1_обновленный.xlsx")

# Создание сводной таблицы
# Определяем пол пациента по отчеству
report['Пол'] = report['Отчество'].apply(
    lambda x: 'муж' if x.endswith('вич') or x.endswith('ич') else 'жен'
)

# Сводная таблица по количеству больных на каждую дату
pivot_table = pd.pivot_table(
    report,
    values=['10 окт', '12 окт', '20 окт'],
    index='Пол',
    aggfunc=lambda x: (x == 'болен').sum()
)

# Добавляем строку "Всего"
pivot_table.loc['Всего'] = pivot_table.sum()

# Переименовываем колонки для красоты
pivot_table.columns = ['10 окт', '12 окт', '20 окт']

# Вывод результата
print(pivot_table)
