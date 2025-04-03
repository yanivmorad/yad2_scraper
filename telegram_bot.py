from telegram import ReplyKeyboardMarkup  # הוספת ייבוא חדש
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import pandas as pd
import os
import subprocess
import threading
from yad2_scan import Yad2VehicleScraper  # הוספת ייבוא למחלקה

# פרטי הבוט שלך
TELEGRAM_TOKEN = "8050638497:AAG4gK6hCaPKXvcTwhT9BNY0949XgwdbJ7A"
BASE_URL = "https://www.yad2.co.il/vehicles/cars?manufacturer=19,21,48&year=2015-2021&price=28000-40000&km=20000-110000&engineval=1200--1&hand=0-1&engineType=1101&ownerID=1"

# מצבי שיחה להוספת URL
ADD_URL = 0

def start(update, context):
    # הגדרת הכפתורים במקלדת
    keyboard = [
        ['/scan', '/list'],
        ['/addurl', '/help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🚗 **ברוכים הבאים לבוט סקירת הרכבים!** 🚗\n\n"
             "בחר אחת מהאפשרויות הבאות:",
        reply_markup=reply_markup  # הוספת המקלדת להודעה
    )

def help_command(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📚 **מדריך לשימוש בבוט:**\n\n"
             "- /start: הצגת תפריט ראשי.\n"
             "- /scan: בצע סריקה חדשה של אתר Yad2.\n"
             "- /list: הצג את רשימת הרכבים מהסריקה האחרונה.\n"
             "- /addurl: הוסף URL מותאם אישית לפילטרים נוספים.\n\n"
             "💡 **טיפים:**\n"
             "- הסריקה מתבצעת רק עם /scan.\n"
             "- ודא שה-URL תקין בעת הוספתו."
    )

def scan(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="⏳ מחפש רכבים... נא להמתין")

    def run_scraper():
        try:
            # בדיקה האם קיים קובץ URL מותאם אישית
            if os.path.exists("custom_url.txt"):
                with open("custom_url.txt", "r", encoding="utf-8") as f:
                    custom_url = f.read().strip()
            else:
                custom_url = BASE_URL

            # יצירת אובייקט הסקרייפר וביצוע הסריקה
            scraper = Yad2VehicleScraper(custom_url)
            scraper.scrape(max_pages=5)

            # קבלת רשימת הרכבים החדשים שנוספו
            new_listings = scraper.get_new_listings()

            if not new_listings:
                context.bot.send_message(chat_id=chat_id, text="⚠️ לא נמצאו רכבים חדשים.")
                return

            message = "🚗 **רכבים חדשים** 🚗\n\n"
            for listing in new_listings:
                message += f"**🚗 דגם:** {listing['make_model']}\n"
                message += f"**💰 מחיר:** {listing['price']}\n"
                message += f"**📊 קילומטראז':** {listing['km']} קמ\n"
                message += f"**🔗 קישור:** {listing['link']}\n\n"
                if len(message) > 3000:
                    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                    message = ""

            if message:
                context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            context.bot.send_message(chat_id=chat_id, text="✅ הסריקה הסתיימה בהצלחה!")
        except Exception as e:
            context.bot.send_message(chat_id=chat_id, text=f"❌ תקלה בסריקה: {e}\nנסה שוב בעוד דקה.")

    threading.Thread(target=run_scraper).start()

def list_vehicles(update, context):
    chat_id = update.effective_chat.id
    csv_file = "vehicles.csv"  # קובץ הנתונים
    if not os.path.exists(csv_file):
        context.bot.send_message(chat_id=chat_id, text="❌ לא נמצא קובץ 'vehicles.csv'. בצע סריקה עם /scan.")
        return

    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ שגיאה בקריאת הקובץ: {e}")
        return

    if df.empty:
        context.bot.send_message(chat_id=chat_id, text="⚠️ אין נתונים להצגה.")
        return

    required_columns = ['make_model', 'km', 'price', 'link']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        context.bot.send_message(chat_id=chat_id, text=f"❌ חסרות עמודות: {missing_columns}")
        return

    message = "🚗 **רשימת הרכבים** 🚗\n\n"
    for _, row in df.iterrows():
        message += f"**🚗 דגם:** {row['make_model']} {row['year_hand']}\n"
        message += f"**💰 מחיר:** {row['price']}\n"
        message += f"**📊 קילומטראז':** {row['km']} קמ\n"
        message += f"**🔗 קישור:** {row['link']}\n\n"
        if len(message) > 3000:
            context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            message = ""

    if message:
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

def add_url(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✏️ שלח את ה-URL המותאם אישית לפילטרים."
    )
    return ADD_URL

def receive_url(update, context):
    url = update.message.text
    if not url.startswith("https://www.yad2.co.il/vehicles/cars?"):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ ה-URL אינו תקין. ודא שהוא מתחיל ב-'https://www.yad2.co.il/vehicles/cars?'."
        )
        return ConversationHandler.END

    with open("custom_url.txt", "w", encoding="utf-8") as f:
        f.write(url)

    # מחיקת קובץ ה-CSV כאשר הקישור משתנה
    if os.path.exists("vehicles.csv"):
        os.remove("vehicles.csv")

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ ה-URL נוסף בהצלחה! ישמש בסריקה הבאה. הרשימה אופסה."
    )
    return ConversationHandler.END

def cancel(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❌ הוספת ה-URL בוטלה."
    )
    return ConversationHandler.END

# הגדרת הבוט והפקודות
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("scan", scan))
dispatcher.add_handler(CommandHandler("list", list_vehicles))

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("addurl", add_url)],
    states={ADD_URL: [MessageHandler(Filters.text & (~Filters.command), receive_url)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)
dispatcher.add_handler(conv_handler)

updater.start_polling()
updater.idle()