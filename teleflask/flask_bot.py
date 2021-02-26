#!/usr/bin/python3
import telebot
import flask
import sqlite3
import time

# API_TOKEN = '1622722309:AAG6S1-b-mgob0RVRtC2uWuH9wOaUa7cxTY' #webhookbot
API_TOKEN = '1325955552:AAF40qxDw0lJ1v_EdUumEBnXZ4mKyE5s8Nk' # bot_for_debug

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


# Handle '/start' and '/help'
@bot.message_handler(commands=['mh'])
def send_mh(message):
    conn = sqlite3.connect('/home/pi/hdd_drive/pavlovsk_doc/bd/raspi_doc.db')
    cur = conn.cursor()
    ins = 'SELECT Genset1_run_hours as G1, Genset2_run_hours as G2, Genset3_run_hours as G3, Genset4_run_hours as G4, Genset5_run_hours as G5 FROM g_val WHERE date_time=(SELECT max(date_time) FROM g_val)'
    cur.execute(ins)
    hrs = cur.fetchone()
    cur.close()
    conn.close()
    
    resp = f"*Наработка, мч*\n*ГПГУ1:* {hrs[0]}\n*ГПГУ2:* {hrs[1]}\n*ГПГУ3:* {hrs[2]}\n*ГПГУ4:* {hrs[3]}\n*ГПГУ5:* {hrs[4]}"
    bot.reply_to(message, resp)

# Handle all other messages
# @bot.message_handler(func=lambda message: True, commands=['mh'])
# def echo_message(message):
#     conn = sqlite3.connect('/home/pi/hdd_drive/pavlovsk_doc/bd/raspi_doc.db')
#     cur = conn.cursor()
#     ins = 'SELECT Genset1_run_hours as G1, Genset2_run_hours as G2, Genset3_run_hours as G3, Genset4_run_hours as G4, Genset5_run_hours as G5 FROM g_val WHERE date_time=(SELECT max(date_time) FROM g_val)'
#     cur.execute(ins)
#     hrs = cur.fetchone()
#     cur.close()
#     conn.close()
    
#     resp = f"Наработка, мч\nГПГУ1: {hrs[0]}\nГПГУ2: {hrs[1]}\nГПГУ3: {hrs[2]}\nГПГУ4: {hrs[3]}\nГПГУ5: {hrs[4]}"
#     bot.reply_to(message, resp)

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
