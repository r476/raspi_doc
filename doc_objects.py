import minimalmodbus
import config
import logging
import telebot
import sqlite3
import datetime
import requests
from modbus.client import *
import pandas as pd
import time

tb = telebot.TeleBot(config.token)

# logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', filename=config.log_path, level=logging.DEBUG)
# logging.disable(logging.CRITICAL)

# Инициализация БД. При запуске
def init_bd(doc):
    conn = sqlite3.connect(config.raspi_bd)
    curs = conn.cursor()
    
    # Таблица быстрых значений мощностей
    try:
        ins = f'DELETE FROM {config.fast_power_values}'
        curs.execute(ins)
    except Exception as e:
        logging.info(f'Создание таблицы значений: {config.fast_power_values}')
        ins = f'CREATE TABLE {config.fast_power_values} (date_time VARCHAR(20) PRIMARY KEY, ESS_Power INT, Genset1_Act_power INT, Genset2_Act_power INT, Genset3_Act_power INT, Genset4_Act_power INT, Genset5_Act_power INT)'
        curs.execute(ins)
        conn.commit()

    # Большая таблица регулярных параметров
    try:
        ins = f'SELECT MAX(date_time) FROM {config.table_regular_values}'
        curs.execute(ins)
    except Exception as e:
        logging.info(f'Создание таблицы значений: {config.table_regular_values}')
        ins = f'CREATE TABLE {config.table_regular_values} (date_time VARCHAR(20) PRIMARY KEY, ambient_temp INT'
        for g in doc:
            for k, v in {k: v for k, v in g.modbus_table.items() if v['Group'] in config.regular_values}.items():
                if v['Type'] == 'Integer' or v['Type'] == 'Unsigned':
                    type_field = 'INT'
                else:
                    type_field = 'CHAR (20)'
                ins += f", Genset{g.address}_{v['Name_in_bd']} {type_field}"
            ins += f", Genset{g.address}_run_hours INT"
            ins += f", Genset{g.address}_totRunPact_P INT"
            ins += f", Genset{g.address}_totRunPact_Q INT"
            ins += f", Genset{g.address}_kWhours INT"
        ins += ')'
        curs.execute(ins)
        conn.commit()
        logging.info(f'Таблица {config.table_regular_values} создана.')
        
    # Полная таблица засветившихся пользователей
    try:
        ins = f'SELECT * FROM {config.all_users}'
        curs.execute(ins)
    except Exception as e:
        logging.info(f'Создание таблицы значений: {config.all_users}')
        ins = f'CREATE TABLE {config.all_users} (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER , user_name VARCHAR(20))'
        curs.execute(ins)
        conn.commit()

    # Tаблица пользователей для рассылки
    try:
        ins = f'SELECT * FROM {config.broadcast_user_list}'
        curs.execute(ins)
    except Exception as e:
        logging.info(f'Создание таблицы значений: {config.broadcast_user_list}')
        ins = f'CREATE TABLE {config.broadcast_user_list} (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER, user_name VARCHAR(20))'
        curs.execute(ins)
        conn.commit()

    # Tаблица лог сообщений
    try:
        ins = f'SELECT * FROM {config.msg_log}'
        curs.execute(ins)
    except Exception as e:
        logging.info(f'Создание таблицы значений: {config.msg_log}')
        ins = f'CREATE TABLE {config.msg_log} (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, date_time VARCHAR(20), user_name VARCHAR(20), user_id INTEGER, msg_text VARCHAR(250))'
        curs.execute(ins)
        conn.commit()

    curs.close()
    conn.close()
    
def get_temperature():
    s_city = 'Pavlovsk'
    city_id = '1495448'
    appid = '98e48d2bb43dafe8eb6d7383c37b9647'
    try:
        res = requests.get('http://api.openweathermap.org/data/2.5/weather', params={'id': city_id, 'units': 'metric', 'APPID': appid})
        data = res.json()
        city_temp = data['main']['temp']
        return city_temp
    except Exception as e:
        logging.debug(f'Ошибка запроса температуры: {e}')
        return None    

