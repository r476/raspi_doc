#!/usr/bin/python3

import doc_objects
import time

doc_objects.send_msg(doc_objects.config.my_telegram_id, 'Старт скрипта.')

g1 = doc_objects.Genset('/dev/ttyS0', 1)
g2 = doc_objects.Genset('/dev/ttyS0', 2)
g3 = doc_objects.Genset('/dev/ttyS0', 3)
g4 = doc_objects.Genset('/dev/ttyS0', 4)
g5 = doc_objects.Genset('/dev/ttyS0', 5)

doc = (g1, g2, g3, g4, g5)

doc_objects.init_bd(doc)

start_interval = time.time()

while 1:
    # Если прошел интервал, то обновляем все параметры и пишем в БД, иначе просто проверяем события.
    if (time.time()-start_interval) > doc_objects.config.db_interval:
        start_interval = time.time()
        for g in doc:
            g.get_update()
        doc_objects.regular_values_to_bd(doc)
    else:
        power_in_bd = []
        for g in doc:
            g.update_events()
            # После обновления добавляю последние значения мошности в список, потом их в БД
            adr = 263 if g.address in (1, 2) else 463
            power_in_bd.append(g.modbus_table[adr]['Fast_value'])
            # Пока протекты прикрою, возможно они не стоят того
#             if g.protects['current_protects'] != g.protects['prev_protects']:
#                 doc_objects.send_msg(723253749, f"ГПГУ{g.address}. protects: {g.protects['current_protects']}")

            if g.gcb_state['current_gcb_state'] != g.gcb_state['prev_gcb_state']:
                doc_objects.send_msg(doc_objects.config.my_telegram_id, f"ГПГУ{g.address} {'включена в работу' if g.gcb_state['current_gcb_state'] else 'выключена'}")

            if g.mcb_state['current_mcb_state'] != g.mcb_state['prev_mcb_state']:
                doc_objects.send_msg(doc_objects.config.my_telegram_id, f"ГПГУ{g.address}. {'MCB замкнут' if g.mcb_state['current_mcb_state'] else 'MCB разомкнут'}")
                doc_objects.mcb_open_record(g1, g2, g3, g4, g5) # Запускаю быстрое логгирование, на период работы в острове.

            if g.engine_state['current_engine_state'] != g.engine_state['prev_engine_state']:
                if g.engine_state['current_engine_state'] in ('Аварийная остановка', ):
                    doc_objects.send_msg(doc_objects.config.my_telegram_id, f"ГПГУ{g.address}. {g.engine_state['current_engine_state']}")

        doc_objects.fast_power_values_to_db(power_in_bd)
        print((f'{time.time() - start_interval:.1f} seconds'))
