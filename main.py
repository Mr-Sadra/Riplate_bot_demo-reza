import os
import json
from flask import Flask

app = Flask(__name__)


from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes


Token = os.environ['BOT_TOKEN']
ADMIN_ID = 301808051  # آی‌دی مدیر

user_status = {}  # ذخیره وضعیت کاربران
approved_users = [205302686]  # لیست کاربران تأیید‌شده


# خواندن داده‌ها از فایل JSON
def load_menu_data():
    with open("menu.json", "r", encoding="utf-8") as file:
        return json.load(file)


menu_data = load_menu_data()  # بارگذاری داده‌ها
main_menus = menu_data["main_menus"]
sub_menus = menu_data["sub_menus"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # اگر کاربر از قبل تأیید شده باشد، درخواست به مدیر ارسال نمی‌شود
    if user_id == ADMIN_ID or user_id in approved_users or user_status.get(
            user_id) == "accepted":
        keyboard = [[name] for name in main_menus]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("لطفاً یک گزینه را انتخاب کنید:",
                                        reply_markup=reply_markup)
        user_status[user_id] = "accepted"
        return

    # ارسال درخواست تأیید به مدیر
    keyboard = [[
        InlineKeyboardButton("✅ تأیید", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=
        f"کاربر {update.effective_user.full_name} ({user_id}) درخواست دسترسی دارد:",
        reply_markup=reply_markup)
    user_status[user_id] = "pending"


async def accept_user(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id != ADMIN_ID:
        await query.answer("⛔ فقط مدیر می‌تواند کاربران را تأیید کند.",
                           show_alert=True)
        return

    user_id = int(query.data.split("_")[1])

    if user_id not in approved_users:
        approved_users.append(user_id)

    user_status[user_id] = "accepted"

    keyboard = [[name] for name in main_menus]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await context.bot.send_message(chat_id=user_id,
                                   text="لطفاً یک گزینه را انتخاب کنید:",
                                   reply_markup=reply_markup)


async def reject_user(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id != ADMIN_ID:
        await query.answer("⛔ فقط مدیر می‌تواند کاربران را رد کند.",
                           show_alert=True)
        return

    user_id = int(query.data.split("_")[1])
    user_status[user_id] = "rejected"
    await context.bot.send_message(
        chat_id=user_id,
        text="❌ شما رد شدید و امکان استفاده از ربات را ندارید.")


async def show_submenu(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if user_status.get(user_id) != "accepted":
        await update.message.reply_text(
            "⛔ شما هنوز تأیید نشده‌اید. لطفاً منتظر تأیید مدیر باشید.")
        return

    selected_menu = update.message.text
    if selected_menu in sub_menus:
        keyboard = [[name] for name in sub_menus[selected_menu]]
        keyboard.append(["بازگشت"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"شما وارد {selected_menu} شدید، لطفاً یک گزینه انتخاب کنید:",
            reply_markup=reply_markup)


async def back_to_main(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def show_approved_users(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    if approved_users:
        users_list = "\n".join(
            [f"👤 کاربر {user_id}" for user_id in approved_users])
        await update.message.reply_text(f"✅ کاربران تأیید‌شده:\n{users_list}")
    else:
        await update.message.reply_text("⛔ هیچ کاربری تأیید نشده است!")


app = ApplicationBuilder().token(Token).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler(
    "approved_users", show_approved_users))  # دستور نمایش کاربران تأیید‌شده
app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex(f"^{'|'.join(sub_menus.keys())}$"),
        show_submenu))  # نمایش زیرمنوها
app.add_handler(
    MessageHandler(filters.TEXT & filters.Regex("^بازگشت$"),
                   back_to_main))  # بازگشت به منوی اصلی
app.add_handler(CallbackQueryHandler(accept_user, pattern="^accept_.*"))
app.add_handler(CallbackQueryHandler(reject_user, pattern="^reject_.*"))


print("Bot is running...")
app.run_polling()
print("Bot Run.")