# Запись регулярных значений в БД. В качестве аргумента - список экземпляров ГПГУ
def regular_values_to_bd(doc):
    temp = get_temperature()
    data = [datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), temp]

    ins = f'INSERT INTO {config.table_regular_values} (date_time, ambient_temp'
    ins_val = ' VALUES(?, ?'
    for g in doc:
        for k, v in {k: v for k, v in g.modbus_table.items() if v['Group'] in config.regular_values}.items():
            ins += f", Genset{g.address}_{v['Name_in_bd']}"
            ins_val += ', ?'
            data.append(v['Curr_val'])
            
        ins += f", Genset{g.address}_run_hours"
        ins_val += ', ?'
        data.append(g.run_hours)
        
        ins += f", Genset{g.address}_totRunPact_P"
        ins_val += ', ?'
        data.append(g.totRunPact_P)
        
        ins += f", Genset{g.address}_totRunPact_Q"
        ins_val += ', ?'
        data.append(g.totRunPact_Q)
        
        ins += f", Genset{g.address}_kWhours"
        ins_val += ', ?'
        data.append(g.kWhours)
        
    ins += ') ' + ins_val + ')'
    conn = sqlite3.connect(config.raspi_bd)
    curs = conn.cursor()
    curs.execute(ins, data)
    conn.commit()
    curs.close()
    conn.close()

class Genset(minimalmodbus.Instrument):

    def __init__(self, port, slaveaddress):
        logging.debug(f'Инициализация объекта: ГПГУ{slaveaddress}')
        super().__init__(port=port, slaveaddress=slaveaddress)
        self.serial.baudrate = config.baudrate
        self.protect_dict = self.get_protect_dict()
        self.modbus_table = self.get_modbus_table()
        self.protects = {'prev_protects': None, 
                         'current_protects': self.get_protections()}
        self.gcb_state = {'prev_gcb_state': None, 
                         'current_gcb_state': self.get_gcb_state()}
        self.mcb_state = {'prev_mcb_state': None, 
                         'current_mcb_state': self.get_mcb_state()}
        self.engine_state = {'prev_engine_state': None, 
                         'current_engine_state': self.get_engine_state()}
        # Длинные параметры добавляю отдельно, этот вариант кажется оптимальным
        self.run_hours = self.get_run_hours()
        self.totRunPact_P = self.get_totRunPact_P()
        self.totRunPact_Q = self.get_totRunPact_Q()
        self.kWhours = self.get_kWhours()

        self.get_update()
        
    def read_mb_register(self, registeraddress, number_of_decimals=0, functioncode=3, signed=False):
        for c in range(15):
            try:
                return self.read_register(registeraddress=registeraddress, number_of_decimals=number_of_decimals, functioncode=functioncode, signed=signed)
            except Exception as e:
                pass
        return None

    def read_mb_long(self, registeraddress, functioncode=3, signed=False, byteorder=0):
        for c in range(15):
            try:
                return self.read_long(registeraddress, functioncode=functioncode, signed=signed, byteorder=byteorder)
            except Exception as e:
                pass
        return None

    def read_mb_registers(self, registeraddress, number_of_registers, functioncode=3):
        for c in range(15):
            try:
                return self.read_registers(registeraddress=registeraddress, number_of_registers=number_of_registers, functioncode=functioncode)
            except Exception as e:
                pass
        return None

    def get_run_hours(self):
        return self.read_mb_long(3586) if self.address in (1, 2) else self.read_mb_long(3821)

    def get_totRunPact_P(self):
        return self.read_mb_long(336) if self.address in (1, 2) else self.read_mb_long(541)

    def get_totRunPact_Q(self):
        return self.read_mb_long(334) if self.address in (1, 2) else self.read_mb_long(539)

    def get_kWhours(self):
        return self.read_mb_long(3594) if self.address in (1, 2) else self.read_mb_long(3829)

    def get_engine_state(self):
        logging.debug('get_engines_state()')
        engine_state = config.engine_states
        registeraddress = 162 if self.address in (1, 2) else 295
        value = self.read_mb_register(registeraddress)
        if not value: return None
        engine_state_return = engine_state[value]
        logging.debug(engine_state_return)
        return engine_state_return

#     def get_breaker_state(self):
#         logging.debug('get_breakers_state()')
#         breaker_state = config.breaker_states
#         registeraddress = 163 if self.address in (1, 2) else 296
#         value = self.read_mb_register(registeraddress)
#         if not value: return None
#         breaker_state_return = breaker_state[value]
#         logging.debug(breaker_state_return)
#         return breaker_state_return

