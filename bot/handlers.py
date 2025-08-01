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
    logger.info(f"Querying applications for student: {student}")
    return student.applications.select_related('application_type').order_by('-submitted_at').first()

@sync_to_async(thread_sensitive=False)
def get_application_items(application):
    logger.info("Querying application items")
    return list(application.items.select_related('direction').all())

@sync_to_async(thread_sensitive=False)
def get_direction_name(item):
    dir_name = safe_getattr(item.direction, 'name')
    logger.info(f"Direction name: {dir_name}")
    return dir_name

@sync_to_async(thread_sensitive=False)
def get_test_result(item):
    result = item.test_result if item.test_result is not None else 0.0
    logger.info(f"Test result: {result}")
    return float(result)

@sync_to_async(thread_sensitive=False)
def get_gpa_score(item):
    score = item.gpa_score if item.gpa_score is not None else 0.0
    logger.info(f"GPA score: {score}")
    return float(score)

@sync_to_async(thread_sensitive=False)
def get_gpa(student):
    gpa = float(student.gpa) if student.gpa else 0.0
    logger.info(f"Student GPA: {gpa}")
    return gpa

@sync_to_async(thread_sensitive=False)
def get_application_type(application):
    app_type = safe_getattr(application, 'application_type')
    logger.info(f"Raw application type: {app_type} (type: {type(app_type)})")
    return str(app_type) if app_type is not None else 'Unknown'

@sync_to_async(thread_sensitive=False)
def get_submitted_at(application):
    logger.info(f"Accessing submitted_at for application: {application}")
    return application.submitted_at.strftime('%Y-%m-%d %H:%M') if application.submitted_at else ''

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

        # Fetch student fields
        full_name = await safe_getattr(student, 'full_name')
        university_name = await safe_getattr(student.university1, 'name')
        faculty_name = await safe_getattr(student.faculty, 'name')
        specialty_name = await safe_getattr(student.specialty, 'name')
        specialty_code = await safe_getattr(student.specialty, 'code')
        group_hemis_name = await safe_getattr(student.group_hemis, 'name')
        group_hemis_lang = await safe_getattr(student.group_hemis, 'lang')
        level_name = await safe_getattr(student.level, 'name')
        group = await safe_getattr(student, 'group')

        # Get latest application
        logger.info(f"Fetching latest application for student: {student.full_name}")

        application = await get_student_applications(student)
        if not application:
            logger.warning("No application found for student")
            await message.answer("Sizning arizangiz topilmadi.")
            await state.clear()
            return
        
        # Fetch application fields
        application_type = await get_application_type(application)
        submitted_at = await get_submitted_at(application)

        response_text = (
            f"<b>FISH:</b> {html.escape(full_name)}\n"
            f"<b>OTM:</b> {html.escape(university_name)}\n"
            f"<b>Fakultet:</b> {html.escape(faculty_name)}\n"
            f"<b>Mutaxassislik:</b> {html.escape(specialty_name)}\n"
            f"<b>Ta'lim shifri:</b> {html.escape(specialty_code)}\n"
            f"<b>Guruh:</b> {html.escape(group_hemis_name)}\n"
            f"<b>Ta'lim tili:</b> {html.escape(group_hemis_lang)}\n"
            f"<b>Kurs:</b> {html.escape(level_name)}\n"
            f"<b>Guruh (qo'shimcha):</b> {html.escape(group)}\n"
            f"<b>Grant turi:</b> {html.escape(application_type)}\n"
            f"<b>Yuborilgan sana:</b> {html.escape(submitted_at)}\n\n"
        )

        total_score = 0.0
        scores_text = "<b>Ballar:</b>\n"
        items = await get_application_items(application)

        for item in items:
            dir_name = await get_direction_name(item)
            if not dir_name:
                continue
            dir_name_lower = dir_name.lower()

            if dir_name_lower == "kitobxonlik madaniyati":
                score = await get_test_result(item)
                if score:
                    score = round(score * 0.2, 2)
                    scores_text += f"{html.escape(dir_name)}: {score} (test * 0.2)\n"
                    total_score += score
                else:
                    scores_text += f"{html.escape(dir_name)}: Mavjud emas\n"
            elif dir_name_lower == "talabaning akademik o‘zlashtirishi":
                score = await get_gpa_score(item)
                if score:
                    scores_text += f"{html.escape(dir_name)}: {score} (GPA asosida)\n"
                    total_score += score
                else:
                    gpa = await get_gpa(student)
                    gpa_score = GPA_MAP.get(round(gpa, 1), 0.0)
                    scores_text += f"{html.escape(dir_name)}: {gpa_score} (GPA asosida)\n"
                    total_score += gpa_score
            else:
                score = await get_test_result(item)
                scores_text += f"{html.escape(dir_name)}: {score if score else '-'}\n"
                if isinstance(score, (int, float)) and score:
                    total_score += score

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