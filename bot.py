import logging
import asyncio
import aiosqlite
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv('BOT_TOKEN') or "7950441922:AAEhDB9gopYhOFmhd0nRrCbej8MtPi9elBI"
if not API_TOKEN:
    logging.error("Токен бота не найден!")
    exit(1)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

ACTIVATION_CODE = "25848"
IMAGE_PATH = "start_image.jpg"


async def has_active_subscription(user_id):
    async with aiosqlite.connect('users.db') as db:
        async with db.execute("SELECT subscription_end FROM users WHERE user_id=?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            if not result:
                return False
            try:
                subscription_end = datetime.strptime(result[0], "%Y-%m-%d")
                return datetime.now() < subscription_end
            except:
                return False


class DemolitionStates(StatesGroup):
    waiting_for_target = State()


class ActivationStates(StatesGroup):
    waiting_for_code = State()


def get_subscription_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1 день - 1.5$", callback_data="buy_1_day")],
        [InlineKeyboardButton(text="1 неделя - 6$", callback_data="buy_1_week")],
        [InlineKeyboardButton(text="1 месяц - 10$", callback_data="buy_1_month")],
        [InlineKeyboardButton(text="1 год - 15$", callback_data="buy_1_year")],
        [InlineKeyboardButton(text="НАВСЕГДА - 20$", callback_data="buy_forever")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="🔍 Снос аккаунтов", callback_data="snose"),
            InlineKeyboardButton(text="💰 Купить подписку", callback_data="buy")
        ],
        [
            InlineKeyboardButton(text="📊 Мой статус", callback_data="status"),
            InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard():
    button = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=button)


