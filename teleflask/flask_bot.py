#!/usr/bin/python3

import telebot
import flask
import sqlite3
import time
import datetime

my_telegram_id = 723253749
db_path = '/home/pi/hdd_drive/pavlovsk_doc/bd/raspi_doc.db'
# API_TOKEN = '1622722309:AAG6S1-b-mgob0RVRtC2uWuH9wOaUa7cxTY' #webhookbot
API_TOKEN = '1325955552:AAGBn2LQoXItTlagfRV5EcrMpue-OsIliEg'# bot_for_debug
auth_pass = '22309:AAG6S1-b-m'

WEBHOOK_HOST = '217.8.228.231'
WEBHOOK_PORT = 8443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

WEBHOOK_SSL_CERT = '/home/pi/Documents/PythonScripts/raspi_doc/teleflask/webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = '/home/pi/Documents/PythonScripts/raspi_doc/teleflask/webhook_pkey.pem'  # Path to the ssl private key

WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

bot = telebot.TeleBot(API_TOKEN, parse_mode='Markdown')
bot.send_message(723253749, 'сервер запущен')

app = flask.Flask(__name__)

# Декоратор для логгирования и уведомления о входящих сообщений

def notification_by_msg(f):
    def wrapped(message):
        conn = sqlite3.connect(db_path)
        curs = conn.cursor()
        
        # добавляю сообщение в лог ---------------------------------------
        date_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = [date_time, message.from_user.username, message.from_user.id, message.text]
        ins = 'INSERT INTO msg_log (date_time, user_name, user_id, msg_text) VALUES (?, ?, ?, ?)'
        curs.execute(ins, data)
        conn.commit()
        
        # если пользователя нет в таблице all_users, то добавляю его туда
        ins = 'SELECT user_id FROM all_users'
        curs.execute(ins)
        usr_list = [i[0] for i in curs.fetchall()]
        if not (message.from_user.id in usr_list):
            ins = 'INSERT INTO all_users (user_id, user_name) VALUES (?, ?)'
            data = (message.from_user.id, message.from_user.username)
            curs.execute(ins, data)
            conn.commit()
            
        curs.close()
        conn.close()

        if message.from_user.id != my_telegram_id:
            bot.reply_to(message, f'Cообщение от пользователя {message.from_user.username}')
        response = f(message)
        return response
    return wrapped

# Empty webserver index, return nothing, just http 200
@app.route('/')
def index():
    return ''


# Process webhook calls
@app.route(WEBHOOK_URL_PATH, methods=['GET', 'POST'])
def webhook():
    print(flask.request.headers)
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        print('You NOT made it!')
        flask.abort(403)


@bot.message_handler(commands=['start'])
@notification_by_msg
def start(message):
    bot.reply_to(message, 'Для начала работы с ботом, отправьте пароль, ответным сообщением')
    
@bot.message_handler(commands=['help'])
@notification_by_msg
def start(message):
    bot.reply_to(message, '''/delme - отписка от рассылки бота,
/mw или /wtf - состояние комплекса в данный момент,
/mh - наработка ГПГУ, в моточасах''')

@bot.message_handler(commands=['mh'])
@notification_by_msg
def send_mh(message):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    ins = 'SELECT date_time, Genset1_run_hours, Genset2_run_hours, Genset3_run_hours, Genset4_run_hours, Genset5_run_hours FROM g_val WHERE date_time=(SELECT max(date_time) FROM g_val)'
    cur.execute(ins)
    dt, g1, g2, g3, g4, g5 = cur.fetchone()
    date_time = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    cur.close()
    conn.close()
    
    resp = f"*Наработка, мч*\n*ГПГУ1:* {g1}. ТО250 через {250-g1%250} мч\n*ГПГУ2:* {g2}. ТО250 через {250-g2%250} мч\n*ГПГУ3:* {g3}. ТО250 через {250-g3%250} мч\n*ГПГУ4:* {g4}. ТО250 через {250-g4%250} мч\n*ГПГУ5:* {g5}. ТО250 через {250-g5%250} мч\n\n{date_time}"
    bot.reply_to(message, resp)

@bot.message_handler(commands=['mw', 'wtf'])
@notification_by_msg
def send_mw(message):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    ins = 'SELECT * FROM fast_power_values'
    cur.execute(ins)
    dt, ess, g1, g2, g3, g4, g5 = cur.fetchone()
    cur.close()
    conn.close()
    date_time = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    
    resp = f"*Мощность*\n*ГПГУ1:* {g1} кВт\n*ГПГУ2:* {g2} кВт\n*ГПГУ3:* {g3} кВт\n*ГПГУ4:* {g4} кВт\n*ГПГУ5:* {g5} кВт\n-------------------------------------------------------\n*ПОЛНАЯ МОЩНОСТЬ:* {g1+g2+g3+g4+g5} кВт\n\n*ESS:* {ess} кВт\n-------------------------------------------------------\n{date_time}"
    bot.reply_to(message, resp)

# Авторизация
@bot.message_handler(content_types=['text'])
@notification_by_msg
def send_response(message):
    # Если пришел код авторизации
    if message.text == auth_pass:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        ins = 'SELECT user_id FROM broadcast_user_list'
        cur.execute(ins)
        user_id_list = [d[0] for d in cur.fetchall()]
        bot.send_message(message.from_user.id, f'{message.from_user.id}, {str(cur.fetchall())}')
        if not(message.from_user.id in user_id_list):
            bot.send_message(message.from_user.id, 'Авторизация прошла успешно. Чтобы отказаться от рассылки бота, отправьте ему команду: /delme. Для ознакомления с командами и функционалом, отправьте боту команду: /helpme')
            usr_data = [message.from_user.id, message.from_user.username]
            ins = f'INSERT INTO broadcast_user_list (user_id, user_name) VALUES (?, ?)'
            cur.execute(ins, usr_data)
        else:
            bot.send_message(message.from_user.id, 'Вы уже есть в списке рассылки')
        conn.commit()
        cur.close()
        conn.close()
    else:
        bot.send_message(message.from_user.id, message.text)


# Remove webhook, it fails sometimes the set if there is a previous webhook
bot.remove_webhook()

time.sleep(0.1)

# Set webhook
bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Start flask server
app.run(host=WEBHOOK_LISTEN,
        port=WEBHOOK_PORT,
        ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
        debug=True)
