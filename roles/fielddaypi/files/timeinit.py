#!/usr/bin/python3

import subprocess
from time import sleep

p = subprocess.Popen(['/usr/bin/gpspipe', '-r'], stdout=subprocess.PIPE)
while True:
    l = p.stdout.readline().decode()
    if l.startswith('$GPRMC'):
        pieces = l.split(',')
        time = pieces[1][:6]
        date = pieces[9]
        break

p.stdout.close()
p.terminate()

day = date[:2]
month = date[2:4]
year = date[4:]
sec = time[4:]
time = time[:4]

stamp = '%s%s%s20%s.%s' % (month, day, time, year, sec)

subprocess.check_call(['/usr/bin/date', '-u', stamp])

p.wait()
