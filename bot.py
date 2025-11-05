from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from db_manager import init_db, get_db, get_or_create_user, save_test_to_db, get_test_questions_from_db, save_quiz_result, get_leaderboards, Test 
from config import TELEGRAM_BOT_TOKEN, ADMIN_ID
from parser import parse_text_to_quiz
import random
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 

user_quiz_state = {}


def get_db_session(context: ContextTypes.DEFAULT_TYPE):
    """Context'dan DB sessiyasini oladi."""
    try:
        return next(get_db())
    except Exception as e:
        print(f"DB sessiyasini olishda xatolik: {e}")
        return None

async def add_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin /addtest buyrug'ini ishga tushirganda chaqiriladi."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu buyruq faqat adminlarga ruxsat etilgan.")
        return
    
    user_quiz_state[update.effective_user.id] = {'step': 'awaiting_test_name'}
    await update.message.reply_text("Yangi test uchun **nom** kiriting (masalan: Geografiya_101).")


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adminning matn/nom kiritishini boshqaradi."""
    user_id = update.effective_user.id
    state = user_quiz_state.get(user_id, {})
    step = state.get('step')
    
    if step == 'awaiting_test_name' and update.message.text:
        test_name = update.message.text.strip()
        user_quiz_state[user_id]['step'] = 'awaiting_test_content'
        user_quiz_state[user_id]['test_name'] = test_name
        await update.message.reply_text(
            f"Test nomi **{test_name}** qabul qilindi.\n\n"
            "Endi **matnni** quyidagi formatda yuboring (Savollar raqam bilan boshlanishi kerak):\n"
            "1. Savol matni?\n*To'g'ri javob\nNoto'g'ri javob\nNoto'g'ri javob\n"
            "2. Boshqa savol?\n*To'g'ri javob"
        )
        return

    elif step == 'awaiting_test_content' and update.message.text:
        text_content = update.message.text
        parsed_questions = parse_text_to_quiz(text_content)
        
        if not parsed_questions:
            await update.message.reply_text("Xato: Matndan savollar ajratilmadi. Formatni tekshiring.")
            return
            
        test_name = state['test_name']
        db: Session = get_db_session(context)
        
        if not db:
            await update.message.reply_text("DB ulanishida xatolik yuz berdi. Iltimos, serverni tekshiring.")
            return
            
        try:
            test_id = save_test_to_db(db, test_name, parsed_questions)
            
            await update.message.reply_text(
                f"✅ Test **'{test_name}'** (ID: {test_id}) muvaffaqiyatli saqlandi!\n"
                f"Jami **{len(parsed_questions)}** ta savol qo'shildi."
            )
        except IntegrityError:
            await update.message.reply_text(f"Xato: **'{test_name}'** nomli test allaqachon mavjud.")
        except Exception as e:
            print(f"DB Save Error: {e}")
            await update.message.reply_text(f"Xato: Testni saqlashda kutilmagan xato yuz berdi: ({e})")
        finally:
            del user_quiz_state[user_id]
        return



async def take_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi /takequiz buyrug'ini beradi."""
    user_id = update.effective_user.id
    db: Session = get_db_session(context)
    
    if not db: return 
    
    available_tests = db.query(Test.name).all()
    available_tests = [t[0] for t in available_tests]
    
    if not available_tests:
        await update.message.reply_text("Hozirda mavjud testlar yo'q.")
        return

    buttons = [[InlineKeyboardButton(name, callback_data=f"take_{name}")] for name in available_tests]
    keyboard = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text("Qaysi testni olishni xohlaysiz?", reply_markup=keyboard)


async def start_quiz_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quizni boshlash uchun tanlangan test bo'yicha."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    db: Session = get_db_session(context)
    
    if not db: 
        await query.edit_message_text("DB ulanishida xatolik yuz berdi.")
        return
    
    if query.data.startswith("take_"):
        test_name = query.data.split("take_")[1]
        
        questions, test_id = get_test_questions_from_db(db, test_name)
        
        if not questions:
            await query.edit_message_text(f"Test topilmadi: {test_name}")
            return
            
        update_info = query.from_user
        get_or_create_user(db, user_id, update_info)
        
        random.shuffle(questions) 
        
        state = user_quiz_state.get(user_id, {})
        state['step'] = 'in_quiz'
        state['test_name'] = test_name
        state['test_id'] = test_id
        state['questions'] = questions
        state['current_q_index'] = 0
        state['correct_answers'] = 0
        state['incorrect_answers'] = 0
        user_quiz_state[user_id] = state
        
        await present_question(update, context, query, 0)


