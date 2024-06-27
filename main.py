from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.web_app_info import WebAppInfo
import sqlite3
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
import asyncio

bot = Bot('6113247845:AAGmISBzr1irMVh_FcpLsB2GRb-vLAD3HyI')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)


class BookingStates(StatesGroup):
    choose_stylist = State()
    choose_date = State()
    choose_time = State()


# хранение данных юзеров
user_data = {}


def setup_database():
    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()

    cur.execute(''' CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER UNIQUE,
        name TEXT,
        phone_number TEXT,
        city TEXT
    )''')
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS users_size (
            user_id INTEGER,
            brand_n TEXT,
            size TEXT,
            PRIMARY KEY (user_id, brand_n)
    )''')
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS Stylists (
                    id_stylist INTEGER PRIMARY KEY,
                    name_st TEXT,
                    number_st TEXT)''')
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS Schedule (
                    id_stylist INTEGER,
                    name_st TEXT,
                    date TEXT,
                    time TEXT,
                    status TEXT DEFAULT 'open',
                    FOREIGN KEY(id_stylist) REFERENCES Stylists(id_stylist))''')
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS Booking (
                    user_id INTEGER,
                    name TEXT,
                    phone_number TEXT,
                    date TEXT,
                    time TEXT,
                    id_stylist INTEGER,
                    name_st TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(phone_number) REFERENCES users(phone_number),
                    FOREIGN KEY(id_stylist) REFERENCES Stylists(id_stylist))''')
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS BrandName
                 (brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 brand_name TEXT NOT NULL)''')
    brands = ['DiegoM', 'AniaSchierhot', 'ReveRa']
    for brand in brands:
        cur.execute("SELECT * FROM BrandName WHERE brand_name=?", (brand,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO BrandName (brand_name) VALUES (?)", (brand,))
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS RSize
              (size_id INTEGER PRIMARY KEY AUTOINCREMENT,
              russian_size TEXT NOT NULL)''')
    russian_sizes = [40, 42, 44, 46, 48, 50]
    for size in russian_sizes:
        cur.execute("SELECT * FROM RSize WHERE russian_size=?", (size,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO RSize (russian_size) VALUES (?)", (size,))
    conn.commit()

    cur.execute('''CREATE TABLE IF NOT EXISTS BrSize
                            (brand_id INTEGER,
                           size_id INTEGER,
                           european_size TEXT NOT NULL,
                           FOREIGN KEY (brand_id) REFERENCES BrandName(brand_id),
                           FOREIGN KEY (size_id) REFERENCES RSize(size_id))''')
    brsize_data = [
        (1, 1, '38'), (1, 2, '40'), (1, 3, '42'), (1, 4, '44'), (1, 5, '46'), (1, 6, '48'),
        (2, 1, '34'), (2, 2, '36'), (2, 3, '38'), (2, 4, '40'), (2, 5, '42'), (2, 6, '44'),
        (3, 1, 'XS'), (3, 2, 'S'), (3, 3, 'M'), (3, 4, 'L'), (3, 5, 'XL'), (3, 6, '2XL')
    ]
    for brand_id, size_id, european_size in brsize_data:
        cur.execute("SELECT * FROM BrSize WHERE brand_id=? AND size_id=? AND european_size=?",
                    (brand_id, size_id, european_size))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO BrSize (brand_id, size_id, european_size) VALUES (?, ?, ?)",
                        (brand_id, size_id, european_size))
    conn.commit()
    conn.close()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.answer('Здравствуйте! Перед вами вируатльный помощник бутика "Bulvar". '
                         'Подскажите, как могу к Вам обращаться?')


@dp.message_handler(lambda message: message.from_user.id in user_data and 'first_name' not in user_data[message.from_user.id])
async def process_name(message: types.Message):
    user_data[message.from_user.id]['first_name'] = message.text
    await message.answer('Приятно познакомиться, из какого вы города?')


@dp.message_handler(lambda message: message.from_user.id in user_data and 'first_name' in user_data[message.from_user.id] and 'city' not in user_data[message.from_user.id])
async def process_city(message: types.Message):
    user_data[message.from_user.id]['city'] = message.text
    await message.answer("Отправьте, пожалуйста, ваш номер телефона, чтобы мы могли связаться с Вами.")


@dp.message_handler(lambda message: message.from_user.id in user_data and 'first_name' in user_data[message.from_user.id] and 'city' in user_data[message.from_user.id] and 'phone_number' not in user_data[message.from_user.id])
async def process_phone_number(message: types.Message):
    user_data[message.from_user.id]['phone_number'] = message.text

    # Save to database
    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    user_info = user_data[message.from_user.id]
    cur.execute('''INSERT OR REPLACE INTO users (user_id, name, city, phone_number)
                   VALUES (?, ?, ?, ?)''', (message.from_user.id, user_info['first_name'],
                                            user_info['city'], user_info['phone_number']))
    conn.commit()
    conn.close()

    await message.answer(f"Спасибо, {user_info['first_name']}! Ваши данные сохранены.")
    asyncio.create_task(send_notif())

    # главное меню
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton(text='Каталог')
    btn2 = types.KeyboardButton(text='Готовые образы')
    markup.row(btn1, btn2)
    btn3 = types.KeyboardButton(text='Размер')
    btn4 = types.KeyboardButton(text='Стилист')
    markup.row(btn3, btn4)
    await message.answer(
        "Пользуйтесь меню для дальнейшей работы с ботом:\n Больше информации о боте: /help",
        reply_markup=markup
    )


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.answer("Список доступных команд:\n"
                         "/help - список доступных команд\n"
                         "/start - начать использование бота\n"
                         "/catalog - показать каталог\n"
                         "/catalog - каталог товаров\n"
                         "/outfits - каталог готовых образов\n"
                         "/reserve - запись на консультацию стилиста")


@dp.message_handler(commands=['catalog'])
@dp.message_handler(text='Каталог')
async def show_catalog(message: types.Message):
    mar = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Открыть каталог", web_app=WebAppInfo(url='https://bulvarpro.tilda.ws/catalog'))
    mar.add(button1)
    await message.answer('Ознакомиться с каталогом можно перейдя по ссылке ниже:', reply_markup=mar)


@dp.message_handler(commands=['stylist'])
@dp.message_handler(text='Стилист')
async def show_stylist(message: types.Message):
    mar = types.InlineKeyboardMarkup()
    button2 = types.InlineKeyboardButton("Стилист-Елена", url='https://t.me/elenaspiridonovaa')
    mar.add(button2)
    await message.answer('Перейти в личный чат со стилистом:', reply_markup=mar)


@dp.message_handler(commands=['outfits'])
@dp.message_handler(text='Готовые образы')
async def show_outfits(message: types.Message):
    m = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Открыть каталог", web_app=WebAppInfo(url='https://bulvaroutfits.tilda.ws/'))
    m.add(btn)
    await message.answer('Ознакомиться с каталогом готовых образов можно перейдя по ссылке ниже:', reply_markup=m)


@dp.message_handler(commands=['size'])
@dp.message_handler(text='Размер')
async def show_size(message: types.Message):
    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    cur.execute('SELECT brand_n, size FROM users_size WHERE user_id = ?', (message.from_user.id,))
    rows = cur.fetchall()
    conn.close()

    if rows:
        sizes_info = '\n'.join([f"{brand}: {size}" for brand, size in rows])
        await message.reply(f"Ваши размеры:\n{sizes_info}")

    await message.reply('Введите название бренда и ваш российский размер.\n'
                        'Пример сообщения: DiegoM 42. \n'
                        'Наши бренды: DiegoM, AniaSchierhot, ReveRa')


@dp.message_handler(commands=['reserve'])
@dp.message_handler(text='Запись')
async def start_reserve(message: types.Message):
    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    cur.execute("SELECT name_st FROM Stylists")
    stylists = cur.fetchall()
    conn.close()

    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for stylist in stylists:
        keyboard.add(KeyboardButton(text=stylist[0]))

    await message.answer("К какому стилисту вы бы хотели записаться?", reply_markup=keyboard)
    await BookingStates.choose_stylist.set()


@dp.message_handler(state=BookingStates.choose_stylist)
async def choose_date(message: types.Message, state: FSMContext):
    stylist_name = message.text
    await state.update_data(stylist_name=stylist_name)

    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT date FROM Schedule WHERE name_st = ? AND status = 'open'", (stylist_name,))
    available_dates = cur.fetchall()
    conn.close()

    if not available_dates:
        await message.answer("Извините, все даты уже заняты или недоступны.")
        await state.finish()
        return

    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for date in available_dates:
        keyboard.add(KeyboardButton(text=date[0]))

    await message.answer("Выберите доступную дату:", reply_markup=keyboard)
    await BookingStates.choose_date.set()


@dp.message_handler(state=BookingStates.choose_date)
async def choose_time(message: types.Message, state: FSMContext):
    chosen_date = message.text
    await state.update_data(chosen_date=chosen_date)

    user_data = await state.get_data()
    stylist_name = user_data['stylist_name']

    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    cur.execute("SELECT time FROM Schedule WHERE name_st = ? AND date = ? AND status = 'open'", (stylist_name, chosen_date))
    available_times = cur.fetchall()
    conn.close()

    if not available_times:
        await message.answer("Извините, все время уже занято или недоступно.")
        await state.finish()
        return

    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    for time in available_times:
        keyboard.add(KeyboardButton(text=time[0]))

    await message.answer("Выберите доступное время:", reply_markup=keyboard)
    await BookingStates.choose_time.set()


@dp.message_handler(state=BookingStates.choose_time)
async def book_consultation(message: types.Message, state: FSMContext):
    chosen_time = message.text
    await state.update_data(chosen_time=chosen_time)
    user_data = await state.get_data()

    stylist_name = user_data['stylist_name']
    chosen_date = user_data['chosen_date']

    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    cur.execute("SELECT phone_number FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        user_number = row[0]
    else:
        user_number = None
    conn.close()

    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()

    # получение id стилиста
    cur.execute("SELECT id_stylist FROM Stylists WHERE name_st = ?", (stylist_name,))
    stylist_id = cur.fetchone()[0]

    # добавление запись в таблицу с бронью
    cur.execute('''INSERT INTO Booking (user_id, name, phone_number, date, time, id_stylist, name_st) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, user_name, user_number, chosen_date, chosen_time, stylist_id, stylist_name))
    # удаление занятого времи из таблицы с графиком
    cur.execute('''DELETE FROM Schedule WHERE id_stylist = ? AND date = ? AND time = ?''',
                (stylist_id, chosen_date, chosen_time))

    conn.commit()
    conn.close()

    await message.answer(f"Вы записаны на консультацию, стилист - {stylist_name}. Ждём вас {chosen_date}, в {chosen_time}.")

    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton(text='Каталог')
    btn2 = types.KeyboardButton(text='Готовые образы')
    markup.row(btn1, btn2)
    btn3 = types.KeyboardButton(text='Размер')
    btn4 = types.KeyboardButton(text='Стилист')
    markup.row(btn3, btn4)
    await message.answer(
        "Пользуйтесь меню для дальнейшей работы с ботом:\n"
        "Больше информации о боте: /help",
        reply_markup=markup
    )
    await state.finish()


@dp.message_handler()
async def process_user_input(message: types.Message):
    try:
        brand_name, russian_size = message.text.split()
    except ValueError:
        await message.reply("Пожалуйста, отправьте сообщение в формате 'Бренд Размер', например: 'DiegoM 42'")
        return

    conn = sqlite3.connect('BulvarSize.db')
    cur = conn.cursor()
    cur.execute('''SELECT european_size FROM BrSize
                   JOIN BrandName ON BrSize.brand_id = BrandName.brand_id
                   JOIN RSize ON BrSize.size_id = RSize.size_id
                   WHERE BrandName.brand_name = ? AND RSize.russian_size = ?''',
                (brand_name, russian_size))
    result = cur.fetchone()

    if result:
        european_size = result[0]
        await message.reply(f"Подходящий размер для бренда {brand_name}: {european_size}")

        cur.execute('''INSERT OR REPLACE INTO users_size (user_id, brand_n, size)
                       VALUES (?, ?, ?)''',
                    (message.from_user.id, brand_name, european_size))
        conn.commit()
    else:
        await message.reply("К сожалению, подходящий размер не найден.")

    conn.close()
    conn.close()


async def send_notif():
    while True:
        conn = sqlite3.connect('BulvarSize.db')
        cursor = conn.cursor()
        await asyncio.sleep(30)  # 30 сек
        try:
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            for user in users:
                user_id = user[0]
                logging.info(f"Отправлено уведомление {user_id}")
                await bot.send_message(chat_id=user_id, text='Добрый день! Приглашаем вас на примерку новой '
                                                             'коллекции!\n'
                                                             'Записаться можно воспользовавшись командой /reserve')
                logging.info(f"Успешно отправлено {user_id}")
        except Exception as e:
            logging.error(f"Ошибка: {e}")
        finally:
            conn.close()

executor.start_polling(dp)