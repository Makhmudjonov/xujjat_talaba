import os
import re
import logging
import html
from aiogram import Bot, Router, types
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from aiogram.exceptions import TelegramAPIError

from apps.models import Student, TestSession, Application

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize router
router = Router()

# Load CHANNEL_ID from environment variable
CHANNEL_ID = os.getenv("CHANNEL_ID", "@tsmuuz")

# HEMIS ID validation pattern (12-character alphanumeric)
HEMIS_ID_PATTERN = re.compile(r'^[A-Z0-9]{12}$')

# GPA mapping for scoring
GPA_MAP = {
    5.0: 10.0, 4.9: 9.7, 4.8: 9.3, 4.7: 9.0, 4.6: 8.7,
    4.5: 8.3, 4.4: 8.0, 4.3: 7.7, 4.2: 7.3, 4.1: 7.0,
    4.0: 6.7, 3.9: 6.3, 3.8: 6.0, 3.7: 5.7, 3.6: 5.3, 3.5: 5.0
}

# Utility function for safe attribute access
def safe_getattr(obj, attr, default=''):
    return getattr(obj, attr, default) if obj else default

# Sync-to-async wrappers for database queries
@sync_to_async(thread_sensitive=False)
def get_student_by_hemis_id(hemis_id):
    return Student.objects.select_related(
        "university1", "faculty", "specialty", "group_hemis", "level"
    ).prefetch_related(
        "gpa_records", "applications__items__score", "applications__items__direction"
    ).get(student_id_number=hemis_id)

@sync_to_async(thread_sensitive=False)
def get_student_applications(student):
    return student.applications.order_by('-submitted_at').first()

@sync_to_async(thread_sensitive=False)
def get_test_session(student):
    return TestSession.objects.filter(student=student).first()

@sync_to_async(thread_sensitive=False)
def get_application_items(application):
    return list(application.items.select_related('score', 'direction').all())

@sync_to_async(thread_sensitive=False)
def get_direction_name(item):
    return safe_getattr(item.direction, 'name')

@sync_to_async(thread_sensitive=False)
def get_score_value(item):
    return item.score.value if item.score else 0.0

@sync_to_async(thread_sensitive=False)
def get_gpa(student):
    return float(student.gpa) if student.gpa else 0.0

@sync_to_async(thread_sensitive=False)
def get_application_type(application):
    app_type = safe_getattr(application, 'application_type', 'Unknown')
    logger.info(f"Application type: {app_type} (type: {type(app_type)})")
    return str(app_type) if app_type is not None else 'Unknown'

# FSM for handling HEMIS ID input
class HEMISForm(StatesGroup):
    waiting_for_id = State()

