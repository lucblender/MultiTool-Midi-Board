import machine
from machine import Pin

from OLED_SPI import OLED_2inch23

sda=machine.Pin(4)
scl=machine.Pin(5)
i2c=machine.I2C(0,sda=sda, scl=scl, freq=400000)


devices = i2c.scan() #get devices because it's possible we don't have all the DAC soldered

volts_per_note = 1/12  # 1/12th V for 1V/Oct

#using  V/oct A0(33) = 0V A1 = 1V 
def midi_to_mv(midi_note):
    if midi_note < 33:
        midi_note = 33
    notemv = 1000 * ((midi_note-33) * volts_per_note)
    return int(notemv)

class GateCvModeModule:
    def __init__(self, gatePin, cvI2cAddr, modI2cAddr):
        print(self, gatePin, cvI2cAddr, modI2cAddr)
        self.gatePin = gatePin
        self.cvI2cAddr = cvI2cAddr
        self.modI2cAddr = modI2cAddr
        
        self.gateOut = Pin(self.gatePin, mode=Pin.OUT)
        self.write_cv(33)
        self.write_mode(0)
        self.write_gate(0)
        
    # midi_note as int A0 = 33 
    def write_cv(self, midi_note):  
        mvValue = midi_to_mv(midi_note)
        dacValue = mvValue/10000*4095
        self.__write_DAC(dacValue, self.cvI2cAddr)
        
    # modeValue in %
    def write_mode(self, modeValue): 
        dacValue = (modeValue/127*4095)/2
        self.__write_DAC(dacValue, self.modI2cAddr)

    def write_gate(self, gate):
        if gate:
            self.gateOut.value(1)
        else:
            self.gateOut.value(0)
            
            
    def __write_DAC(self,dacValue, addr): # 0 = 0V 4095 = 10V
        global devices
        if addr in devices:
            if(dacValue<0):
                dacValue = 0
            if(dacValue >4095):
                dacValue = 4095
            buf = bytearray(3)
            buf[0] = 0x40
            buf[1] = int(dacValue / 16)
            buf[2] = int(dacValue % 16) << 4
            i2c.writeto(addr, buf)
        

class MultiToolMidiConfig:
    def __init__(self):
        self.gate_cv_mode_modules = []
        self.gate_cv_mode_modules.append(GateCvModeModule(0,0x61,0x60))
        self.gate_cv_mode_modules.append(GateCvModeModule(2,0x63,0x62))
        self.gate_cv_mode_modules.append(GateCvModeModule(13,0x65,0x64))
        self.gate_cv_mode_modules.append(GateCvModeModule(14,0x67,0x66))
        
        self.midi_channels_for_modules = [4,5,6,7]
        self.OLED = None
        
        self.display_menu = False
        
    def setDisplay(self, OLED):
        self.OLED = OLED
        
    def note_on(self, note, midi_channel):
        if midi_channel in self.midi_channels_for_modules:
            gate_cv_mode_module_index = self.midi_channels_for_modules.index(midi_channel)
            gate_cv_mode_module = self.gate_cv_mode_modules[gate_cv_mode_module_index]
            gate_cv_mode_module.write_gate(1)
            gate_cv_mode_module.write_cv(note)
        
    def note_off(self, note, midi_channel):
        if midi_channel in self.midi_channels_for_modules:
            gate_cv_mode_module_index = self.midi_channels_for_modules.index(midi_channel)
            gate_cv_mode_module = self.gate_cv_mode_modules[gate_cv_mode_module_index]
            gate_cv_mode_module.write_gate(0)
        
    def mode_update(self, mode, midi_channel):
        if midi_channel in self.midi_channels_for_modules:
            gate_cv_mode_module_index = self.midi_channels_for_modules.index(midi_channel)
            gate_cv_mode_module = self.gate_cv_mode_modules[gate_cv_mode_module_index]
            gate_cv_mode_module.write_mode(mode)
        
        
        