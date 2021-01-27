import minimalmodbus, time

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

doc = [g1, g2, g3, g4, g5]

    # try:
        # return instrument.read_register(adr)
    # except Exception as e:
        # print(e)
    # return '---'

# with open('./mb_reg1.txt', 'r') as f:
    # s = f.readlines()

# data_arr = ''
# start_time = time.time()

# for i in s:
    # data_str = i.split('\t')
    # adr = int(data_str[0]) - 40001
    # param = data_str[1]
    # data = get_data(adr, int(data_str[3]))
    # unit = data_str[2][:-1]

    # data_arr += f'{param}:\t {data} {unit}\n'

# print(data_arr)
# print((f'{time.time() - start_time:.1f} seconds'))
# print(get_data(36, 2))

