#!/usr/bin/env python3

import telebot
import minimalmodbus 
import time

g1 = minimalmodbus.Instrument('/dev/ttyS0', 1)
g1.serial.baudrate = 19200

g2 = minimalmodbus.Instrument('/dev/ttyS0', 2)
g2.serial.baudrate = 19200

g3 = minimalmodbus.Instrument('/dev/ttyS0', 3)
g3.serial.baudrate = 19200

g4 = minimalmodbus.Instrument('/dev/ttyS0', 4)
g4.serial.baudrate = 19200

g5 = minimalmodbus.Instrument('/dev/ttyS0', 5)
g5.serial.baudrate = 19200

token = '1325955552:AAHQJzvhu-IhcMpsVGX5dUsfXTJ7fFECoJs'
tb = telebot.TeleBot(token)

gensets = ('ГПГУ 1', 'ГПГУ 2', 'ГПГУ 3', 'ГПГУ 4', 'ГПГУ 5')
doc = (g1, g2, g3, g4, g5)

def read_mb_register(i, reg):
    for c in range(10):
        try:
            return i.read_register(reg)
        except Exception as e:
            continue
    return -1

def get_engines_state():
    engine_state_3516 = ('Init', 'Ready', 'NotReady', 'Prestart', 'Cranking', 'Pause', 'Starting', 'Running', 'Loaded', 'Soft unld', 'Cooling', 'Stop', 'Shutdown', 'Ventil', 'EmergMan', 'Cooldown', 'Offload', 'Soft load', 'WaitStop', 'Warming', 'SDVentil', None)
    engine_state_3520 = ('Init', 'Ready', 'NotReady', 'Prestart', 'Cranking', 'Pause', 'Starting', 'Running', 'Loaded', 'Soft unld', 'Cooling', 'Stop', 'Shutdown', 'Ventil', 'EmergMan', 'Cooldown', 'Offload', 'Soft load', 'WaitStop', 'Warming', 'SDVentil', 'WD test', 'GasVTest', 'StrtCndWai', None)
    return [engine_state_3516[read_mb_register(g1, 162)], engine_state_3516[read_mb_register(g2, 162)], engine_state_3520[read_mb_register(g3, 295)], engine_state_3520[read_mb_register(g4, 295)], engine_state_3520[read_mb_register(g5, 295)]]

def get_breakers_state():
    breaker_state = ('Init', 'BrksOff', 'IslOper', 'MainsOper', 'ParalOper', 'RevSync', 'Synchro', 'MainsFlt', 'ValidFlt', 'MainsRet', 'MultIslOp', 'MultParOp', 'EmergMan', 'StrUpSync', None)
    return [breaker_state[read_mb_register(g1, 163)], breaker_state[read_mb_register(g2, 163)], breaker_state[read_mb_register(g3, 296)], breaker_state[read_mb_register(g4, 296)], breaker_state[read_mb_register(g5, 296)]]

def get_protect(genset):
    level = ['inactive', 'N/A', 'active, confirmed', 'active, but blocked or delay still running', 'previously active, not confirmed yet', 'N/A','active, not confirmed yet', 'active, not confirmed yet, blocked']
    sensfail = ['Sensor failure not active', 'Sensor failure active, confirmed', 'Sensor failure previously active, not confirmed yet', 'Sensor failure active, not confirmed yet']
    
    if genset.address == 1 or genset.address == 2:
        with open('protections_3516.txt') as f:
            data_lines = f.readlines()
    elif genset.address == 3 or genset.address == 4 or genset.address == 5:
        with open('protections_3520.txt') as f:
            data_lines = f.readlines()
        
    protections = []
    ret = []
    
    for line in data_lines:
        # [6211, 'Bus V L2-L3', 'Bus V L3-L1']
        protections.append((int(line[:5])-40001, line[17:37].strip(), line[37:].strip()))
        
    for p in protections:
        addr, protect2, protect1 = p
        protection = read_mb_register(genset, addr)
    
        prot1_level1 = 0b0000000000000111 & protection
        prot1_level2 = (0b0000000000111000 & protection)>>3
        prot1_sens = (0b0000000011000000 & protection)>>6
        prot2_level1 = 0b0000011100000000 & protection>>8
        prot2_level2 = (0b0011100000000000 & protection)>>11
        prot2_sens = (0b1100000000000000 & protection)>>14
        
        if prot1_level1: ret.append(f'{protect1}. Level 1: {level[prot1_level1]}\n')
        if prot1_level2: ret.append(f'{protect1}. Level 2: {level[prot1_level2]}\n')
        if prot1_sens: ret.append(f'{protect1}. Sensor failure: {sensfail[prot1_sens]}\n')
        if prot2_level1: ret.append(f'{protect2}. Level 1: {level[prot2_level1]}\n')
        if prot2_level2: ret.append(f'{protect2}. Level 2: {level[prot2_level2]}\n')
        if prot2_sens: ret.append(f'{protect2}. Sensor failure: {sensfail[prot2_sens]}\n')
        
    return ret

def get_gcb_state():
    g1_bin1, g2_bin1, g3_bin2, g4_bin2, g5_bin2 = read_mb_register(g1, 2), read_mb_register(g2, 2), read_mb_register(g3, 7), read_mb_register(g4, 7), read_mb_register(g5, 7) 
    return [(1<<2&g1_bin1)>>2, (1<<2&g2_bin1)>>2, 1&g3_bin2, 1&g4_bin2, 1&g5_bin2]

es_old = get_engines_state()
bs_old = get_breakers_state()
gs_old = get_gcb_state()

# Основной цикл
while 1:
    
#     start_time = time.time()

    es_new = get_engines_state()
    bs_new = get_breakers_state()
    gs_new = get_gcb_state()
    
#     print((f'{time.time() - start_time:.1f} seconds'))
    
    for i in range(5):
        # Читаю состояния двигателей
        if es_new[i] == None: es_new[i] = es_old[i] 
        if es_new[i] != es_old[i]:
            es_old[i] = es_new[i]
            if es_new[i] in ('Init', 'Ready', 'NotReady', 'Starting', 'Soft unld', 'Stop', 'Shutdown', 'Ventil', 'EmergMan', 'Cooldown', 'Offload', 'WaitStop', 'Warming', 'SDVentil'):
                tb.send_message(723253749, f'{gensets[i]}. Engine state: {es_new[i]}')
            if es_new[i] in ('NotReady', 'Shutdown', 'Soft unld'):
                msg = ''
                for i in get_protect(doc[i]):
                    msg += i
                if msg: tb.send_message(723253749, msg)
        # Читаю статусы выключателей
        if bs_new[i] == None: bs_new[i] = bs_old[i] 
        if bs_new[i] != bs_old[i]:
            bs_old[i] = bs_new[i]
            if bs_new[i] in ('Init', 'BrksOff', 'IslOper', 'ParalOper', 'RevSync', 'MainsFlt', 'ValidFlt', 'MainsRet', 'MultIslOp', 'EmergMan', 'StrUpSync'):
                tb.send_message(723253749, f'{gensets[i]}. Breaker state: {bs_new[i]}')
        # Читаю состояния выключателей
        if gs_new[i] != gs_old[i]:
            gs_old[i] = gs_new[i]
            if gs_new[i]:
                tb.send_message(723253749, f'{gensets[i]}. GCB Close')
            else:
                tb.send_message(723253749, f'{gensets[i]}. GCB Open')

    time.sleep(1)