#     def get_gcb_state(self):
#         logging.debug('get_gcb_state()')
#         registeraddress = 2 if self.address in (1, 2) else 7
#         value = self.read_mb_register(registeraddress)
#         if not value: return None
#         gcb_state = (1<<2&value)>>2 if self.address in (1, 2) else 1&value
#         logging.debug(gcb_state)
#         return gcb_state

    def get_chunk_intervals(self, adresses):
        logging.debug('get_chunk_intervals')

        chunk = 10
        chunk_requests = []

        chunk_start = adresses[0]
        chunk_len = 0

        for a in range(1, len(adresses)):
            chunk_len += 1
            if  adresses[a] == adresses[-1]:
                chunk_requests.append((chunk_start, chunk_len+1))
            elif chunk_len == chunk or not adresses[a]-adresses[a-1] == 1:
                chunk_requests.append((chunk_start, chunk_len))
                chunk_start = adresses[a]
                chunk_len = 0
        # [(45751, 10), (45761, 10), (45771, 2), (45774, 10), (45785, 4), (45807, 1), (45865, 10), (45875, 10), (45949, 9), (45963, 1), (45965, 10), (45975, 10), (45985, 10), (45995, 6), (46201, 10), (46211, 10), (46221, 5), (46248, 3)]
        return chunk_requests

    def get_protect_dict(self):
        logging.debug('get_protect_dict')
        protect_dict = {}
        if self.address in (1, 2):
            with open(config.protections_3516) as f:
                data_lines = f.readlines()
        elif self.address in (3, 4, 5):
            with open(config.protections_3520) as f:
                data_lines = f.readlines()

        for p in data_lines:
            # [6211, 'Bus V L2-L3', 'Bus V L3-L1']
            protect_dict[int(p[:5])-40001] = [p[17:37].strip(), p[37:].strip()]
        return protect_dict
    
    def parse_data_line(self, s):
        addr = int(s[:5])-40001
        com_obj = int(s[17:26])
        name = s[26:41].strip()
        dim = s[41:46].strip()
        data_type = s[46:58].strip()
        data_len = int(s[58:60].strip())
        dec = s[60:63].strip()
        data_min = s[63:70].strip()
        data_max = s[70:77].strip()
        group = s[77:].strip()
        return [addr, com_obj, name, dim, data_type, data_len, dec, data_min, data_max, group]

    
    def get_modbus_table(self):
        logging.debug('get_modbus_table()')
        if self.address in (1, 2):
            with open(config.mb_table_3516, encoding='cp1252') as f:
                data_lines = f.readlines()
        else:
            with open(config.mb_table_3520, encoding='cp1252') as f:
                data_lines = f.readlines()

        data_dict = {} # Словарь из modbus таблицы

        for i in data_lines[2:]:
            if i[0] == '\n': # Если пустая строка, то заканчиваем опрос
                break
            elif i[0] == '4': # Если начинается с 4-х, то
                # парсим, получается: (40027, 9166, Manifold Temp, °C, Integer, 2, 0, 0, 150, AnalogInputs 1)
                line = self.parse_data_line(i)
                # если группа есть в values_if_changed и regular_values и нет в val_ignore_list
                if line[9] in (config.values_if_changed + config.regular_values) and line[2] not in (config.val_ignore_list):
                    data_dict[line[0]] = {
                        'Name': line[2],
                        'Name_in_bd': line[2].replace(' ', '_').replace('-', '_').replace('+', '_plus_').replace('<', '_down_').replace('>', '_up_'),
                        'Dim': line[3],
                        'Type': line[4],
                        'Len': line[5],
                        'Dec': line[6],
                        'Min': line[7],
                        'Max': line[8],
                        'Group': line[9],
                        'Prev_val': None,
                        'Curr_val': None
                    }
        # словарь вида: {..., 2: {'Name': 'BIN', 'Name_in_bd': 'BIN', 'Dim': '','Type': 'Binary#1', 'Len': 2, 'Dec': '-', 'Min': '-', 'Max': '-', 'Group': 'Bin inputs CU', 'Prev_val': None, 'Curr_val': None}, ...}
        return data_dict

    # Функция форматирования регистров
    def _formating_register(self, adr, reg):
        # Если бинарное число, то возвращаю в двоичном виде
        if self.modbus_table[adr]['Type'].lower()[:3] == 'bin':
            return format(reg, '#016b')
        # Отрицательное число определяю по косвенным признакам и списку исключений
        elif (not self.modbus_table[adr]['Min'].isdigit()) and len(self.modbus_table[adr]['Min'])-1 and self.modbus_table[adr]['Min'][-1]!='*' and reg&0b1000000000000000:
            reg = reg - 65535
        # Десятичная точка
        dec = self.modbus_table[adr]['Dec']
        if dec!='-':
            reg = reg/10**int(dec)
        return reg

    def get_update(self):
        logging.debug(f'Entering in get_update()')
        if not self.read_mb_register(5): # проверка узла на доступность
            for v in self.modbus_table.values():
                v['Curr_val'] = None
            logging.debug(f'get_update() - None')
            return None
        chank_arr = self.get_chunk_intervals(list(self.modbus_table.keys()))
        for chank in chank_arr:
            regs = self.read_mb_registers(chank[0], chank[1])
            if regs:
                for c in range(len(regs)):
                    adr = chank[0] + c
                    self.modbus_table[adr]['Prev_val'] = self.modbus_table[adr]['Curr_val']
                    self.modbus_table[adr]['Curr_val'] = self._formating_register(adr, regs[c])

        # Освежаю защиты и статусы
        self.update_events()
        # Обновляю длинные регистры
        self.run_hours = self.get_run_hours()
        self.totRunPact_P = self.get_totRunPact_P()
        self.totRunPact_Q = self.get_totRunPact_Q()
        self.kWhours = self.get_kWhours()

        logging.debug(f'ГПГУ{self.address}. get_update() - успешно')
        return None


    def get_protections(self):
        logging.debug(f'get_protect(genset {self.address})')
        level = config.protect_levels
        sensfail = config.sensfails

        if self.address in (1, 2):
            with open(config.protections_3516) as f:
                data_lines = f.readlines()
        elif self.address in (3, 4, 5):
            with open(config.protections_3520) as f:
                data_lines = f.readlines()

        adresses = [int(line[:5])-40001 for line in data_lines]

        protections = self.get_protect_dict()
        protections_return = ''

        for interval in self.get_chunk_intervals(adresses):
            value = self.read_mb_registers(interval[0], interval[1])
            if not value: return None
            for i in range(interval[1]):
                 protections[interval[0]+i].append(value[i])

        for k, v in protections.items():
            # (749, ['Rem Start/Stop', 'Emergency Stop', 2])
            addr, protect2, protect1, protection = k, v[0], v[1], v[2]

            if not protection: continue

            prot1_level1 = 0b0000000000000111 & protection
            prot1_level2 = (0b0000000000111000 & protection)>>3
            prot1_sens = (0b0000000011000000 & protection)>>6
            prot2_level1 = 0b0000011100000000 & protection>>8
            prot2_level2 = (0b0011100000000000 & protection)>>11
            prot2_sens = (0b1100000000000000 & protection)>>14

            # Если уровень active или confirmed.
            if prot1_level1 in (2,): protections_return += f'{protect1}. Level 1: {level[prot1_level1]}\n'
            if prot1_level2 in (2,): protections_return += f'{protect1}. Level 2: {level[prot1_level2]}\n'
            if prot1_sens: protections_return += f'{protect1}. Sensor failure: {sensfail[prot1_sens]}\n'
            if prot2_level1 in (2,): protections_return += f'{protect2}. Level 1: {level[prot2_level1]}\n'
            if prot2_level2 in (2,): protections_return += f'{protect2}. Level 2: {level[prot2_level2]}\n'
            if prot2_sens: protections_return += f'{protect2}. Sensor failure: {sensfail[prot2_sens]}\n'

        logging.debug(protections_return)

        if protections_return: return protections_return
        else: return None

    def get_gcb_state(self):
        if self.address in (1, 2):
            gcb = self.read_mb_register(2)
            return (gcb&4)>>2 if gcb else None

        elif self.address in (3, 4, 5):
            gcb = self.read_mb_register(7)
            return gcb&1 if gcb else None


    def get_mcb_state(self):
        if self.address in (1, 2):
            mcb = self.read_mb_register(136)
            return mcb&1 if mcb else None

        elif self.address in (3, 4, 5):
            mcb = self.read_mb_register(230)
            return mcb&1 if mcb else None

    def update_events(self):