@router.message(CommandStart())
async def start_handler(message: types.Message, bot: Bot, state: FSMContext):
    """Handle /start command and check channel membership."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer(
                f"Xush kelibsiz, {html.escape(message.from_user.full_name)}! 👋\n"
                f"Natijani ko‘rish uchun iltimos, HEMIS ID yuboring.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            await state.set_state(HEMISForm.waiting_for_id)
        else:
            channel_link = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
            await message.answer(
                f"Salom {html.escape(message.from_user.full_name)}!\n\n"
                f"Iltimos, kanalga a'zo bo‘ling: ",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(text='Kanalga o‘tish', url=channel_link)
                    ]]
                ),
                parse_mode="HTML"
            )
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in start_handler: {e}")
        await message.answer("A’zolikni tekshirishda xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.")
    except Exception as e:
        logger.error(f"Unexpected error in start_handler: {e}", exc_info=True)
        await message.answer("Noma’lum xatolik yuz berdi.")

@router.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    """Handle /cancel command to clear FSM state."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Hozirda faol so‘rov yo‘q.")
        return
    await state.clear()
    await message.answer(
        "So‘rov bekor qilindi. Yangi so‘rov uchun /start ni bosing.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(HEMISForm.waiting_for_id)
async def receive_hemis_id(message: types.Message, state: FSMContext):
    """Handle HEMIS ID input and fetch student data."""
    if not message.text:
        await message.answer("Iltimos, HEMIS ID ni matn sifatida yuboring.")
        return

    hemis_id = message.text.strip()
    if not HEMIS_ID_PATTERN.match(hemis_id):
        await message.answer("Noto‘g‘ri HEMIS ID formati. Iltimos, 12 belgidan iborat to‘g‘ri ID kiriting.")
        return

    try:
        logger.info(f"Fetching student data for HEMIS ID: {hemis_id}")
        # Fetch student with related data
        student = await get_student_by_hemis_id(hemis_id)

        # Get latest application
        logger.info(f"Fetching latest application for student: {student.full_name}")
        # application = await get_student_applications(student)
        # if not application:
        #     await message.answer("Sizning arizangiz topilmadi.")
        #     await state.clear()
        #     return

        # Fetch application type
        # application_type = await get_application_type(application)

        # Build response
        response_text = (
            f"<b>FISH:</b> {html.escape(student.full_name)}\n"
            f"<b>OTM:</b> {html.escape(safe_getattr(student.university1, 'name'))}\n"
            f"<b>Fakultet:</b> {html.escape(safe_getattr(student.faculty, 'name'))}\n"
            f"<b>Mutaxassislik:</b> {html.escape(safe_getattr(student.specialty, 'name'))}\n"
            f"<b>Guruh:</b> {html.escape(safe_getattr(student.group_hemis, 'name'))}\n"
            f"<b>Kurs:</b> {html.escape(safe_getattr(student.level, 'name'))}\n"
            # f"<b>Grant turi:</b> {html.escape(application_type)}\n"
            # f"<b>Yuborilgan sana:</b> {application.submitted_at.strftime('%Y-%m-%d %H:%M') if application.submitted_at else ''}\n\n"
        )

        total_score = 0.0
        scores_text = "<b>Ballar:</b>\n"
        logger.info("Fetching application items")
        # items = await get_application_items(application)

        # for item in items:
        #     # Fetch direction name
        #     dir_name = await get_direction_name(item)
        #     if not dir_name:
        #         continue
        #     dir_name_lower = dir_name.lower()

        #     if dir_name_lower == "kitobxonlik madaniyati":
        #         logger.info(f"Fetching test session for student: {student.full_name}")
        #         test = await get_test_session(student)
        #         if test:
        #             score = await sync_to_async(lambda: round(float(test.score) * 0.2, 2))()
        #             scores_text += f"{html.escape(dir_name)}: {score} (test * 0.2)\n"
        #             total_score += score
        #         else:
        #             scores_text += f"{html.escape(dir_name)}: Mavjud emas\n"

        #     elif dir_name_lower == "talabaning akademik o‘zlashtirishi":
        #         gpa = await get_gpa(student)
        #         gpa_score = GPA_MAP.get(round(gpa, 1), 0.0)
        #         scores_text += f"{html.escape(dir_name)}: {gpa_score} (GPA asosida)\n"
        #         total_score += gpa_score
        #     else:
        #         score = await get_score_value(item)
        #         scores_text += f"{html.escape(dir_name)}: {score}\n"
        #         if isinstance(score, (int, float)):
        #             total_score += score

        response_text += scores_text
        response_text += f"\n<b>Jami ball:</b> {round(total_score, 2)}\n"
        response_text += f"<b>Jami * 0.2:</b> {round(total_score * 0.2, 2)}"

        await message.answer(response_text, parse_mode="HTML")

    except ObjectDoesNotExist:
        logger.warning(f"Student not found for HEMIS ID: {hemis_id}")
        await message.answer("Bunday HEMIS ID topilmadi.")
    except TelegramAPIError as e:
        logger.error(f"Telegram API error in receive_hemis_id: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.")
    except Exception as e:
        # logger.error(f"Unexpected error in receive_hemis_id: {e}, application_type: {type(application_type)}", exc_info=True)
        await message.answer("Ma’lumotni olishda xatolik yuz berdi.")
    finally:
        await state.clear()

@router.message(HEMISForm.waiting_for_id)
async def invalid_input_handler(message: types.Message):
    """Handle invalid input during HEMIS ID state."""
    await message.answer("Iltimos, faqat HEMIS ID ni matn sifatida yuboring.")