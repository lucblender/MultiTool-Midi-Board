import machine
from machine import Pin

from OLED_SPI import OLED_2inch23

from MenuNavigationMap import *

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
    def __init__(self, gatePin, cvI2cAddr, modI2cAddr, inverted_gate, limit_cv_5v):
        print(self, gatePin, cvI2cAddr, modI2cAddr)
        self.gatePin = gatePin
        self.cvI2cAddr = cvI2cAddr
        self.modI2cAddr = modI2cAddr
        
        self.inverted_gate = inverted_gate
        self.limit_cv_5v = limit_cv_5v
        
        self.gateOut = Pin(self.gatePin, mode=Pin.OUT)
        self.write_cv(33)
        self.write_mode(0)
        self.write_gate(0)
        
    # midi_note as int A0 = 33 
    def write_cv(self, midi_note):  
        mvValue = midi_to_mv(midi_note)
        dacValue = mvValue/10000*4095
        if self.limit_cv_5v and dacValue > 2047:
             dacValue = 2047
        self.__write_DAC(dacValue, self.cvI2cAddr)
        
    # modeValue in %
    def write_mode(self, modeValue): 
        dacValue = (modeValue/127*4095)/2
        self.__write_DAC(dacValue, self.modI2cAddr)

    def write_gate(self, gate):
        if self.inverted_gate == True:
            if gate :
                self.gateOut.value(0)
            else:
                self.gateOut.value(1)
        else:
            if gate :
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
        
class motPot:
    def __init__(self, adc_pin):
        self.adc_pin = adc_pin
        self.adc = machine.ADC(self.adc_pin)
        self.motor_enabled = False
        self.value = 0
        
    def get_last_adc_value(self):
        return self.value
        
    def poll_adc_value(self):
        self.value = self.adc.read_u16()
        return self.value

class MultiToolMidiConfig:
    def __init__(self):
        self.gate_cv_mode_modules = []
        self.gate_cv_mode_modules.append(GateCvModeModule(0,0x61,0x60, False, False))
        self.gate_cv_mode_modules.append(GateCvModeModule(2,0x63,0x62, True, False))
        self.gate_cv_mode_modules.append(GateCvModeModule(13,0x65,0x64, False, False))
        self.gate_cv_mode_modules.append(GateCvModeModule(14,0x67,0x66, False, False))
        
        self.mot_pot_modules = []
        self.mot_pot_modules.append(motPot(28))
        self.mot_pot_modules.append(motPot(27))
        self.mot_pot_modules.append(motPot(26))
        self.mot_pot_percent_value = [0,0,0]
        
        self.midi_channels_for_modules = [4,5,6,16]
        self.OLED = None
        
        self.menu_navigation_map = get_menu_navigation_map()
        
        self.display_menu = True # TODO start in menu
        self.current_menu_len = len(self.menu_navigation_map)
        self.current_menu_selected = 0
        self.menu_path = []
        
        self.menu_navigation_map["cv/gate/mod"]["module a"]["data_pointer"] = self.gate_cv_mode_modules[0]
        self.menu_navigation_map["cv/gate/mod"]["module b"]["data_pointer"] = self.gate_cv_mode_modules[1]
        self.menu_navigation_map["cv/gate/mod"]["module c"]["data_pointer"] = self.gate_cv_mode_modules[2]
        self.menu_navigation_map["cv/gate/mod"]["module d"]["data_pointer"] = self.gate_cv_mode_modules[3]
        
    def poll_adc_values(self):
        old_pot_value = []
        for value in self.mot_pot_percent_value:
            old_pot_value.append(value)
            
        index = 0
        for mot_Pot_module in self.mot_pot_modules:
            self.mot_pot_percent_value[index] = (mot_Pot_module.poll_adc_value()*100)>>16            
            index = index+1

        need_update = False
        for i in range(0,3):
            if old_pot_value[i] != self.mot_pot_percent_value[i]:
                need_update = True
        if need_update:
            self.OLED.set_need_display()
            
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

    """
    self.menu_navigation_map = get_menu_navigation_map()

    self.display_menu = True # TODO start in menu
    self.current_menu_len = len(self.menu_navigation_map)
    self.current_menu_selected = 0
    self.menu_path = []
    """
    def up_pressed(self):
        if self.display_menu == True:                
            if self.current_menu_selected > 0:
                self.current_menu_selected = self.current_menu_selected - 1
                self.OLED.set_need_display()
            print("up_pressed")
    def down_pressed(self):
        if self.display_menu == True:
            if self.current_menu_selected < self.current_menu_len-1:
                self.current_menu_selected = self.current_menu_selected + 1
                self.OLED.set_need_display()
            print("down_pressed")
    def back_pressed(self):
        if self.display_menu == True:
            if len(self.menu_path) > 0:
                self.menu_path = self.menu_path[:-1]
                self.current_menu_selected = 0            
                self.current_menu_len = len(self.get_current_menu_keys())
            else:
                self.display_menu = False
            self.OLED.set_need_display()

            print("back_pressed")
    def enter_pressed(self):
        if self.display_menu == True:
            current_keys = self.get_current_menu_keys()
            self.menu_path.append(current_keys[self.current_menu_selected])
            self.current_menu_selected = 0            
            self.current_menu_len = len(self.get_current_menu_keys())
            print("enter_pressed")            
            self.OLED.set_need_display()
        else:
            self.display_menu = True   
            self.OLED.set_need_display()
    def get_current_menu_keys(self):
        if len(self.menu_path) == 0:
            current_keys = list(self.menu_navigation_map.keys())
        else:
            tmp_menu_selected = self.menu_navigation_map
            for key_path in self.menu_path:
                tmp_menu_selected = tmp_menu_selected[key_path]
                
            current_keys = list(tmp_menu_selected.keys())

        return current_keys
        
