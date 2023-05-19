import machine
from machine import Pin
from multiToolMidiConfig import *

import SimpleMIDIDecoder
import time
from OLED_SPI import OLED_2inch23

import _thread

MAX_DELAY_BEFORE_SCREENSAVER_S = 300
stop_thread = False
interrupt_lock = _thread.allocate_lock()

led = Pin("LED",Pin.OUT)

btn_up=Pin(3, mode=Pin.IN, pull = Pin.PULL_UP)
btn_down=Pin(6, mode=Pin.IN, pull = Pin.PULL_UP)
btn_enter=Pin(7, mode=Pin.IN, pull = Pin.PULL_UP)
btn_back=Pin(16, mode=Pin.IN, pull = Pin.PULL_UP)

pot_value_0 = machine.ADC(26)
pot_value_1 = machine.ADC(27)
pot_value_2 = machine.ADC(28)

debounce_time_btn_up=0
debounce_time_btn_down=0
debounce_time_btn_enter=0
debounce_time_btn_back=0

btn_up_pressed = False
btn_down_pressed = False
btn_enter_pressed = False
btn_back_pressed = False

btn_up_status   = btn_up.value()
btn_down_status  = btn_down.value()
btn_enter_status = btn_enter.value()
btn_back_status  = btn_back.value()

btn_up_status_old =btn_up_status 
btn_down_status_old =btn_down_status 
btn_enter_status_old = btn_enter_status 
btn_back_status_old =btn_back_status 
        
      
def btn_status_read():    
    global btn_up_status_old ,btn_up_status ,btn_down_status_old,btn_down_status ,btn_enter_status_old , btn_enter_status ,btn_back_status_old ,btn_back_status
    global btn_up_pressed, btn_down_pressed, btn_enter_pressed, btn_back_pressed 
    btn_up_status   = btn_up.value()
    btn_down_status  = btn_down.value()
    btn_enter_status = btn_enter.value()
    btn_back_status  = btn_back.value()
                                               
    if btn_up_status_old !=btn_up_status:
        btn_up_pressed = True
    if btn_down_status_old !=btn_down_status:
        btn_down_pressed = True    
    if btn_enter_status_old != btn_enter_status:
        btn_enter_pressed = True
    if btn_back_status_old !=btn_back_status:
        btn_back_pressed = True

    btn_up_status_old =btn_up_status 
    btn_down_status_old =btn_down_status 
    btn_enter_status_old = btn_enter_status 
    btn_back_status_old =btn_back_status 

# Initialise the serial MIDI handling
uart = machine.UART(0,31250)

multiToolMidiConfig = MultiToolMidiConfig()

OLED = OLED_2inch23(multiToolMidiConfig)

multiToolMidiConfig.setDisplay(OLED)

last_key_update = time.time()


def doMidiNoteOn(ch, cmd, note, vel):
    multiToolMidiConfig.note_on(note, ch, vel)
    
def doMidiNoteOff(ch, cmd, note, vel):
    multiToolMidiConfig.note_off(note, ch)
    
def doMidiThru(ch,cmd,data1,data2,idx = -1):
    if cmd == 176 and data1 == 1:        
        multiToolMidiConfig.mode_update(data2, ch)       
def doMidiStart():    
        multiToolMidiConfig.midi_start()
def doMidiStop():
        multiToolMidiConfig.midi_stop()
def doMidiClock():
        multiToolMidiConfig.midi_clock()
# initialise MIDI decoder and set up callbacks
md = SimpleMIDIDecoder.SimpleMIDIDecoder()
md.cbNoteOn (doMidiNoteOn)
md.cbNoteOff (doMidiNoteOff)
md.cbThru(doMidiThru)
md.cbMidiStart(doMidiStart)
md.cbMidiStop(doMidiStop)
md.cbClock(doMidiClock)
    
led.value(1)
time.sleep_ms(200)
led.value(0)
time.sleep_ms(200)

OLED.fill(0x0000) 
OLED.show()
OLED.display_helixbyte()
time.sleep(1)
OLED.display_debug()

def is_usb_connected():
    SIE_STATUS=const(0x50110000+0x50)
    CONNECTED=const(1<<16)
    SUSPENDED=const(1<<4)
        
    if (machine.mem32[SIE_STATUS] & (CONNECTED | SUSPENDED))==CONNECTED:
        return True
    else:
        return False

def screen_saver_thread():
    global stop_thread
    index = 0
    while not stop_thread:
        if OLED.is_screensaver() == True:           
            index+=1
            if index%16== 0:
                OLED.update_screensaver()
                index = 0
        elif OLED.need_display == True:
            OLED.display()
    
print("launch thread")
_thread.start_new_thread(screen_saver_thread, ())

if is_usb_connected() and (btn_up.value() and  btn_down.value() and  btn_enter.value() and  btn_back.value()) == 1:
    OLED.display_programming_mode()
    stop_thread = True
    print("exit")
else:
    print("launch main")
    led.value(1)
    OLED.set_need_display()
    index = 0
    
    multiToolMidiConfig.poll_adc_values()
    multiToolMidiConfig.mot_pot_modules[0].launch_to_setpoint(32768)
    multiToolMidiConfig.mot_pot_modules[1].launch_to_setpoint(32768)
    multiToolMidiConfig.mot_pot_modules[2].launch_to_setpoint(32768)
    while True:
        if time.time() - last_key_update > MAX_DELAY_BEFORE_SCREENSAVER_S and OLED.is_screensaver() == False:
            OLED.set_screensaver_mode()
            
        btn_status_read()
        multiToolMidiConfig.poll_adc_values()
        motors_status = multiToolMidiConfig.update_motors()
        
        if motors_status == True:            
            multiToolMidiConfig.poll_adc_values()
            OLED.set_need_display()
            
        if btn_up_pressed:
            last_key_update = time.time()
            btn_up_pressed = False
            multiToolMidiConfig.up_pressed()
            if OLED.is_screensaver() == True:
                OLED.reset_screensaver_mode()
                
        if btn_down_pressed:
            last_key_update = time.time()
            btn_down_pressed = False
            multiToolMidiConfig.down_pressed()
            if OLED.is_screensaver() == True:
                OLED.reset_screensaver_mode()
                
        if btn_enter_pressed:
            last_key_update = time.time()
            btn_enter_pressed = False
            multiToolMidiConfig.enter_pressed()
            if OLED.is_screensaver() == True:
                OLED.reset_screensaver_mode()
                
        if btn_back_pressed:
            last_key_update = time.time()
            btn_back_pressed = False
            multiToolMidiConfig.back_pressed()
            if OLED.is_screensaver() == True:
                OLED.reset_screensaver_mode()
                
        while (uart.any()):
            md.read(uart.read(1)[0])

          