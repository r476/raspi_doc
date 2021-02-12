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

while 1:
    start_time = time.time()
    
    for g in doc: 
        g.get_update()
        
    doc_objects.regular_values_to_bd(doc)
    
    print((f'{time.time() - start_time:.1f} seconds'))
