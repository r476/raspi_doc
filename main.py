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


while 1:

#     start_time = time.time()
    for g in doc:
        g.updates_values()

        if not g.engine_state in (g.prev_engine_state, None) and g.prev_engine_state != None:
            print(f'ГПГУ{g.address}, {g.engine_state}: {g.engine_state}')
            doc_objects.send_msg(723253749, f'ГПГУ{g.address}, engine_state: {g.engine_state}')

        if not g.breaker_state in (g.prev_breaker_state, None) and g.prev_breaker_state != None:
            print(f'ГПГУ{g.address}, {g.breaker_state}: {g.breaker_state}')
            doc_objects.send_msg(723253749, f'ГПГУ{g.address}, breaker_state: {g.breaker_state}')

        if not g.gcb_state in (g.prev_gcb_state, None):
            print(f'ГПГУ{g.address}, {g.prev_gcb_state}: {g.gcb_state}')
            state = 'Close' if g.gcb_state else 'Open'
            doc_objects.send_msg(723253749, f'ГПГУ{g.address}, gcb_state: {state}')

        if not g.protections in (g.prev_protections, None) and g.prev_protections != None:
            print(f'ГПГУ{g.address}: {g.protections}')
            doc_objects.send_msg(723253749, f'ГПГУ{g.address}: {g.protections}')
    time.sleep(3)
#     print((f'{time.time() - start_time:.1f} seconds'))
