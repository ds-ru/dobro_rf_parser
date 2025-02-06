import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientConnectionError
import aiosqlite
import json
from urllib.parse import quote


HEADERS = {
    ':authority': 'dobro.ru',
    ':method': 'GET',
    ':scheme': 'https',
    ':path': '/api/v2/volunteers/search?page=2&limit=30',
    'accept': 'application/vnd.meta+json',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'ru,en;q=0.9',
    'dnt': '1',
    'if-none-match': 'W/"d7b2014d554991ecb419d705934a4b2f"',
    'priority': 'u=1, i',
    'referer': 'https://dobro.ru/search?t=vl',
    'sec-ch-ua': '"Chromium";v="130", "YaBrowser";v="24.12", "Not?A_Brand";v="99", "Yowser";v="2.5"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 '
                  'YaBrowser/24.12.0.0 Safari/537.36'
}


DB_NAME = 'volunteers.db'


async def create_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу, если она не существует
        await db.execute(''' 
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                second_name TEXT,
                birth_date DATE,
                profile_url TEXT,
                city TEXT,
                organization TEXT,
                social_links TEXT
            )
        ''')
        await db.close()


async def fetch_volunteers(session, url):
    retries = 3
    for attempt in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    print(f"Ошибка {response.status} при запросе к {url}")
                    return []
        except ClientConnectionError:
            print("Сайт недоступен. Попробуйте позже.")
            break
        except asyncio.TimeoutError:
            print("Время ожидания истекло. Повторная попытка...")
            await asyncio.sleep(2)  # Ждем перед повтором
        except json.JSONDecodeError:
            print("Ошибка формата ответа. Попробуйте снова.")
            break
    return []


async def fetch_institutions(session, query):
    """Функция для получения списка учебных заведений по введённой части названия."""
    url = f"https://dobro.ru/api/v2/handbooks/institutions?title={quote(query)}"
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                print(f"Ошибка {response.status} при запросе к {url}")
                return []
    except aiohttp.ClientError as e:
        print(f"Ошибка соединения: {e}")
        return []


# noinspection PyTypeChecker
async def choose_institution(session):
    """
    Функция для динамического поиска и выбора учебного заведения.
    Пользователь вводит часть названия, видит список результатов и выбирает нужное.
    """
    while True:
        query = input("Введите часть названия учебного заведения (или нажмите Enter для пропуска): ").strip()
        if not query:
            return None  # Пользователь не хочет выбирать учебное заведение
        institutions = await fetch_institutions(session, query)
        if not institutions:
            print("Учебные заведения по запросу не найдены. Попробуйте снова.")
            continue
        print(institutions)
        print("Найденные учебные заведения:")
        for idx, inst in enumerate(institutions["data"], start=1):
            # Убираем лишние пробелы в начале строки методом .strip()
            title = inst.get("title", "Без названия").strip()
            inst_id = inst.get("id", "нет")
            print(f"{idx}. {title} (ID: {inst_id})")

        choice = input(
            "Введите номер выбранного учебного заведения (или нажмите Enter для повторного поиска): ").strip()
        if not choice:
            # Если пользователь нажал Enter без ввода, возвращаемся к поиску
            continue
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(institutions["data"]):
                selected = institutions["data"][choice_num - 1]  # Исправленный индекс
                print(f"Вы выбрали: {selected.get('title')} (ID: {selected.get('id')})")
                return selected.get('id')  # Возвращаем выбранное заведение
            else:
                print("Неверный номер. Попробуйте снова.")
        except ValueError:
            print("Введите корректное число.")


def format_name(value):
    return value.title() if value else None


async def save_to_db(volunteer):
    social_media = volunteer.get('socialMedia', {})
    social_links = [link for platform, link in social_media.items() if platform != 'hasNotEmptyLink' and link]

    volunteer_data = volunteer.get('fio', {})

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO volunteers (
                id, first_name, last_name, second_name, birth_date, 
                profile_url, city, organization, social_links
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            volunteer.get('id'),
            format_name(volunteer_data.get('first_name')),
            format_name(volunteer_data.get('last_name')),
            format_name(volunteer_data.get('second_name')),  # middle_name в таблице
            volunteer.get('birthday'),
            f"https://dobro.ru/volunteer/{volunteer.get('id')}",
            volunteer.get('settlement', {}).get('title', '').title() or None,
            volunteer.get('volunteerOrganization', {}).get('name'),
            ', '.join(social_links) if social_links else None
        ))
        await db.commit()
        print("Запись сохранена:", volunteer_data.get('first_name', 'Без имени'))


