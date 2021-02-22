import doc_objects
import time
import config

# doc_objects.send_msg(723253749, 'Старт скрипта.')

g1 = doc_objects.Genset('/dev/ttyS0', 1)
g2 = doc_objects.Genset('/dev/ttyS0', 2)
g3 = doc_objects.Genset('/dev/ttyS0', 3)
g4 = doc_objects.Genset('/dev/ttyS0', 4)
g5 = doc_objects.Genset('/dev/ttyS0', 5)

doc = (g1, g2, g3, g4, g5)

print(f'ГПГУ{g1.address}, наработка: {g1.read_mb_long(3586)} мч')
print(f'ГПГУ{g2.address}, наработка: {g2.read_mb_long(3586)} мч')
print(f'ГПГУ{g3.address}, наработка: {g3.read_mb_long(3821)} мч')
print(f'ГПГУ{g4.address}, наработка: {g4.read_mb_long(3821)} мч')
print(f'ГПГУ{g5.address}, наработка: {g5.read_mb_long(3821)} мч')
print()
