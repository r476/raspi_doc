import minimalmodbus
import config
import logging
import telebot

tb = telebot.TeleBot(config.token)

# logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', filename=config.log_path, level=logging.DEBUG)
# logging.disable(logging.CRITICAL)

class Genset(minimalmodbus.Instrument):

    def __init__(self, port, slaveaddress):
        logging.debug(f'Инициализация объекта: ГПГУ{slaveaddress}')
        super().__init__(port=port, slaveaddress=slaveaddress)
        self.serial.baudrate = config.baudrate
#         self.chunk_intervals = self.get_chunk_intervals()
        self.protect_dict = self.get_protect_dict()
        self.modbus_table = self.get_modbus_table()
        self.get_update()

#         self.engine_state = self.get_engines_state()
#         self.prev_engine_state = self.engine_state

#         self.breaker_state = self.get_breaker_state()
#         self.prev_breaker_state = self.breaker_state

#         self.gcb_state = self.get_gcb_state()
#         self.prev_gcb_state = self.gcb_state

#         self.protections = self.get_protections()
#         self.prev_protections = self.protections

#         self.power = self.read_mb_register(263)

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

    def get_engines_state(self):
        logging.debug('get_engines_state()')
        engine_state = config.engine_states
        registeraddress = 162 if self.address in (1, 2) else 295
        value = self.read_mb_register(registeraddress)
        if not value: return None
        engine_state_return = engine_state[value]
        logging.debug(engine_state_return)
        return engine_state_return

    def get_breaker_state(self):
        logging.debug('get_breakers_state()')
        breaker_state = config.breaker_states
        registeraddress = 163 if self.address in (1, 2) else 296
        value = self.read_mb_register(registeraddress)
        if not value: return None
        breaker_state_return = breaker_state[value]
        logging.debug(breaker_state_return)
        return breaker_state_return

    def get_gcb_state(self):
        logging.debug('get_gcb_state()')
        registeraddress = 2 if self.address in (1, 2) else 7
        value = self.read_mb_register(registeraddress)
        if not value: return None
        gcb_state = (1<<2&value)>>2 if self.address in (1, 2) else 1&value
        logging.debug(gcb_state)
        return gcb_state

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
                line = self.parse_data_line(i)
                if line[9] in (config.values_if_changed + config.regular_values) and line[2] not in (config.val_ignore_list):
                    data_dict[line[0]] = {
                        'Name': line[2],
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
        return data_dict
    
    # Функция форматирования регистров
    def _formating_register(self, adr, reg):
        # Если бинарное число, то возвращаю в двоичном виде
        if self.modbus_table[adr]['Type'].lower()[:3] == 'bin':
            return format(reg, '#016b')
        # Отрицательное число определяю по косвенным признакам
        elif (not self.modbus_table[adr]['Min'].isdigit()) and len(self.modbus_table[adr]['Min'])-1 and self.modbus_table[adr]['Min'][-1]!='*' and reg&0b1000000000000000:
            reg = reg - 65535
        # Десятичная точка
        dec = self.modbus_table[adr]['Dec']
        if dec!='-':
            reg = reg/10**int(dec)
        return reg
    
    def get_update(self):
        if not self.read_mb_register(5):
            return None
        chank_arr = self.get_chunk_intervals(list(self.modbus_table.keys()))
        for chank in chank_arr:
            regs = self.read_mb_registers(chank[0], chank[1])
            if regs:
                for c in range(len(regs)):
                    adr = chank[0] + c
                    self.modbus_table[adr]['Prev_val'] = self.modbus_table[adr]['Curr_val']
                    self.modbus_table[adr]['Curr_val'] = self._formating_register(adr, regs[c])
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
            # (5750, ['Rem Start/Stop', 'Emergency Stop', 2])
            addr, protect2, protect1 = k, v[0], v[1]
            protection = v[2]
            if not protection: continue

            prot1_level1 = 0b0000000000000111 & protection
            prot1_level2 = (0b0000000000111000 & protection)>>3
            prot1_sens = (0b0000000011000000 & protection)>>6
            prot2_level1 = 0b0000011100000000 & protection>>8
            prot2_level2 = (0b0011100000000000 & protection)>>11
            prot2_sens = (0b1100000000000000 & protection)>>14

            # Если уровень 'active или confirmed'.
            if prot1_level1 in (2,): protections_return += f'{protect1}. Level 1: {level[prot1_level1]}\n'
            if prot1_level2 in (2,): protections_return += f'{protect1}. Level 2: {level[prot1_level2]}\n'
            if prot1_sens: protections_return += f'{protect1}. Sensor failure: {sensfail[prot1_sens]}\n'
            if prot2_level1 in (2,): protections_return += f'{protect2}. Level 1: {level[prot2_level1]}\n'
            if prot2_level2 in (2,): protections_return += f'{protect2}. Level 2: {level[prot2_level2]}\n'
            if prot2_sens: protections_return += f'{protect2}. Sensor failure: {sensfail[prot2_sens]}\n'

        logging.debug(protections_return)

        if protections_return: return protections_return
        else: return None

    def updates_values(self):
        self.prev_engine_state = self.engine_state
        self.prev_breaker_state = self.breaker_state
        self.prev_gcb_state = self.gcb_state
        self.prev_protections = self.protections

        self.engine_state = self.get_engines_state()
        self.breaker_state = self.get_breaker_state()
        self.gcb_state = self.get_gcb_state()
        self.protections = self.get_protections()

def send_msg(chat_id, text, disable_web_page_preview=None, reply_to_message_id=None, reply_markup=None, parse_mode=None, disable_notification=None, timeout=None):
    logging.debug(f'Отправка сообщения: {text}')
    try:
        tb.send_message(chat_id, text, disable_web_page_preview, reply_to_message_id, reply_markup, parse_mode, disable_notification, timeout)
    except Exception as e:
        logging.error(e)
        print(e)
