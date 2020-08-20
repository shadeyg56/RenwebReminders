from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters
import psycopg2
import psycopg2.extras
import private
import driver as dv
from passlib.hash import cisco_type7
import os
from PIL import Image, ImageFont, ImageDraw
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import datetime


class Bot(Updater):
    def __init__(self, token):
        super().__init__(token=token, use_context=True)
        self.conn = psycopg2.connect(f"dbname={private.db} user={private.dbuser} password={private.dbpass} host={private.host}")
        self.pool = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.pool.execute("CREATE TABLE IF NOT EXISTS users(id int PRIMARY KEY, username text, password text, chat_id int);")
        self.conn.commit()
        self.loop = asyncio.get_event_loop()

    def command(self, name, args=False):
        def decorator(function, *args, **kwargs):
            self.dispatcher.add_handler(CommandHandler(name, function, pass_args=args))
            return function
        return decorator

    def main(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('register', register)],

            states={
                USERNAME: [MessageHandler(Filters.text & ~Filters.command, username)],
                PASSWORD: [MessageHandler(Filters.text & ~Filters.command, password)]
            },
            fallbacks=[CommandHandler("cancel", cancel)])

        self.dispatcher.add_handler(conv_handler)
        self.start_polling()
        print("Bot is online")
        try:
            self.loop.create_task(self.loop.run_in_executor(ThreadPoolExecutor(1), send_homework))
        except TypeError:
            pass
        self.loop.run_forever()


bot = Bot(private.token)
chats = {}


@bot.command("start")
def start(update, context):
    update.message.reply_text("To get started with reminders, run /register")


@bot.command("forget")
def forget(update, context):
    bot.pool.execute("DELETE FROM users WHERE id = %s;", (update.effective_user.id,))
    bot.conn.commit()
    update.message.reply_text("You have been unregistered")


@bot.command("fetch", args=True)
def fetch(update, context):
    day = context.args[0].lower()
    update.message.reply_text(f"Fetching homework for {day.title()}")
    screenshot(update.effective_user.id, day)
    manip(update.effective_user.id, day)
    update.message.reply_photo(open(f"pics/{update.effective_user.id}.png", "rb"))
    os.remove(f"pics/{update.effective_user.id}.png")


def screenshot(user_id, day):
    user = bot.pool.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
    user = bot.pool.fetchone()
    passw = cisco_type7.decode(user["password"])
    driver = dv.CustomDriver()
    driver.login(user["username"], passw)
    driver.fetch_pics(day, user_id)
    driver.quit()


def manip(user_id, day):
    images = []
    heights = []
    width = 0
    for file in os.listdir("pics"):
        if file.startswith(str(user_id)):
            nfile = Image.open(f"pics/{file}")
            images.append(nfile)
            if len(heights) == 0:
                width = nfile.width
            heights.append(nfile.height)
    new = Image.new("RGB", (width, sum(heights) + 35))
    before = 35
    for image in images:
        new.paste(image, (0, before))
        before += image.height
    draw = ImageDraw.Draw(new)
    font = ImageFont.truetype("fonts/Aaargh.ttf", 30)
    w, h = draw.textsize(day.title())
    draw.text(((new.width - w) / 2, 0), day.title(), (255, 255, 255), font=font, align="center")
    new.save(f"pics/{user_id}.png")
    for file in os.listdir("pics"):
        if file.startswith(str(user_id)) and file != f"{str(user_id)}.png":
            os.remove(f"pics/{file}")

# Conversation Stuff
USERNAME, PASSWORD = range(2)
users = {}


def register(update, context):
    update.message.reply_text("Please enter your Renweb username. To cancel registration at anytime just type /cancel")
    return USERNAME


def username(update, context):
    users[update.effective_user.id] = update.message.text
    update.message.reply_text("Please enter your Renweb password")
    return PASSWORD


def password(update, context):
    user = users[update.effective_user.id]
    passw = update.message.text
    # this hash is not a real hash, it's an encoding. This is not a security measure, it's simply to prevent plain-text storage.
    # I would use an actual hashing algorithm, but I needed to decode for autologin purposes. This is a simple way to do it
    hash = cisco_type7.hash(passw)
    bot.pool.execute("INSERT INTO users (id, username, password, chat_id) VALUES (%s, %s, %s, %s);", (update.effective_user.id, user, hash, update.effective_chat.id))
    bot.conn.commit()
    update.message.reply_text("You have been registered")
    chats[update.effective_chat.id] = [update.effect_user.id, context.bot]
    del users[update.effective_user.id]
    return ConversationHandler.END


def cancel(update, context):
    update.message.reply_text("Registration cancelled")
    if users.get(update.effective_user.id):
        del users[update.effective_user.id]
    return ConversationHandler.END

# Loop
def send_homework():
    ran = False
    while True:
        users = bot.pool.execute("SELECT * FROM users;")
        users = bot.pool.fetchall()
        for user in users:
            chat = user["id"]
            now = datetime.datetime.now()
            if now.strftime("%H") == "15":
                if not ran:
                    days = {0: "sunday", 1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 5: "friday", 6: "saturday"}
                    day = int(datetime.datetime.today().strftime('%w'))
                    day = days[day]
                    screenshot(user['id'], day)
                    manip(user['id'], day)
                    bot.bot.send_photo(chat_id=chat, photo=open(f"pics/{user['id']}.png", "rb"))
                    os.remove(f"pics/{user['id']}.png")
                ran = True
            else:
                ran = False
        time.sleep(15)


bot.main()
