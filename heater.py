from threading import Thread
from time import sleep

def l(x):
    while True:
        print(x)

threads = []

for i in range(0, 4):
    t = Thread(target=l, args=[i+1], daemon=True)
    t.start()
    threads.append(t)

while True:
    try:
        l(0)
    except KeyboardInterrupt:
        exit()