async def present_question(update, context, query, q_index):
    """Belgilangan indeksdagi savolni foydalanuvchiga ko'rsatadi."""
    user_id = query.from_user.id
    state = user_quiz_state[user_id]
    
    current_q_data = state['questions'][q_index]
    
    
    labels = ['A', 'B', 'C', 'D', 'E', 'F']
    options_pool = [current_q_data['correct_answer']] + current_q_data['options']
    random.shuffle(options_pool)
    
    selected_options = options_pool[:4]
    
    buttons = []
    for i, option_text in enumerate(selected_options):
        label = labels[i]
        
        is_correct = (option_text == current_q_data['correct_answer'])
        callback_data = f"ans_next_{q_index + 1}_{is_correct}"
        
        buttons.append(InlineKeyboardButton(f"{label}. {option_text}", callback_data=callback_data))
        
    
    question_text = f"**{q_index + 1}-Savol ({state['test_name']}):**\n{current_q_data['question']}"
    
    keyboard = InlineKeyboardMarkup([[btn] for btn in buttons])
    
    if query.message:
        await query.edit_message_text(question_text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(question_text, reply_markup=keyboard, parse_mode='Markdown')


async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quiz jarayonidagi callbacklarni boshqaradi."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    db: Session = get_db_session(context)
    
    if query.data.startswith("take_"):
        await start_quiz_selection(update, context)
        return

    if query.data == "show_leaderboard":
        await show_leaderboard(update, context)
        return

    state = user_quiz_state.get(user_id)
    
    if state and state['step'] == 'in_quiz' and query.data.startswith("ans_next_"):
        try:
            parts = query.data.split('_')
            next_q_index = int(parts[2])
            is_correct = parts[3] == 'True' 

            current_q_index = state['current_q_index']
            

            if is_correct:
                state['correct_answers'] += 1
                result_text = "✅ **To'g'ri javob!**"
            else:
                state['incorrect_answers'] += 1
                result_text = "❌ **Noto'g'ri.**"
            
            
            if next_q_index < len(state['questions']):
                state['current_q_index'] = next_q_index
                await present_question(update, context, query, next_q_index)
                
            else:
                await finalize_quiz(update, context, query, state, result_text, db)
        
        except Exception as e:
            print(f"Quiz xatosi: {e}")
            await query.edit_message_text("Quizda kutilmagan xatolik yuz berdi. Iltimos, /takequiz orqali qayta urinib ko'ring.")
            if user_id in user_quiz_state:
                del user_quiz_state[user_id]

async def finalize_quiz(update, context, query, state, last_result_text, db: Session):
    """Quiz tugaganidan keyin natijani ko'rsatadi va DB ga saqlaydi."""
    user_id = query.from_user.id
    
    total_correct = state['correct_answers']
    total_incorrect = state['incorrect_answers']
    total_score = total_correct + total_incorrect
    
    save_quiz_result(db, user_id, state['test_id'], total_correct, total_score)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Reytingni Ko'rish", callback_data="show_leaderboard")]
    ])
    
    final_message = (
        f"🎉 **Quiz yakunlandi!**\n\n"
        f"{last_result_text}\n\n"
        f"Jami natijalar ({state['test_name']}):\n"
        f"🔹 To'g'ri javoblar: **{total_correct}**\n"
        f"🔸 Noto'g'ri javoblar: **{total_incorrect}**\n"
        f"💯 Umumiy ishlangan savol: **{total_score}**"
    )
    
    await query.edit_message_text(final_message, reply_markup=keyboard, parse_mode='Markdown')
    del user_quiz_state[user_id] 



async def list_tests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin uchun mavjud testlarni ko'rsatadi."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu buyruq faqat adminlarga ruxsat etilgan.")
        return
        
    db: Session = get_db_session(context)
    if not db:
        await update.message.reply_text("DB ulanishida xatolik yuz berdi.")
        return

    test_names = db.query(Test.name).all() 
    test_names = [t[0] for t in test_names]

    if not test_names:
        await update.message.reply_text("Hozirda saqlangan testlar mavjud emas.")
        return
        
    message = "Saqlangan testlar ro'yxati:\n\n"
    for name in test_names:
        message += f"- **{name}**\n"
        
    await update.message.reply_text(message, parse_mode='Markdown')

def format_leaderboard_message(title, data, is_global=False):
    """Reytingni tayyorlash."""
    message = f"🏆 **{title}** 🏆\n\n"
    
    if is_global:
     
        for i, (user_id, score) in enumerate(data):
            message += f"{i+1}. <a href='tg://user?id={user_id}'>Foydalanuvchi ID:{user_id}</a>: **{score}** to'g'ri\n"
    else:
 
        for i, item in enumerate(data):
            message += f"{i+1}. <a href='tg://user?id={item['id']}'>{item['username']}</a>: **{item['score']}** to'g'ri\n"
            
    return message

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reytingni ko'rsatadi."""
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
        
    db: Session = get_db_session(context)
    
    if not db:
        target = query or update.message
        await target.reply_text("DB ulanishida xatolik yuz berdi.")
        return
        
    global_lb, monthly_lb = get_leaderboards(db)
    
    global_msg = format_leaderboard_message("Global Reyting (Umumiy To'g'ri Javob)", global_lb, is_global=True)
    monthly_msg = format_leaderboard_message("Oylik Reyting (Joriy Oy)", monthly_lb, is_global=False)
    
    full_message = global_msg + "\n" + "-"*30 + "\n" + monthly_msg
    
    if query:
        await query.edit_message_text(full_message, parse_mode='HTML')
    else:
     
        await update.message.reply_html(full_message)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'iga javob beradi va DB da foydalanuvchini yaratadi."""
    user_id = update.effective_user.id
    db: Session = get_db_session(context)
    
    if not db:
        await update.message.reply_text("Bot serveri va DB ulanishida muammo bor.")
        return
    
    update_info = update.effective_user
    get_or_create_user(db, user_id, update_info)
    
    response = (
        "Assalomu alaykum! Men quiz generator botman.\n\n"
        "**Adminlar uchun (ID: {ADMIN_ID}):**\n"
        "/addtest - Yangi test matnini yuboring.\n"
        "/listtests - Mavjud testlarni ko'rish.\n\n"
        "**Foydalanuvchilar uchun:**\n"
        "/takequiz - Quiz olish.\n"
        "/leaderboard - Reytingni ko'rish."
    ).format(ADMIN_ID=ADMIN_ID)
    
    await update.message.reply_text(response)


def main() -> None:
    """Botni ishga tushiradi."""

    init_db()


    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("addtest", add_test_command)) 
    application.add_handler(CommandHandler("listtests", list_tests_command))
    application.add_handler(CommandHandler("takequiz", take_quiz_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID), handle_admin_message))
    
    application.add_handler(CallbackQueryHandler(handle_quiz_callback))


    print("Bot ishga tushirildi va DB sozlandi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()