import os
import asyncio
import requests
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# مفاتيح الوصول (يفضل عبر متغيرات بيئية على البيئة الحية)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8110119856:AAEKyEiIlpHP2e-xOQym0YHkGEBLRgyG_wA")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCbKhGJ8HJLDa_mZ8VZoau8mH1Yz2-KPmY")

# نهاية العنوان لإصدار v1beta2 من Gemini
GEMINI_URL = (
    "https://generativelanguage.googleapis.com"
    "/v1beta2/models/gemini-pro:generateText"
    f"?key={GEMINI_API_KEY}"
)

# امتدادات الملفات بناءً على الاسم
EXT_MAP = {
    "php": "php",
    "py": "py",
    "js": "js",
    "html": "html"
}


# لوحة الأزرار الرئيسية
main_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔨 بناء مشروع", callback_data="build_project"),
    ],
    [
        InlineKeyboardButton("✍️ اكتب كود", callback_data="write_code"),
        InlineKeyboardButton("🧪 اختبر الكود", callback_data="test_code")
    ],
    [
        InlineKeyboardButton("❓ اسأل سؤال", callback_data="ask_question")
    ]
])

# لوحة اختيار لغة الكود بعد "✍️ اكتب كود"
language_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("PHP", callback_data="lang_php"),
        InlineKeyboardButton("Python", callback_data="lang_python")
    ],
    [
        InlineKeyboardButton("JavaScript", callback_data="lang_js"),
        InlineKeyboardButton("HTML/CSS", callback_data="lang_html")
    ]
])

# لوحة اختيار نوع المشروع بعد "🔨 بناء مشروع"
project_type_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("موقع ويب", callback_data="project_web"),
        InlineKeyboardButton("بوت تلجرام", callback_data="project_bot")
    ]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك! اختر من القائمة:",
        reply_markup=main_keyboard
    )

# وظيفة التلويح بالابتسامة أثناء إنشاء الملف
async def blink_message(bot, chat_id, message_id, filename, stop_event):
    state = True
    while not stop_event.is_set():
        text = f"⏳ جاري العمل على {filename}" + (" 😁" if state else "")
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
        except:
            pass
        state = not state
        await asyncio.sleep(0.5)