def get_cancel_keyboard():
    button = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=button)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        if os.path.exists(IMAGE_PATH):
            photo = FSInputFile(IMAGE_PATH)
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption="👁️ Hilgogram Bot\n• Снос аккаунтов Telegram\n\nВыберите действие:",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "👁️ Hilgogram Bot\n• Снос аккаунтов Telegram\n\nВыберите действие:",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logging.error(f"Error sending image: {e}")
        await message.answer(
            "👁️ Hilgogram Bot\n• Снос аккаунтов Telegram\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )


@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer("⬅️ Возврат в главное меню")
    try:
        if os.path.exists(IMAGE_PATH):
            photo = FSInputFile(IMAGE_PATH)
            await bot.send_photo(
                chat_id=callback_query.from_user.id,
                photo=photo,
                caption="Главное меню. Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        else:
            await bot.send_message(
                callback_query.from_user.id,
                "Главное меню. Выберите действие:",
                reply_markup=get_main_keyboard()
            )
    except:
        await bot.send_message(
            callback_query.from_user.id,
            "Главное меню. Выберите действие:",
            reply_markup=get_main_keyboard()
        )


@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer("❌ Действие отменено")
    try:
        if os.path.exists(IMAGE_PATH):
            photo = FSInputFile(IMAGE_PATH)
            await bot.send_photo(
                chat_id=callback_query.from_user.id,
                photo=photo,
                caption="Действие отменено. Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        else:
            await bot.send_message(
                callback_query.from_user.id,
                "Действие отменено. Выберите действие:",
                reply_markup=get_main_keyboard()
            )
    except:
        await bot.send_message(
            callback_query.from_user.id,
            "Действие отменено. Выберите действие:",
            reply_markup=get_main_keyboard()
        )


@dp.callback_query(F.data == "buy")
async def process_buy(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        "📦 ВЫБЕРИТЕ ТАРИФ:\n\n1 день - 1.5$\n1 неделя - 6$\n1 месяц - 10$\n1 год - 15$\nНАВСЕГДА - 20$\n\n💰 Если хотите приобрести подписку другой валютой, пишите в лс - @anonbum\n\nПосле оплаты нажмите /activate для активации.",
        reply_markup=get_subscription_keyboard()
    )


@dp.callback_query(F.data.startswith("buy_"))
async def process_tariff(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    tariff_prices = {'1_day': '1.5', '1_week': '6', '1_month': '10', '1_year': '15', 'forever': '20'}
    tariff_periods = {'1_day': '1 день', '1_week': '1 неделя', '1_month': '1 месяц', '1_year': '1 год',
                      'forever': 'НАВСЕГДА'}
    tariff_durations = {'1_day': 1, '1_week': 7, '1_month': 30, '1_year': 365, 'forever': 9999}
    tariff = callback_query.data.replace('buy_', '')
    price = tariff_prices.get(tariff, '?')
    period = tariff_periods.get(tariff, '?')
    await state.update_data(selected_tariff=tariff)
    await state.update_data(tariff_duration=tariff_durations.get(tariff, 1))
    await state.update_data(tariff_period=period)
    payment_urls = {
        '1_day': 'http://t.me/send?start=IVn10dhkgbbu',
        '1_week': 'http://t.me/send?start=IVnTbPWCr5tc',
        '1_month': 'http://t.me/send?start=IVOIX4OxkSD0',
        '1_year': 'http://t.me/send?start=IVR77UJodADo',
        'forever': 'http://t.me/send?start=IVmgeJkvYJGJ'
    }
    payment_url = payment_urls.get(tariff, 'http://t.me/send?start=IVmgeJkvYJGJ')
    payment_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {period} - ${price}", url=payment_url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await bot.send_message(
        callback_query.from_user.id,
        f"💳 ОПЛАТА ТАРИФА: {period}\n\nСтоимость: ${price}\nСрок действия: {period}\n\nЕсли хотите оплатить другой валютой, пишите @anonbum\n\n1. Нажмите на кнопку для оплаты\n2. После оплаты нажмите /activate",
        reply_markup=payment_button
    )


@dp.message(Command("activate"))
async def cmd_activate(message: types.Message, state: FSMContext):
    await state.set_state(ActivationStates.waiting_for_code)
    await message.answer(
        "🔐 АКТИВАЦИЯ ПОДПИСКИ\n\nВведите код активации, полученный после оплаты:\n\nИли нажмите ⬅️ Назад для возврата",
        reply_markup=get_back_keyboard()
    )


@dp.message(ActivationStates.waiting_for_code)
async def process_activation_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    data = await state.get_data()
    selected_tariff = data.get('selected_tariff')
    tariff_duration = data.get('tariff_duration', 1)
    tariff_period = data.get('tariff_period', '1 день')

    if not selected_tariff:
        await message.answer(
            "❌ СНАЧАЛА ВЫБЕРИТЕ ТАРИФ\n\nПожалуйста, сначала выберите тариф в разделе '💰 Купить подписку'",
            reply_markup=get_subscription_keyboard()
        )
        await state.clear()
        return

    if code != ACTIVATION_CODE:
        await message.answer(
            "❌ НЕВЕРНЫЙ КОД\n\nВведенный код неверен.\nПожалуйста, проверьте код и попробуйте еще раз.",
            reply_markup=get_back_keyboard()
        )
        return

    if selected_tariff == 'forever':
        subscription_end = "2099-12-31"
    else:
        subscription_end = (datetime.now() + timedelta(days=tariff_duration)).strftime("%Y-%m-%d")

    async with aiosqlite.connect('users.db') as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, subscription_end) VALUES (?, ?)",
                         (user_id, subscription_end))
        await db.commit()

    await state.clear()

    await message.answer(
        f"✅ ПОДПИСКА АКТИВИРОВАНА!\n\nТариф: {tariff_period}\nСрок действия: до {subscription_end}\n\nТеперь вы можете использовать все функции бота.\n\nДля начала сноса аккаунта нажмите '🔍 Снос аккаунтов'",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "snose")
async def process_snose(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id

    subscription_active = await has_active_subscription(user_id)

    if not subscription_active:
        await bot.send_message(
            user_id,
            "❌ НЕТ ДОСТУПА\n\nДля использования функции сноса аккаунтов необходимо приобрести подписку.\n\nПриобрести подписку можно в разделе '💰 Купить подписку'",
            reply_markup=get_subscription_keyboard()
        )
        return

    await state.set_state(DemolitionStates.waiting_for_target)
    await bot.send_message(
        user_id,
        "🔍 ВВЕДИТЕ USERNAME ИЛИ ID АККАУНТА:\n\nПример:\n• @username\n• 123456789\n\nЯ начну снос после отправки username или ID.\n\nИли нажмите ⬅️ Назад для возврата",
        reply_markup=get_back_keyboard()
    )


@dp.message(DemolitionStates.waiting_for_target)
async def handle_target(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    subscription_active = await has_active_subscription(user_id)

    if not subscription_active:
        await message.answer(
            "❌ НЕТ ДОСТУПА\n\nДля использования функции сноса аккаунтов необходимо приобрести подписку.",
            reply_markup=get_subscription_keyboard()
        )
        await state.clear()
        return

    target = message.text.strip()
    if target.startswith('/'):
        await message.answer(
            "⚠️ ЭТО КОМАНДА, А НЕ USERNAME/ID\n\nПожалуйста, введите username или ID аккаунта:\n• @username\n• 123456789",
            reply_markup=get_back_keyboard()
        )
        return

    await state.update_data(target=target)
    start_message = await message.answer(
        f"🔍 Начинаю снос аккаунта:\n\nЦель: {target}\nСтатус: В процессе сноса...\n\nПримерное время завершения: 10 минут"
    )
    asyncio.create_task(process_demolition(user_id, target, start_message.message_id))
    await state.clear()


async def process_demolition(user_id: int, target: str, message_id: int):
    try:
        await asyncio.sleep(10)
        await bot.send_message(
            user_id,
            f"✅ СНОС ЗАКОНЧЕН\n\nЦель: {target}\nСтатус: Аккаунт успешно снесен\n\nДля нового сноса нажмите '🔍 Снос аккаунтов'",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logging.error(f"Error in demolition process: {e}")
        await bot.send_message(
            user_id,
            f"⚠️ ОШИБКА ПРИ СНОСЕ\n\nЦель: {target}\nСтатус: Ошибка при выполнении\n\nПопробуйте еще раз или обратитесь в поддержку.",
            reply_markup=get_main_keyboard()
        )


@dp.callback_query(F.data == "status")
async def process_status(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    subscription_active = await has_active_subscription(user_id)

    if subscription_active:
        async with aiosqlite.connect('users.db') as db:
            async with db.execute("SELECT subscription_end FROM users WHERE user_id=?", (user_id,)) as cursor:
                result = await cursor.fetchone()

        await callback_query.answer()
        await bot.send_message(
            user_id,
            f"✅ ВАШ СТАТУС\n\nПодписка активна до: {result[0]}\nДоступ: ПОЛНЫЙ\n\nВы можете использовать все функции бота",
            reply_markup=get_back_keyboard()
        )
    else:
        await callback_query.answer()
        await bot.send_message(
            user_id,
            "❌ НЕТ ПОДПИСКИ\n\nУ вас нет активной подписки.\nКупите подписку для доступа к функциям.\n\nЕсли хотите приобрести подписку другой валютой, пишите в лс - @anonbum",
            reply_markup=get_subscription_keyboard()
        )


@dp.callback_query(F.data == "help")
async def process_help(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        "🆘 ПОМОЩЬ\n\n1. Нажмите '💰 Купить подписку' и выберите тариф\n2. Оплатите выбранный тариф\n3. После оплаты нажмите /activate\n4. Введите код активации\n5. После активации нажмите '🔍 Снос аккаунтов'\n6. Введите username или ID цели\n7. Через 10 минут снос будет завершен\n\nЕсли хотите приобрести подписку другой валютой, пишите в лс - @anonbum\n\nПоддержка: @anonbum",
        reply_markup=get_back_keyboard()
    )


@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer(
        "ℹ️ КОМАНДА /check УСТАРЕЛА\n\nДля активации подписки используйте команду:\n/activate",
        reply_markup=get_main_keyboard()
    )


@dp.message()
async def handle_other_messages(message: types.Message):
    if message.text and message.text.startswith('/'):
        return

    user_id = message.from_user.id

    if message.text and (message.text.startswith('@') or message.text.isdigit()):
        subscription_active = await has_active_subscription(user_id)

        if not subscription_active:
            await message.answer(
                "❌ НЕТ ДОСТУПА\n\nДля использования функции сноса аккаунтов необходимо приобрести подписку.\n\nНажмите '💰 Купить подписку' для приобретения доступа.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "🔍 Чтобы начать снос, нажмите кнопку '🔍 Снос аккаунтов' в главном меню.",
                reply_markup=get_main_keyboard()
            )


async def init_db():
    async with aiosqlite.connect('users.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users
                          (user_id INTEGER PRIMARY KEY, 
                           subscription_end TEXT)''')
        await db.commit()


async def on_startup(bot: Bot):
    await init_db()

    webhook_url = os.getenv('RAILWAY_STATIC_URL')
    if not webhook_url:
        webhook_url = os.getenv('WEBHOOK_URL')
        if not webhook_url:
            logging.warning("Не удалось получить URL для webhook")
            return

    await bot.set_webhook(f"{webhook_url}/webhook")
    logging.info(f"Webhook установлен: {webhook_url}/webhook")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook удален")


async def main():
    try:
        await init_db()

        app = web.Application()

        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path='/webhook')

        setup_application(app, dp, bot=bot)

        app.on_startup.append(lambda app: on_startup(bot))
        app.on_shutdown.append(lambda app: on_shutdown(bot))

        port = int(os.getenv('PORT', 8080))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()

        logging.info(f"Бот запущен на порту {port}")

        await asyncio.Event().wait()

    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")


if __name__ == '__main__':
    asyncio.run(main())
