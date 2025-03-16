import logging
import os
import sys
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram.error import TimedOut, NetworkError, Forbidden, TelegramError
import asyncio
import traceback
from datetime import datetime

# Добавляем родительскую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bot_Core.responders.generator import generate_responder, generate_interview_response
from Bot_Core.validation.validator import ProfileValidator
from Bot_Core.data.database import DatabaseManager

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
log_file = f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Логируем важную информацию при запуске
logger.info("Бот запускается...")
logger.info(f"Версия Python: {sys.version}")
logger.info(f"Рабочая директория: {os.getcwd()}")
logger.info(f"Файл лога: {log_file}")

# Проверяем наличие токена
if not os.getenv('TELEGRAM_BOT_TOKEN'):
    logger.error("Токен бота не найден в переменных окружения!")
    sys.exit(1)
else:
    logger.info("Токен бота успешно загружен")

# Состояния разговора
CHOOSING_RESPONDENT, WAITING_PROFESSION, WAITING_AGE, INTERVIEW, HYPOTHESIS_INPUT = range(5)

# Инициализация компонентов
db = DatabaseManager()
validator = ProfileValidator()

async def start(update: Update, context):
    """Обработчик команды /start"""
    try:
        logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
        keyboard = [
            [
                InlineKeyboardButton("Создать респондента", callback_data='new_responder'),
                InlineKeyboardButton("Начать интервью", callback_data='start_interview')
            ],
            [InlineKeyboardButton("Анализ результатов", callback_data='analysis')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в Custos AI Bot!\n\n"
            "Я помогу вам:\n"
            "🎯 Создавать цифровых респондентов\n"
            "🗣 Проводить интервью\n"
            "📊 Анализировать результаты\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
        logger.debug("Отправлено приветственное сообщение")
        return CHOOSING_RESPONDENT
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def button_handler(update: Update, context):
    """Обработчик нажатий на кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        
        logger.info(f"Получен callback_data: {query.data} от пользователя {update.effective_user.id}")
        
        if query.data == 'new_responder':
            keyboard = [
                [
                    InlineKeyboardButton("Скептик", callback_data='trait_skeptic'),
                    InlineKeyboardButton("Болтливый", callback_data='trait_chatty')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Выберите тип респондента:",
                reply_markup=reply_markup
            )
            logger.debug("Отправлено меню выбора типа респондента")
            return CHOOSING_RESPONDENT
        
        elif query.data.startswith('trait_'):
            trait = query.data.split('_')[1]
            logger.info(f"Выбран тип респондента: {trait}")
            
            # Сохраняем выбранный trait в контексте пользователя
            context.user_data['trait'] = trait
            
            await query.message.reply_text(
                "Укажите профессию респондента (например: бухгалтер, product manager, разработчик):"
            )
            return WAITING_PROFESSION
    except Exception as e:
        logger.error(f"Ошибка в обработчике button_handler: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def handle_profession(update: Update, context):
    """Обработчик ввода профессии"""
    try:
        profession = update.message.text
        context.user_data['profession'] = profession
        logger.info(f"Получена профессия: {profession}")
        
        await update.message.reply_text(
            "Укажите возраст респондента (число от 18 до 80):"
        )
        return WAITING_AGE
    except Exception as e:
        logger.error(f"Ошибка в обработчике handle_profession: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def handle_age(update: Update, context):
    """Обработчик ввода возраста"""
    try:
        try:
            age = int(update.message.text)
            if age < 18 or age > 80:
                await update.message.reply_text(
                    "Возраст должен быть от 18 до 80 лет. Попробуйте еще раз:"
                )
                return WAITING_AGE
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите корректное число. Попробуйте еще раз:"
            )
            return WAITING_AGE

        context.user_data['age'] = age
        logger.info(f"Получен возраст: {age}")

        # Создаем респондента
        await update.message.reply_text("🤖 Генерирую респондента...")
        
        try:
            result = await generate_responder(
                age=context.user_data['age'],
                profession=context.user_data['profession'],
                trait=context.user_data['trait']
            )
            
            if not result['success']:
                logger.error(f"Ошибка при создании респондента: {result['message']}")
                await update.message.reply_text(result['message'])
                return CHOOSING_RESPONDENT

            profile = result['data']
            
            # Сохраняем в базу
            respondent = db.create_respondent(
                name=profile['name'],
                age=profile['age'],
                profession=profile['profession'],
                trait=context.user_data['trait'],
                profile=profile
            )
            
            # Сохраняем ID респондента в контексте
            context.user_data['current_respondent_id'] = respondent.id
            
            # Отправляем информацию о респонденте
            await update.message.reply_text(result['message'])
            return INTERVIEW

        except Exception as e:
            logger.error(f"Ошибка при генерации респондента: {str(e)}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Произошла ошибка при создании респондента. Попробуйте еще раз."
            )
            return CHOOSING_RESPONDENT

    except Exception as e:
        logger.error(f"Ошибка в обработчике handle_age: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def handle_interview_message(update: Update, context):
    """Обработчик сообщений в режиме интервью"""
    try:
        question = update.message.text
        logger.info(f"Получен вопрос: {question}")
        
        # Получаем текущего респондента
        respondent_id = context.user_data.get('current_respondent_id')
        if not respondent_id:
            await update.message.reply_text(
                "❌ Сессия истекла. Пожалуйста, создайте нового респондента."
            )
            return CHOOSING_RESPONDENT
            
        respondent = db.get_respondent(respondent_id)
        if not respondent:
            await update.message.reply_text(
                "❌ Респондент не найден. Пожалуйста, создайте нового респондента."
            )
            return CHOOSING_RESPONDENT
            
        # Генерируем ответ от респондента
        try:
            await update.message.reply_text(
                "🤔 Думаю над ответом..."
            )
            
            answer = await generate_interview_response(question, respondent.profile)
            
            # Сохраняем ответ в базу данных
            current_interview = context.user_data.get('current_interview')
            if not current_interview:
                # Создаем новое интервью, если его нет
                current_interview = db.create_interview(
                    respondent_id=respondent_id,
                    hypothesis=context.user_data.get('hypothesis', 'Не указана')
                )
                context.user_data['current_interview'] = current_interview
            
            # Добавляем ответ к интервью
            db.add_response(current_interview.id, {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            })
            
            await update.message.reply_text(answer)
            return INTERVIEW
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации ответа. Попробуйте задать вопрос еще раз."
            )
            return INTERVIEW
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике handle_interview_message: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def error_handler(update: Update, context):
    """Обработчик ошибок"""
    logger.error(f"Update {update} вызвал ошибку {context.error}")
    logger.error(traceback.format_exc())
    
    if isinstance(context.error, TimedOut):
        logger.warning("Ошибка таймаута соединения")
        logger.info("Переподключение через 1 секунду...")
        await asyncio.sleep(1)
    elif isinstance(context.error, NetworkError):
        logger.warning("Ошибка сети")
        logger.info("Переподключение через 5 секунд...")
        await asyncio.sleep(5)
    elif isinstance(context.error, Forbidden):
        logger.error("Ошибка доступа к боту")
        logger.error("Проверьте права бота и токен")
    elif isinstance(context.error, TelegramError):
        logger.error(f"Ошибка Telegram API: {context.error}")
    else:
        logger.error(f"Неизвестная ошибка: {context.error}")
        logger.error(traceback.format_exc())

def main():
    """Запуск бота"""
    try:
        logger.info("Инициализация бота...")
        
        # Создаем приложение с расширенными таймаутами
        application = (
            Application.builder()
            .token(os.getenv('TELEGRAM_BOT_TOKEN'))
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .get_updates_read_timeout(30)
            .get_updates_connect_timeout(30)
            .get_updates_write_timeout(30)
            .build()
        )
        logger.info("Приложение создано успешно")

        # Обработчики команд
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                CHOOSING_RESPONDENT: [
                    CallbackQueryHandler(button_handler)
                ],
                WAITING_PROFESSION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profession)
                ],
                WAITING_AGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)
                ],
                INTERVIEW: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_interview_message)
                ],
            },
            fallbacks=[CommandHandler('start', start)],
            per_message=False
        )

        application.add_handler(conv_handler)
        logger.info("Обработчики команд добавлены")
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        logger.info("Обработчик ошибок добавлен")

        # Запуск бота
        logger.info("Запуск бота...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main() 