#         self.protects['prev_protects'] = self.protects['current_protects']
#         self.protects['current_protects'] =  self.get_protections()

        # Значения для запроса бота
        adr = 263 if self.address in (1, 2) else 463
        self.modbus_table[adr]['Fast_value'] = self.read_mb_register(adr)

        self.gcb_state['prev_gcb_state'] =  self.gcb_state['current_gcb_state']
        self.gcb_state['current_gcb_state'] =  self.get_gcb_state()

        self.mcb_state['prev_mcb_state'] =  self.mcb_state['current_mcb_state']
        self.mcb_state['current_mcb_state'] =  self.get_mcb_state()

        self.engine_state['prev_engine_state'] =  self.engine_state['current_engine_state']
        self.engine_state['current_engine_state'] =  self.get_engine_state()

def send_msg(chat_id, text, disable_web_page_preview=None, reply_to_message_id=None, reply_markup=None, parse_mode=None, disable_notification=None, timeout=None):
    logging.debug(f'Отправка сообщения: {text}')
    try:
        tb.send_message(chat_id, text, disable_web_page_preview, reply_to_message_id, reply_markup, parse_mode, disable_notification, timeout)
    except Exception as e:
        logging.error(e)
        print(e)
        
def mcb_open_record(g1, g2, g3, g4, g5):
    conn = sqlite3.connect(config.raspi_bd)
    cur = conn.cursor()
    # очищаю таблицу
    try:
        cur.execute('DELETE FROM mcb_open_log_table')
    # иначе создаю новую
    except:
        cur.execute('CREATE TABLE mcb_open_log_table (date_time VARCHAR(20) PRIMARY KEY, flex_gen INT, genset_1 INT, genset_2 INT, genset_3 INT, genset_4 INT, genset_5 INT)')
    conn.commit()
    cur.close()
    conn.close()

    ess = client(host=config.ess_hostname)

    start_time = time.time()
    xlsx_name = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.xlsx')

    while 1:
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')
        ess_active_power = ess.read(FC=4, ADR=36, LEN=1)[0]
        g1_active_power = g1.read_mb_register(263)
        g2_active_power = g2.read_mb_register(263)
        g3_active_power = g3.read_mb_register(463)
        g4_active_power = g4.read_mb_register(463)
        g5_active_power = g5.read_mb_register(463)
        mcb_state = g1.get_mcb_state() # Смотрю MCB по 1-й машине
        
        conn = sqlite3.connect(config.raspi_bd)
        cur = conn.cursor()
        ins = f'INSERT INTO mcb_open_log_table VALUES (?, ?, ?, ?, ?, ?, ?)'
        data = (date, ess_active_power, g1_active_power, g2_active_power, g3_active_power, g4_active_power, g5_active_power)
        cur.execute(ins, data)
        conn.commit()
        cur.close()
        conn.close()
        if not mcb_state or mcb_state == None: break
        # Пока спрыгиваю по таймеру
