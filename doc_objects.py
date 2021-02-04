import minimalmodbus
import config
import logging
import telebot

tb = telebot.TeleBot(config.token)

# logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s', filename='/home/pi/Documents/PythonScripts/raspi_doc/debug_log', level=logging.DEBUG)
# logging.disable(logging.CRITICAL)

class Genset(minimalmodbus.Instrument):

    def __init__(self, port, slaveaddress):
        logging.debug(f'Инициализация объекта: ГПГУ{slaveaddress}')
        super().__init__(port=port, slaveaddress=slaveaddress)
        self.serial.baudrate = config.baudrate
        self.chunk_intervals = self.get_chunk_intervals()
        self.protect_dict = self.get_protect_dict()

        self.engine_state = self.get_engines_state()
        self.prev_engine_state = self.engine_state

        self.breaker_state = self.get_breaker_state()
        self.prev_breaker_state = self.breaker_state

        self.gcb_state = self.get_gcb_state()
        self.prev_gcb_state = self.gcb_state

        self.protections = self.get_protections()
        self.prev_protections = self.protections

#         self.power = self.read_mb_register(263)

    def read_mb_register(self, registeraddress, number_of_decimals=0, functioncode=3, signed=False):

        for c in range(15):
            try:
                return self.read_register(registeraddress, number_of_decimals, functioncode, signed)
            except Exception as e:
                pass
#                 logging.error(e)
        return None

    def read_mb_registers(self, registeraddress, number_of_registers, functioncode=3):
        for c in range(15):
            try:
                return self.read_registers(registeraddress, number_of_registers, functioncode)
            except Exception as e:
                pass
#                 logging.error(e)
        return None

    def get_engines_state(self):
        logging.debug('get_engines_state()')
        engine_state = ('Init', 'Ready', 'NotReady', 'Prestart', 'Cranking', 'Pause', 'Starting', 'Running', 'Loaded', 'Soft unld', 'Cooling', 'Stop', 'Shutdown', 'Ventil', 'EmergMan', 'Cooldown', 'Offload', 'Soft load', 'WaitStop', 'Warming', 'SDVentil', 'WD test', 'GasVTest', 'StrtCndWai')
        registeraddress = 162 if self.address in (1, 2) else 295
        value = self.read_mb_register(registeraddress)
        if not value: return None
        engine_state_return = engine_state[value]
        logging.debug(engine_state_return)
        return engine_state_return

    def get_breaker_state(self):
        logging.debug('get_breakers_state()')
        breaker_state = ('Init', 'BrksOff', 'IslOper', 'MainsOper', 'ParalOper', 'RevSync', 'Synchro', 'MainsFlt', 'ValidFlt', 'MainsRet', 'MultIslOp', 'MultParOp', 'EmergMan', 'StrUpSync', None)
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

    def get_chunk_intervals(self):
        logging.debug('get_chunk_intervals')
        if self.address in (1, 2):
            with open('/home/pi/Documents/PythonScripts/raspi_doc/protections_3516.txt') as f:
                data_lines = f.readlines()
        elif self.address in (3, 4, 5):
            with open('/home/pi/Documents/PythonScripts/raspi_doc/protections_3520.txt') as f:
                data_lines = f.readlines()

        adresses = [int(line[:5])-40001 for line in data_lines]

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
            with open('/home/pi/Documents/PythonScripts/raspi_doc/protections_3516.txt') as f:
                data_lines = f.readlines()
        elif self.address in (3, 4, 5):
            with open('/home/pi/Documents/PythonScripts/raspi_doc/protections_3520.txt') as f:
                data_lines = f.readlines()

        for p in data_lines:
            # [6211, 'Bus V L2-L3', 'Bus V L3-L1']
            protect_dict[int(p[:5])-40001] = [p[17:37].strip(), p[37:].strip()]
        return protect_dict

    def get_protections(self):
        logging.debug(f'get_protect(genset {self.address})')
        level = ('inactive', 'N/A', 'active, confirmed', 'active, but blocked or delay still running', 'previously active, not confirmed yet', 'N/A','active, not confirmed yet', 'active, not confirmed yet, blocked')
        sensfail = ('Sensor failure not active', 'Sensor failure active, confirmed', 'Sensor failure previously active, not confirmed yet', 'Sensor failure active, not confirmed yet')

        protections = self.get_protect_dict()
        protections_return = ''

        for interval in self.chunk_intervals:
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
            if prot1_level1 in (2, 3): protections_return += f'{protect1}. Level 1: {level[prot1_level1]}\n'
            if prot1_level2 in (2, 3): protections_return += f'{protect1}. Level 2: {level[prot1_level2]}\n'
            if prot1_sens: protections_return += f'{protect1}. Sensor failure: {sensfail[prot1_sens]}\n'
            if prot2_level1 in (2, 3): protections_return += f'{protect2}. Level 1: {level[prot2_level1]}\n'
            if prot2_level2 in (2, 3): protections_return += f'{protect2}. Level 2: {level[prot2_level2]}\n'
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