def build_url(city, category, top_rating_max, top_rating_min,
              region_rating_max, region_rating_min,
              mentor, organizer, page, limit, selected_institution, fio):
    base_url = "https://dobro.ru/api/v2/volunteers/search?"
    params = []

    if top_rating_max:
        params.append(f"topRatingMax={top_rating_max}")
    if top_rating_min:
        params.append(f"topRatingMin={top_rating_min}")
    if region_rating_max:
        params.append(f"regionTopRatingMax={region_rating_max}")
    if region_rating_min:
        params.append(f"regionTopRatingMin={region_rating_min}")

    if city:
        # Кодируем значение города, например "Москва" -> %D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0
        city_encoded = quote(city)
        params.append(f"location%5Btitle%5D={city_encoded}")

    if fio:
        fio_encoded = quote(fio)
        params.append(f"query={fio_encoded}")

    if category:
        params.append(f"categories%5B0%5D={category}")
    if mentor == "yes":
        params.append("mentor=true")
    if organizer == "yes":
        params.append("organizer=true")

    if selected_institution:
        params.append(f"institution={selected_institution}")

    params.append(f"page={page}")
    params.append(f"limit={limit}")

    url = base_url + "&".join(params)
    print("Сформированный URL:", url)
    return url


CATEGORIES = (
    (15, "Здравоохранение и ЗОЖ"), (16, "ЧС"), (17, "Ветераны и Историческая память"),
    (18, "Дети и молодежь"), (19, "Спорт и события"), (20, "Животные"),
    (21, "Старшее поколение"), (22, "Люди с ОВЗ"), (23, "Экология"),
    (24, "Культура и искусство"), (25, "Поиск пропавших"), (26, "Урбанистика"),
    (27, "Интеллектуальная помощь"), (28, "Права человека"), (29, "Образование"),
    (30, "Другое"), (18134, "Коронавирус"), (129332, "Наука"),
    (246356, "Наставничество"), (391614, "СВО")
)


async def main():
    await create_db()
    city = input("Введите город (или нажмите Enter для пропуска): ")

    fio = input("Введите фамилию, имя или отчество для поиска (или нажмите Enter для пропуска): ")

    for cat in CATEGORIES:
        print(f"{cat[0]} - {cat[1]}")
    while True:
        category = input("Введите номер категории (или нажмите Enter для пропуска): ")
        if not category:
            print("Фильтрация по категории не выбрана.")
            break
        try:
            selected_category_id = int(category)
            if selected_category_id not in [cat[0] for cat in CATEGORIES]:
                raise ValueError
            break
        except ValueError:
            print("Пожалуйста, введите корректный числовой ID из списка доступных категорий.")

    # Минимальный рейтинг карточки волонтера на портале
    top_rating_min = input("Введите минимальный желаемый рейтинг на платформе: ")

    # Максимальный рейтинг карточки волонтера на портале
    top_rating_max = input("Введите максимальный желаемый рейтинг на платформе: ")

    # Минимальный рейтинг волонтера по региону
    region_rating_min = input("Введите минимальный желаемый рейтинг по региону: ")

    # Максимальный рейтинг волонтера по региону
    region_rating_max = input("Введите максимальный желаемый рейтинг по региону: ")

    mentor = input("Требуется наставник? (yes/no, по умолчанию no): ").lower() or "no"

    organizer = input("Требуется организатор? (yes/no, по умолчанию no): ").lower() or "no"

    limit = 30  # число записей на странице
    page = 1

    async with aiohttp.ClientSession() as session:
        selected_institution = await choose_institution(session)
        while True:
            url = build_url(city, category, top_rating_max, top_rating_min,
                            region_rating_max, region_rating_min,
                            mentor, organizer, page, limit, selected_institution, fio)
            print(f"Загрузка страницы {page}...")
            volunteers_data = await fetch_volunteers(session, url)
            if not volunteers_data:
                print("Данные закончились или не найдены.")
                break

            await asyncio.gather(*(save_to_db(volunteer) for volunteer in volunteers_data))

            page += 1
            print(f"Переход на страницу {page}...")

if __name__ == '__main__':
    asyncio.run(main())
