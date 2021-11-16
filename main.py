from telegram import Update, ParseMode
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters
from mega import Mega
import psycopg2
import os
import re
import config

if not os.path.exists('users'):
    os.mkdir('users')

conn = psycopg2.connect(dbname=config.dbname, user=config.dbuser, password=config.dbpassword, host=config.dbhost)

updater = Updater(token=config.token, use_context=True)
dispatcher = updater.dispatcher

mega = Mega()

regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'

def checkemail(email):
    if(re.search(regex,email)):   
        return True
    else:   
        return False

def addaccount(update: Update, context: CallbackContext):
    if 1 > len(context.args):
        context.bot.send_message(chat_id=update.effective_chat.id, text='Add account like that:\n<code>/addaccount example@email.com password</code>', parse_mode=ParseMode.HTML)
        return

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=%s', [update.message.chat.id])
    result = cursor.fetchone()
    if result != None:
        context.bot.send_message(chat_id=update.effective_chat.id, text='You have added account already!')
        return

    if checkemail(context.args[0]) == False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Invalid email')
        return

    cursor.execute('INSERT INTO users(user_id, email, password) VALUES (%s, %s, %s)', [update.message.chat.id, context.args[0], context.args[1]])
    cursor.close()
    conn.commit()

    os.mkdir('users/{0}'.format(update.message.chat.id))

    context.bot.send_message(chat_id=update.effective_chat.id, text='Done! Now you can send file to upload')

def delaccount(update: Update, context: CallbackContext):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=%s', [update.message.chat.id])
    result = cursor.fetchone()
    if result == None:
        context.bot.send_message(chat_id=update.effective_chat.id, text='You haven\'t added any account!')
        return
    
    cursor.execute('DELETE FROM users WHERE user_id=%s', [update.message.chat.id])
    cursor.close()
    conn.commit()

    os.rmdir('users/{0}'.format(update.message.chat.id))

    context.bot.send_message(chat_id=update.effective_chat.id, text='Your account deleted successfully!')

def upload(update: Update, context: CallbackContext):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=%s', [update.message.chat.id])
    result = cursor.fetchone()
    if result == None:
        context.bot.send_message(chat_id=update.effective_chat.id, text="You need to add account before uploading files:\n<code>/addaccount example@email.com password</code>", parse_mode=ParseMode.HTML)
        cursor.close()
        return
    
    if update.message.document.file_size > 5242880:
        context.bot.send_message(chat_id=update.effective_chat.id, text='File size is too big!\nYou can upload files only up to 5 MB');
        return

    m = mega.login(result[1], result[2])

    filepath = 'users/{0}/{1}'.format(update.message.chat.id, update.message.document.file_name)
    with open(filepath, 'wb') as f:
        context.bot.get_file(update.message.document).download(out=f)
        file = m.upload(filepath)
        context.bot.send_message(chat_id=update.effective_chat.id, text=m.get_upload_link(file))
        os.remove(filepath)

dispatcher.add_handler(CommandHandler('addaccount', addaccount))
dispatcher.add_handler(CommandHandler('delaccount', delaccount))
dispatcher.add_handler(MessageHandler(Filters.document, upload))

updater.start_polling()
