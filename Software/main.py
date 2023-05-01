import machine
from machine import Pin
from multiToolMidiConfig import *

import SimpleMIDIDecoder
import time
from OLED_SPI import OLED_2inch23

led = Pin("LED",Pin.OUT)

btn0=Pin(3, mode=Pin.IN, pull = Pin.PULL_UP)
btn1=Pin(6, mode=Pin.IN, pull = Pin.PULL_UP)
btn2=Pin(7, mode=Pin.IN, pull = Pin.PULL_UP)
btn3=Pin(16, mode=Pin.IN, pull = Pin.PULL_UP)

# Initialise the serial MIDI handling
uart = machine.UART(0,31250)

multiToolMidiConfig = MultiToolMidiConfig()

OLED = OLED_2inch23(multiToolMidiConfig)

multiToolMidiConfig.setDisplay(OLED)



def doMidiNoteOn(ch, cmd, note, vel):
    print(ch, cmd, note, vel)
    multiToolMidiConfig.note_on(note, ch)
    
def doMidiNoteOff(ch, cmd, note, vel):
    print(ch, cmd, note, vel)
    multiToolMidiConfig.note_off(note, ch)
    
def doMidiThru(ch,cmd,data1,data2,idx = -1):
    print(ch,cmd,data1,data2,idx)
    if cmd == 176:        
        multiToolMidiConfig.mode_update(data2, ch)
    
# initialise MIDI decoder and set up callbacks
md = SimpleMIDIDecoder.SimpleMIDIDecoder()
md.cbNoteOn (doMidiNoteOn)
md.cbNoteOff (doMidiNoteOff)
md.cbThru(doMidiThru)
    
led.value(1)
time.sleep_ms(200)
led.value(0)
time.sleep_ms(200)

OLED.fill(0x0000) 
OLED.show()
OLED.display_helixbyte()
time.sleep(1)

if (btn0.value() and  btn1.value() and  btn2.value() and  btn3.value()) == 0:
    print("launch main")
    led.value(1)
    OLED.display()
    while True:
        # Check for MIDI messages
        if (uart.any()):
            md.read(uart.read(1)[0])
else:
    OLED.display_programming_mode()
    print("exit")