#         if (time.time()-start_time)>10: break

    conn = sqlite3.connect(config.raspi_bd)
    df = pd.read_sql('SELECT * FROM mcb_open_log_table', conn)
    conn.close()

    writer = pd.ExcelWriter(config.xlsx_path + xlsx_name, engine='xlsxwriter')
    df.to_excel(writer, 'Sheet1')
    writer.save()

    # Скидываю таблицу, пока только себе
    doc = open(config.xlsx_path + xlsx_name, 'rb')
    tb.send_document(config.my_telegram_id, doc)

def fast_power_values_to_db(pwrs):
    pwrs = pwrs
    ess = client(host=config.ess_hostname)
    dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ess_active_power = ess.read(FC=4, ADR=36, LEN=1)[0]
    pwrs.insert(0, dt)
    pwrs.insert(1, ess_active_power)

    conn = sqlite3.connect(config.raspi_bd)
    curs = conn.cursor()
    # удаление нужно будет потом открутить
    ins = f'DELETE FROM {config.fast_power_values}'
    curs.execute(ins)
    conn.commit()

    ins = f'INSERT INTO {config.fast_power_values} (date_time, ESS_Power, Genset1_Act_power, Genset2_Act_power, Genset3_Act_power, Genset4_Act_power, Genset5_Act_power) VALUES (?, ?, ?, ?, ?, ?, ?)'
    curs.execute(ins, pwrs)
    conn.commit()

    curs.close()
    conn.close()

def trim_fast_power_values_to_db():
    conn = sqlite3.connect(config.raspi_bd)
    curs = conn.cursor()
    ins = f'SELECT date_time FROM {config.fast_power_values}'
    cur.execute(ins)
    data = cur.fetchall()
    if len(data)>86400:
        pass
        # Тут нужно обрезать БД до нужного размера
