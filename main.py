from telegram.ext import Updater, CommandHandler
import psycopg2
import psycopg2.extras
import private
import driver as dv
from passlib.hash import cisco_type7
import os


class Bot(Updater):
    def __init__(self, token):
        super().__init__(token=token, use_context=True)
        self.conn = psycopg2.connect(f"dbname={private.db} user={private.dbuser} password={private.dbpass} host={private.host}")
        self.pool = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self.pool.execute("CREATE TABLE IF NOT EXISTS users(id int PRIMARY KEY, username text, password text);")
        self.conn.commit()

    def command(self, name, args=False):
        def decorator(function, *args, **kwargs):
            self.dispatcher.add_handler(CommandHandler(name, function, pass_args=args))
            return function
        return decorator

    def main(self):
        self.start_polling()
        print("Bot is online")
        self.idle()


bot = Bot(private.token)


@bot.command("start")
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


@bot.command("test")
def test(update, context):
    update.message.reply_text(update.effective_user.id)


@bot.command("fetch", args=True)
def fetch(update, context):
    day = context.args[0].lower()
    user = bot.pool.execute("SELECT * FROM users WHERE id = %s", (update.effective_user.id,))
    user = bot.pool.fetchone()
    passw = cisco_type7.decode(user[2])
    driver = dv.CustomDriver()
    driver.login(user[1], passw)
    user = update.effective_user.id
    driver.fetch_pics(day, user)
    driver.quit()
    for file in os.listdir("pics"):
        if file.startswith(str(update.effective_user.id)):
            update.message.reply_photo(open(f"pics/{file}", "rb"))
            os.remove(f"pics/{file}")


@bot.command("register", args=True)
def register(update, context):
    user = context.args[0]
    passw = context.args[1]
    # this hash is not a real hash, it's an encoding. This is not a security measure, it's simply to prevent plain-text storage.
    # I would use an actual hashing algorithm, but I needed to decode for autologin purposes. This is a simple way to do it
    hash = cisco_type7.hash(passw)
    bot.pool.execute("INSERT INTO users (id, username, password) VALUES (%s, %s, %s)", (update.effective_user.id, user, hash))
    bot.conn.commit()
    update.message.reply_text("You have been registered")


bot.main()