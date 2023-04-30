import machine
from machine import Pin

sda=machine.Pin(4)
scl=machine.Pin(5)
i2c=machine.I2C(0,sda=sda, scl=scl, freq=400000)
btn0=Pin(3, mode=Pin.IN, pull = Pin.PULL_UP)
btn1=Pin(6, mode=Pin.IN, pull = Pin.PULL_UP)
btn2=Pin(7, mode=Pin.IN, pull = Pin.PULL_UP)
btn3=Pin(16, mode=Pin.IN, pull = Pin.PULL_UP)

addresses = [0x60, 0x61, 0x63, 0x66, 0x67]

print('Scan i2c bus...')
devices = i2c.scan()

def Write_DAC(volt, addr): # 0 = 0V 4095 = 10V    
    buf = bytearray(3)
    buf[0] = 0x40
    buf[1] = int(volt / 16)
    buf[2] = int(volt % 16) << 4
    i2c.writeto(addr, buf)

if len(devices) == 0:
    print("No i2c device !")
else:
    print('i2c devices found:',len(devices))

for device in devices:
    print("Decimal address: ",device," | Hexa address: ",hex(device))
    
for addresse in addresses:
    Write_DAC(4095,addresse)
