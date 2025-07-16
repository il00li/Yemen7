import google.generativeai as genai
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# مفاتيح الوصول
TELEGRAM_TOKEN = "8110119856:AAEKyEiIlpHP2e-xOQym0YHkGEBLRgyG_wA"
GEMINI_API_KEY = "AIzaSyCbKhGJ8HJLDa_mZ8VZoau8mH1Yz2-KPmY"
ADMIN_ID = 7251748706

# تهيئة نموذج Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# لوحة الأزرار الرئيسية
main_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("✍️ اكتب كود", callback_data="write_code"),
     InlineKeyboardButton("🧪 اختبر الكود", callback_data="test_code")],
    [InlineKeyboardButton("📘 دروس تعليمية", callback_data="lessons"),
     InlineKeyboardButton("❓ اسأل سؤال", callback_data="ask_question")],
    [InlineKeyboardButton("👤 حسابي", callback_data="user_profile"),
     InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
    [InlineKeyboardButton("🆘 المساعدة", callback_data="help"),
     InlineKeyboardButton("🏠 الرئيسية", callback_data="home")]
])

# لوحة اختيار اللغة بعد الضغط على "✍️ اكتب كود"
language_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("PHP", callback_data="lang_php"),
     InlineKeyboardButton("Python", callback_data="lang_python")],
    [InlineKeyboardButton("JavaScript", callback_data="lang_js"),
     InlineKeyboardButton("HTML/CSS", callback_data="lang_html")]
])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت البرمجة المتعدد اللغات!\nاختر أحد الخيارات:",
        reply_markup=main_keyboard
    )

# التعامل مع الضغط على الأزرار
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_data = context.user_data

    if data == "write_code":
        # نطلب اختيار اللغة أولًا
        user_data.clear()
        user_data['mode'] = 'write_code'
        await query.message.reply_text(
            "📚 اختر لغة الكود التي تريدها:",
            reply_markup=language_keyboard
        )
        return

    if data.startswith("lang_"):
        # حفظ اللغة المختارة ثم طلب الوصف
        lang_map = {
            "lang_php": "PHP",
            "lang_python": "Python",
            "lang_js": "JavaScript",
            "lang_html": "HTML/CSS"
        }
        language = lang_map.get(data, "PHP")
        user_data['language'] = language
        await query.message.reply_text(f"✏️ أرسل وصف الكود المطلوب بلغة {language}.")
        return

    # أوضاع أخرى لا تحتاج اختيار لغة
    user_data['mode'] = data
    messages = {
        "test_code": "🧪 أرسل الكود لاختباره واكتشاف الأخطاء.",
        "lessons": "📘 هذه بعض الدروس التعليمية:\n- أساسيات المتغيرات\n- الحلقات والشروط\n- الدوال والكائنات\n- قواعد البيانات",
        "ask_question": "❓ أرسل سؤالك البرمجي وسأجيبك.",
        "user_profile": f"👤 اسمك: {query.from_user.full_name}\n📌 معرفك: {query.from_user.id}",
        "stats": "📊 لا توجد إحصائيات محفوظة حالياً.",
        "help": "🆘 استخدم الأزرار أو اكتب وصف كود/سؤال، وسأقدم المساعدة.",
        "home": "🏠 عدنا إلى القائمة الرئيسية."
    }
    resp = messages.get(data, "❓ الأمر غير معروف.")
    await query.message.reply_text(resp, reply_markup=main_keyboard if data == "home" else None)

# التعامل مع الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    mode = user_data.get('mode', 'write_code')
    user_input = update.message.text

    # بناء الموجه حسب الوضع
    if mode == 'write_code':
        language = user_data.get('language', 'PHP')
        prompt = f"اكتب كود بلغة {language} حسب الوصف التالي:\n{user_input}"
    elif mode == 'test_code':
        language = user_data.get('language', '')
        lang_suffix = f" بلغة {language}" if language else ""
        prompt = f"افحص الكود التالي{lang_suffix} للعثور على الأخطاء:\n{user_input}"
    elif mode == 'ask_question':
        prompt = f"أجب عن السؤال التالي بدقة:\n{user_input}"
    else:
        prompt = user_input  # fallback

    # استدعاء نموذج Gemini
    try:
        response = model.generate_content(prompt)
        code = response.text

        # إرسال الرد للمستخدم
        await update.message.reply_text(code)

        # حفظ الكود في ملف حسب اللغة
        ext_map = {
            "PHP": "php",
            "Python": "py",
            "JavaScript": "js",
            "HTML/CSS": "html"
        }
        lang = user_data.get('language', 'txt')
        ext = ext_map.get(lang, "txt")
        filename = f"output_code.{ext}"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code)

    except Exception:
        await update.message.reply_text("🚫 حصل خطأ أثناء الاتصال بنموذج الذكاء الاصطناعي.")

# نقطة الانطلاق
def main():
    print("🚀 البوت بدأ العمل...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()