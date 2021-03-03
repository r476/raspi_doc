#!/usr/bin/python3

import telebot
import flask
import sqlite3
import time

# API_TOKEN = '1622722309:AAG6S1-b-mgob0RVRtC2uWuH9wOaUa7cxTY' #webhookbot
API_TOKEN = '1325955552:AAHf1qupEZbM4Ik79VRpVLDaLCXI596P3IY' # bot_for_debug

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


@bot.message_handler(commands=['mh'])
def send_mh(message):
    conn = sqlite3.connect('/home/pi/hdd_drive/pavlovsk_doc/bd/raspi_doc.db')
    cur = conn.cursor()
    ins = 'SELECT Genset1_run_hours as G1, Genset2_run_hours as G2, Genset3_run_hours as G3, Genset4_run_hours as G4, Genset5_run_hours as G5 FROM g_val WHERE date_time=(SELECT max(date_time) FROM g_val)'
    cur.execute(ins)
    hrs = cur.fetchone()
    cur.close()
    conn.close()
    
    resp = f"*Наработка, мч*\n*ГПГУ1:* {hrs[0]}. ТО250 через {250-hrs[0]%250} мч\n*ГПГУ2:* {hrs[1]}. ТО250 через {250-hrs[1]%250} мч\n*ГПГУ3:* {hrs[2]}. ТО250 через {250-hrs[2]%250} мч\n*ГПГУ4:* {hrs[3]}. ТО250 через {250-hrs[3]%250} мч\n*ГПГУ5:* {hrs[4]}. ТО250 через {250-hrs[4]%250} мч"
    bot.reply_to(message, resp)

@bot.message_handler(commands=['mw'])
def send_mh(message):
    conn = sqlite3.connect('/home/pi/hdd_drive/pavlovsk_doc/bd/raspi_doc.db')
    cur = conn.cursor()
    ins = 'SELECT * FROM fast_power_values'
    cur.execute(ins)
    dt, ess, g1, g2, g3, g4, g5 = cur.fetchone()
    cur.close()
    conn.close()
    
    resp = f"*Мощность*\n*ГПГУ1:* {g1} кВт\n*ГПГУ2:* {g2} кВт\n*ГПГУ3:* {g3} кВт\n*ГПГУ4:* {g4} кВт\n*ГПГУ5:* {g5} кВт\n-------------------------------------------------------\n*ПОЛНАЯ МОЩНОСТЬ:* {g1+g2+g3+g4+g5} кВт\n\n*ESS:* {ess} кВт"
    bot.reply_to(message, resp)

@bot.message_handler(content_types=['text'])
def send_response(message):
    bot.send_message(message.from_user.id, str(message.from_user.json))

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