# بدء إنشاء ملف واحد ثم انتظار تفاعل "التالي"
async def process_next_file(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    user_data = context.user_data
    files = user_data.get("file_list", [])
    idx = user_data.get("current_file_index", 0)
    desc = user_data.get("project_desc", "")
    proj_type = user_data.get("project_type", "")

    # إذا اكتمل كل الملفات
    if idx >= len(files):
        msg_id = user_data.get("progress_msg_id")
        await context.bot.edit_message_text(
            "🎉 تم إنشاء جميع الملفات بنجاح!",
            chat_id=chat_id, message_id=msg_id
        )
        return

    filename = files[idx]
    # أرسل الرسالة الأولى مع تدوير الابتسامة
    msg = await context.bot.send_message(
        chat_id, f"⏳ جاري العمل على {filename} 😁"
    )
    user_data["progress_msg_id"] = msg.message_id

    # بدء الوميض
    stop_event = asyncio.Event()
    blink_task = asyncio.create_task(
        blink_message(context.bot, chat_id, msg.message_id, filename, stop_event)
    )

    # استدعاء Gemini API لإنشاء محتوى الملف
    prompt = (
        f"Create the content of the file named '{filename}' "
        f"for a {proj_type} project described as:\n{desc}"
    )
    try:
        res = requests.post(
            GEMINI_URL,
            json={"prompt": {"text": prompt}, "temperature": 0.7}
        )
        res.raise_for_status()
        data = res.json()
        content = data["candidates"][0]["output"]
    except Exception as e:
        stop_event.set()
        await blink_task
        await context.bot.edit_message_text(
            f"🚫 خطأ أثناء إنشاء {filename}:\n{e}",
            chat_id=chat_id, message_id=msg.message_id
        )
        return

    # حفظ الملف محليًا
    ext = filename.split(".")[-1]
    if ext not in EXT_MAP:
        ext = "txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    # إيقاف الوميض وانتظار انتهاء المهمة
    stop_event.set()
    await blink_task

    # تحرير الرسالة لوضع زر "التالي" أو إعلان الانتهاء
    if idx < len(files) - 1:
        next_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("التالي", callback_data="next_file")]
        ])
        await context.bot.edit_message_text(
            f"✅ تم إنشاء {filename}",
            chat_id=chat_id,
            message_id=msg.message_id,
            reply_markup=next_btn
        )
    else:
        await context.bot.edit_message_text(
            f"✅ تم إنشاء {filename}\n🎉 اكتمال المشروع!",
            chat_id=chat_id,
            message_id=msg.message_id
        )

    user_data["current_file_index"] = idx + 1


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_data = context.user_data

    # كتابة كود عادي أو اختبار أو سؤال
    if data == "write_code":
        user_data.clear()
        user_data["mode"] = "write_code"
        await query.message.reply_text(
            "📚 اختر لغة الكود أولًا:",
            reply_markup=language_keyboard
        )
        return

    if data.startswith("lang_") and user_data.get("mode") == "write_code":
        lang_map = {
            "lang_php": "PHP",
            "lang_python": "Python",
            "lang_js": "JavaScript",
            "lang_html": "HTML/CSS"
        }
        language = lang_map.get(data, "PHP")
        user_data["language"] = language
        await query.message.reply_text(
            f"✏️ أرسل وصف الكود المطلوب بلغة {language}."
        )
        return

    if data == "test_code":
        user_data.clear()
        user_data["mode"] = "test_code"
        await query.message.reply_text(
            "🧪 أرسل الكود لاختباره واكتشاف الأخطاء."
        )
        return

    if data == "ask_question":
        user_data.clear()
        user_data["mode"] = "ask_question"
        await query.message.reply_text("❓ أرسل سؤالك البرمجي.")
        return

    # بدء بناء مشروع جديد
    if data == "build_project":
        user_data.clear()
        user_data["mode"] = "build_project_type"
        await query.message.reply_text(
            "🔨 اختر نوع المشروع:",
            reply_markup=project_type_keyboard
        )
        return

    # حدد نوع المشروع (موقع ويب أو بوت)
    if data in ("project_web", "project_bot"):
        user_data["project_type"] = "website" if data == "project_web" else "telegram bot"
        user_data["mode"] = "build_project_desc"
        await query.message.reply_text(
            f"✏️ أرسل وصف {user_data['project_type']} الذي تريد بناؤه."
        )
        return

    # زر التالي في بناء المشروع
    if data == "next_file":
        await process_next_file(context, update.effective_chat.id)
        return

    # زر العودة للقائمة الرئيسية
    await query.message.reply_text("❓ لم أفهم اختيارك، استخدم /start للعودة.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    mode = user_data.get("mode", "")

    # توليد كود عادي
    if mode == "write_code":
        lang = user_data.get("language", "PHP")
        prompt = f"اكتب كود بلغة {lang} حسب الوصف:\n{update.message.text}"
        user_data.clear()

    # اختبار كود
    elif mode == "test_code":
        prompt = f"افحص الكود التالي واكتشف الأخطاء:\n{update.message.text}"
        user_data.clear()

    # سؤال عام
    elif mode == "ask_question":
        prompt = f"أجب بدقة على السؤال التالي:\n{update.message.text}"
        user_data.clear()

    # بدء تجهيز قائمة الملفات للمشروع
    elif mode == "build_project_desc":
        desc = update.message.text
        user_data["project_desc"] = desc
        # نطلب من النموذج قائمة الملفات
        file_list_prompt = (
            f"List all the files needed to build a "
            f"{user_data['project_type']} described as:\n{desc}"
        )
        try:
            res = requests.post(
                GEMINI_URL,
                json={"prompt": {"text": file_list_prompt}, "temperature": 0.5}
            )
            res.raise_for_status()
            items = res.json()["candidates"][0]["output"]
            # تنظيف النتيجة إلى قائمة
            files = [
                line.strip(" -")
                for line in items.splitlines()
                if line.strip()
            ]
            user_data["file_list"] = files
            user_data["current_file_index"] = 0
        except Exception as e:
            await update.message.reply_text(f"🚫 خطأ في جلب قائمة الملفات:\n{e}")
            return

        # ابدأ بإنشاء أول ملف
        await process_next_file(context, update.effective_chat.id)
        return

    else:
        await update.message.reply_text("❓ استخدم الأزرار لبدء تفاعل.")

    # استدعاء AI للحالات الكتابية العادية
    try:
        res = requests.post(
            GEMINI_URL,
            json={"prompt": {"text": prompt}, "temperature": 0.7}
        )
        res.raise_for_status()
        output = res.json()["candidates"][0]["output"]
        await update.message.reply_text(output)
    except Exception as e:
        await update.message.reply_text(f"🚫 خطأ فني:\n{e}")


def main():
    print("🚀 البوت يعمل...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
