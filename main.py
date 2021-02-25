#!/usr/bin/env python3

import doc_objects
import time

doc_objects.send_msg(723253749, 'Старт скрипта.')

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
        for g in doc:
            g.update_events()
            if g.protects['current_protects'] != g.protects['prev_protects']:
                doc_objects.send_msg(723253749, f"ГПГУ{g.address}. protects: {g.protects['current_protects']}")

            if g.gcb_state['current_gcb_state'] != g.gcb_state['prev_gcb_state']:
                doc_objects.send_msg(723253749, f"ГПГУ{g.address}. gcb_state: {'замкнут' if g.gcb_state['current_gcb_state'] else 'разомкнут'}")

            if g.mcb_state['current_mcb_state'] != g.mcb_state['prev_mcb_state']:
                doc_objects.send_msg(723253749, f"ГПГУ{g.address}. mcb_state: {'замкнут' if g.mcb_state['current_mcb_state'] else 'разомкнут'}")

            if g.engine_state['current_engine_state'] != g.engine_state['prev_engine_state']:
                if g.engine_state['current_engine_state'] in ('Shutdown', ):
                    doc_objects.send_msg(723253749, f"ГПГУ{g.address}. engine_state: {g.engine_state['current_engine_state']}")

        print((f'{time.time() - start_interval:.1f} seconds'))
