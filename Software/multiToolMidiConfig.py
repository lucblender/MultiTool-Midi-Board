import machine
from machine import Pin, PWM
import time

from OLED_SPI import OLED_2inch23

from MenuNavigationMap import *
import json

JSON_CONFIG_FILE_NAME = "multi_tool_config.json"

sda=machine.Pin(4)
scl=machine.Pin(5)
i2c=machine.I2C(0,sda=sda, scl=scl, freq=400000)

expected_devices = [0x60, 0x61, 0x63, 0x64, 0x65, 0x66, 0x67]
devices = i2c.scan() #get devices because it's possible we don't have all the DAC soldered


def enum(**enums: int):
    return type('Enum', (), enums)

TimeDiv = enum(ONE_FOURTH=0,
            ONE_FOURTH_T=1,
            ONE_EIGHTH=2,
            ONE_EIGHTH_T=3,
            ONE_SIXTEENTH=4,
            ONE_SIXTEENTH_T=5,
            ONE_THIRTYSECOND=6,
            ONE_THIRTYSECOND_T=7)

DisplayScreen = enum(CV_GATE_SCREEN = 0,
                     MOT_POT_SCREEN = 1,
                     CONFIG_SCREEN = 2)

def timeDivToStr(local_time_div):
    if local_time_div == TimeDiv.ONE_FOURTH:
        return "1/4"
    elif local_time_div == TimeDiv.ONE_EIGHTH:
        return "1/8"
    elif local_time_div == TimeDiv.ONE_SIXTEENTH:
        return "1/16"
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND:
        return "1/32"
    elif local_time_div == TimeDiv.ONE_FOURTH_T:
        return "1/4T"
    elif local_time_div == TimeDiv.ONE_EIGHTH_T:
        return "1/8T"
    elif local_time_div == TimeDiv.ONE_SIXTEENTH_T:
        return "1/16T"
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND_T:
        return "1/32T"
    
def timeDivToTimeSplit(local_time_div):
    if local_time_div == TimeDiv.ONE_FOURTH:
        return 24
    elif local_time_div == TimeDiv.ONE_FOURTH_T:
        return 16
    elif local_time_div == TimeDiv.ONE_EIGHTH:
        return 12
    elif local_time_div == TimeDiv.ONE_EIGHTH_T:
        return 8
    elif local_time_div == TimeDiv.ONE_SIXTEENTH:
        return 6
    elif local_time_div == TimeDiv.ONE_SIXTEENTH_T:
        return 4
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND:
        return 3
    elif local_time_div == TimeDiv.ONE_THIRTYSECOND_T:
        return 2

volts_per_note = 1/12  # 1/12th V for 1V/Oct

#using  V/oct A0(33) = 0V A1 = 1V 
def midi_to_mv(midi_note):
    if midi_note < 33:
        midi_note = 33
    notemv = 1000 * ((midi_note-33) * volts_per_note)
    return int(notemv)

class GateCvModeModule:
    def __init__(self, gatePin, cvI2cAddr, modI2cAddr, gate_level, cv_max, mod_output, midi_channel):
        self.gatePin = gatePin
        self.cvI2cAddr = cvI2cAddr
        self.modI2cAddr = modI2cAddr
        
        self.gate_level = gate_level
        self.cv_max = cv_max
        self.mod_output = mod_output
        self.midi_channel = midi_channel
        
        self.gateOut = Pin(self.gatePin, mode=Pin.OUT)
        self.write_cv(0)
        self.write_mode(0)
        self.write_gate(0)
        
    # midi_note as int A0 = 33 
    def write_cv(self, midi_note):  
        mvValue = midi_to_mv(midi_note)
        dacValue = mvValue/10000*4095
        if self.cv_max == 1 and dacValue > 2047:
             dacValue = 2047
        self.__write_DAC(dacValue, self.cvI2cAddr)
        
    # modeValue in %
    def write_mode(self, modeValue): 
        dacValue = (modeValue/127*4095)/2
        self.__write_DAC(dacValue, self.modI2cAddr)
        
    # velocity 0..127
    def write_vel(self, velocity):
        dacValue = (velocity/127*4095)/2
        self.__write_DAC(dacValue, self.modI2cAddr)

    def write_gate(self, gate):
        if self.gate_level == 1:
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
        
class motPotPreset:
    def __init__(self, value0 = 0, value1 = 0, value2 = 32768):
        self.values = [0,0,0]
        self.percent_value = [0,0,0]
        self.set_value(0, value0)
        self.set_value(1, value1)
        self.set_value(2, value2)
        
    def set_value(self, index, raw_value):
        self.values[index]  = raw_value
        self.percent_value[index] = (raw_value*100)>>16 
        
class motPot:
    def __init__(self, adc_pin, pwm_pin_1, pwm_pin_2):
        self.adc_pin = adc_pin
        self.adc = machine.ADC(self.adc_pin)
        self.motor_enabled = False
        self.value = 0
        self.min_value = 0
        self.max_value = 65535
        self.detla_value = self.max_value -self.min_value
        pin_1 = Pin(pwm_pin_1, mode=Pin.OUT)
        self.pin_1_with_pwm = PWM(pin_1) # Attach PWM object on a pin

        pin_2 = Pin(pwm_pin_2, mode=Pin.OUT)
        self.pin_2_with_pwm = PWM(pin_2) # Attach PWM object on a pin

        self.pin_1_with_pwm.freq(1000)
        self.pin_2_with_pwm.freq(1000)
        
        self.stop_motor()
        
        self.lowest_speed = 28000
        self.highest_speed = 45000
        self.delta_speed = self.highest_speed-self.lowest_speed
        
        self.timeout_ms = 1000
        self.running = False        
        
        self.setpoint = 0        
        
        self.launch_to_setpoint_start_time = 0
        self.valid_position_range = 65
        
    def launch_to_setpoint(self, setpoint):
        self.setpoint = setpoint
        self.running = True
        self.launch_to_setpoint_start_time = time.ticks_ms()
        self.update_motor()
        
    def update_motor(self):
        if self.running == True:
            if (time.ticks_ms()-self.launch_to_setpoint_start_time) > self.timeout_ms:
                self.stop_motor()
                self.running = False
                print("Stopped motor due to timeout")
                return True
                
            else:
                if (self.setpoint - self.value)>self.valid_position_range:
                    self.compute_speed_P_controller()
                    self.run_forward(int(self.regulated_speed))
                elif (self.setpoint - self.value)< (0-self.valid_position_range):
                    self.compute_speed_P_controller()
                    self.run_backward(int(self.regulated_speed))
                else:
                    self.stop_motor()
                    self.running = False
                    return True
        return False                

    def compute_speed_P_controller(self):        
        error = abs(self.setpoint - self.value)

        self.regulated_speed = self.lowest_speed + self.delta_speed * (error/self.detla_value)

        print("self.regulated_speed ",self.regulated_speed)
        
    def run_forward(self, speed):
        self.pin_1_with_pwm.duty_u16(0)
        self.pin_2_with_pwm.duty_u16(speed)
        
    def run_backward(self, speed):
        self.pin_1_with_pwm.duty_u16(speed)
        self.pin_2_with_pwm.duty_u16(0)
        
    def stop_motor(self):        
        self.pin_1_with_pwm.duty_u16(0)
        self.pin_2_with_pwm.duty_u16(0)
        
    
    def get_last_adc_value(self):
        return self.value
        
    def poll_adc_value(self):
        self.value = self.adc.read_u16()
        return self.value

class SyncOut:
    def __init__(self, sync_pin):
        self.sync_pin = sync_pin
        self.sync_out = Pin(self.sync_pin, mode=Pin.OUT)
        self.sync_out.value(0)
        self.clock_counter = 0
        self.time_division = TimeDiv.ONE_FOURTH
        self.clock_polarity = 0
        # 0 = high pulse 1 = low pulse 2 = invert
    
    def sync_reset(self):
        self.clock_counter = 0
        self.sync_out.value(0)

    def clock(self):
        if self.clock_counter % timeDivToTimeSplit(self.time_division) == 0:
            if self.clock_polarity == 0:
                self.sync_out.value(1)
            if self.clock_polarity == 1:
                self.sync_out.value(0)
            if self.clock_polarity == 2:
                self.sync_out.value(not self.sync_out.value())
        elif self.sync_out.value() == 1 and self.clock_polarity == 0:
            self.sync_out.value(0)
        elif self.sync_out.value() == 0 and self.clock_polarity == 1:
            self.sync_out.value(1)
        self.clock_counter = (self.clock_counter+1)%48

class MultiToolMidiConfig:
    def __init__(self):
        self.gate_cv_mode_modules = []
        self.gate_cv_mode_modules.append(GateCvModeModule(0,0x61,0x60, 0, 0, 0,0))
        self.gate_cv_mode_modules.append(GateCvModeModule(2,0x63,0x62, 0, 0, 0,1))
        self.gate_cv_mode_modules.append(GateCvModeModule(13,0x65,0x64, 0, 0, 0,2))
        self.gate_cv_mode_modules.append(GateCvModeModule(14,0x67,0x66, 0, 0, 0,3))
        
        self.mot_pot_modules = []
        self.mot_pot_modules.append(motPot(28,22,21))
        self.mot_pot_modules.append(motPot(27,20,19))
        self.mot_pot_modules.append(motPot(26,18,17))
        self.mot_pot_percent_value = [0,0,0]
        
        self.motPotPresets = []
        for i in range(0,16):
            self.motPotPresets.append(motPotPreset())

        self.current_selected_motPot_preset = 0
        self.load_self_preset_pressed = False
        
        self.sync_out_module = SyncOut(15)
        
        self.OLED = None
        
        self.menu_navigation_map = get_menu_navigation_map()
        
        self.display_screen = DisplayScreen.CV_GATE_SCREEN # TODO start in menu
        self.current_menu_len = len(self.menu_navigation_map)
        self.current_menu_selected = 0
        self.current_menu_value = 0
        self.menu_path = []
        
        self.menu_navigation_map["cv-gate-mod"]["module a"]["data_pointer"] = self.gate_cv_mode_modules[0]
        self.menu_navigation_map["cv-gate-mod"]["module b"]["data_pointer"] = self.gate_cv_mode_modules[1]
        self.menu_navigation_map["cv-gate-mod"]["module c"]["data_pointer"] = self.gate_cv_mode_modules[2]
        self.menu_navigation_map["cv-gate-mod"]["module d"]["data_pointer"] = self.gate_cv_mode_modules[3]
        
        self.menu_navigation_map["sync out"]["data_pointer"] = self.sync_out_module
        
        global expected_devices, devices
        self.expected_devices = expected_devices
        self.devices = devices
        self.missing_devices = list(set(self.expected_devices)-set(self.devices))
        
        self.load_data()
        
        
    def load_data(self):
        print("Start loading data")
        config_file = None
        try:
            config_file = open(JSON_CONFIG_FILE_NAME, "r")
            dict_data = json.load(config_file)
            gate_cv_mode_module_list = dict_data["gate_cv_mode_modules"]
            i = 0
            for dict_gate_cv_mode_module in gate_cv_mode_module_list:
                self.gate_cv_mode_modules[i].gate_level = dict_gate_cv_mode_module["gate_level"]
                self.gate_cv_mode_modules[i].cv_max = dict_gate_cv_mode_module["cv_max "]
                self.gate_cv_mode_modules[i].midi_channel = dict_gate_cv_mode_module["midi_channel"]
                self.gate_cv_mode_modules[i].mod_output = dict_gate_cv_mode_module["mod_output"]
                i = i+1
                
            sync_out_dict= dict_data["sync_out"]
            self.sync_out_module.time_division = sync_out_dict["time_division"]
            self.sync_out_module.time_division = sync_out_dict["clock_polarity"]
            
            mot_pot_presets = dict_data["mot_pot_presets"]

            mot_index = 0
            for mot_pot_preset in mot_pot_presets:
                value_index = 0
                for value in mot_pot_preset:
                    self.motPotPresets[mot_index].set_value(value_index, value)
                    value_index = value_index + 1
                mot_index = mot_index + 1            
            print("Data Loaded!")
        except OSError:
            print("Couldn't load config because of OS ERROR")
        except Exception as e:
            print("Couldn't load config because unknown error")
            print(e)

        if config_file != None:
            config_file.close()
            
            
    def save_data(self):
        dict_data = {}
        gate_cv_mode_module_list = []
        i = 0
        for gate_cv_mode_module in self.gate_cv_mode_modules:            
            dict_gate_cv_mode_module = {}
            dict_gate_cv_mode_module["gate_level"] = gate_cv_mode_module.gate_level
            dict_gate_cv_mode_module["cv_max "] = gate_cv_mode_module.cv_max
            dict_gate_cv_mode_module["midi_channel"] = gate_cv_mode_module.midi_channel
            dict_gate_cv_mode_module["mod_output"] = gate_cv_mode_module.mod_output
            gate_cv_mode_module_list.append(dict_gate_cv_mode_module)
            i = i+1
        dict_data["gate_cv_mode_modules"] = gate_cv_mode_module_list
        
        
        mot_pot_presets = []
        
        for motPotPreset in self.motPotPresets:
            value_list = []
            for value in motPotPreset.values:
                value_list.append(value)
            mot_pot_presets.append(value_list)
        dict_data["mot_pot_presets"] = mot_pot_presets
        
        sync_out_dict = {}
        sync_out_dict["time_division"] = self.sync_out_module.time_division
        sync_out_dict["clock_polarity"] = self.sync_out_module.time_division
        
        dict_data["sync_out"] = sync_out_dict
        
        
        with open(JSON_CONFIG_FILE_NAME, "w") as config_file:
            json.dump(dict_data, config_file)
        
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
        
    def update_motors(self):
        to_return = False
        for mot_Pot_module in self.mot_pot_modules:
            mot_status = mot_Pot_module.update_motor()
            if mot_status:
                to_return = True
        return to_return
    
    def load_preset(self):
        for i in range(0,3):
            self.mot_pot_modules[i].launch_to_setpoint(self.motPotPresets[self.current_selected_motPot_preset].values[i])
            
    def save_preset(self):        
        self.poll_adc_values()
        for i in range(0,3):
            self.motPotPresets[self.current_selected_motPot_preset].set_value(i, self.mot_pot_modules[i].get_last_adc_value())
        self.save_data()

    
    def setDisplay(self, OLED):
        self.OLED = OLED
        
    def get_midi_channels_for_modules(self):
        to_return = []
        for gate_cv_mode_module in self.gate_cv_mode_modules:
            to_return.append(gate_cv_mode_module.midi_channel)
        return to_return

    def note_on(self, note, midi_channel, vel):
        midi_channels_for_modules = self.get_midi_channels_for_modules()
        if midi_channel in midi_channels_for_modules or 0 in midi_channels_for_modules:
            for gate_cv_mode_module in self.gate_cv_mode_modules:
                if gate_cv_mode_module.midi_channel == 0 or gate_cv_mode_module.midi_channel == midi_channel:
                    gate_cv_mode_module.write_gate(1)
                    gate_cv_mode_module.write_cv(note)
                    if gate_cv_mode_module.mod_output == 1:
                        gate_cv_mode_module.write_vel(vel)
        
    def note_off(self, note, midi_channel):
        midi_channels_for_modules = self.get_midi_channels_for_modules()
        if midi_channel in midi_channels_for_modules or 0 in midi_channels_for_modules:
            for gate_cv_mode_module in self.gate_cv_mode_modules:
                if gate_cv_mode_module.midi_channel == 0 or gate_cv_mode_module.midi_channel == midi_channel:
                    gate_cv_mode_module.write_gate(0)
 
    def midi_start(self):
        self.sync_out_module.sync_reset()
        
    def midi_stop(self):
        self.sync_out_module.sync_reset()
        
    def midi_clock(self):        
        self.sync_out_module.clock()
        
    def mode_update(self, mode, midi_channel):        
        midi_channels_for_modules = self.get_midi_channels_for_modules()
        if midi_channel in midi_channels_for_modules or 0 in midi_channels_for_modules:
            for gate_cv_mode_module in self.gate_cv_mode_modules:
                if (gate_cv_mode_module.midi_channel == 0 or gate_cv_mode_module.midi_channel == midi_channel) and gate_cv_mode_module.mod_output == 0:
                    gate_cv_mode_module.write_mode(mode)

    """
    self.menu_navigation_map = get_menu_navigation_map()

    self.display_screen = True # TODO start in menu
    self.current_menu_len = len(self.menu_navigation_map)
    self.current_menu_selected = 0
    self.menu_path = []
    """

    def up_pressed(self):
        if self.display_screen == DisplayScreen.CONFIG_SCREEN:                
            if self.current_menu_selected > 0:
                self.current_menu_selected = self.current_menu_selected - 1
                self.OLED.set_need_display()
        elif  self.display_screen == DisplayScreen.MOT_POT_SCREEN:
            if self.load_self_preset_pressed == True:
                self.save_preset()
                self.load_self_preset_pressed = False
                self.OLED.set_need_display()      
            else:
                self.current_selected_motPot_preset = self.current_selected_motPot_preset-1
                if self.current_selected_motPot_preset < 0:
                    self.current_selected_motPot_preset = 0

                self.OLED.set_need_display()        
        
            
    def down_pressed(self):
        if self.display_screen == DisplayScreen.CONFIG_SCREEN:
            if self.current_menu_selected < self.current_menu_len-1:
                self.current_menu_selected = self.current_menu_selected + 1
                self.OLED.set_need_display()
        elif  self.display_screen == DisplayScreen.MOT_POT_SCREEN:
            if self.load_self_preset_pressed == True:
                self.load_preset()
                self.load_self_preset_pressed = False
                self.OLED.set_need_display()      
            else:
                self.current_selected_motPot_preset = self.current_selected_motPot_preset+1
                if self.current_selected_motPot_preset > 15:
                    self.current_selected_motPot_preset = 15
                    
                self.OLED.set_need_display()
                
    def back_pressed(self):
        if self.display_screen == DisplayScreen.CONFIG_SCREEN:
            if len(self.menu_path) > 0:
                self.menu_path = self.menu_path[:-1]
                self.current_menu_selected = 0
                current_keys, _ = self.get_current_menu_keys()
                self.current_menu_len = len(current_keys)
            else:
                self.display_screen = DisplayScreen.CV_GATE_SCREEN
            self.OLED.set_need_display()
        elif self.display_screen == DisplayScreen.CV_GATE_SCREEN:
            self.display_screen = DisplayScreen.MOT_POT_SCREEN
            self.OLED.set_need_display()
        elif self.display_screen == DisplayScreen.MOT_POT_SCREEN:
            self.display_screen = DisplayScreen.CV_GATE_SCREEN
            self.OLED.set_need_display()
    def enter_pressed(self):
        if self.display_screen == DisplayScreen.CONFIG_SCREEN:
            current_keys, in_last_sub_menu  = self.get_current_menu_keys()
            if in_last_sub_menu:
                # need to change value
                tmp_menu_selected = self.menu_navigation_map
                for key_path in self.menu_path:
                    tmp_menu_selected = tmp_menu_selected[key_path]
                attribute_name = tmp_menu_selected["attribute_name"]
                attribute_value = setattr(self.get_current_data_pointer(), attribute_name,self.current_menu_selected)
                self.current_menu_value = self.current_menu_selected
                self.save_data()
                self.OLED.set_need_display()
            else:
                self.menu_path.append(current_keys[self.current_menu_selected])
                self.current_menu_selected = 0            
                current_keys, in_last_sub_menu  = self.get_current_menu_keys()   
                self.current_menu_len = len(current_keys)
                if in_last_sub_menu:
                    tmp_menu_selected = self.menu_navigation_map
                    for key_path in self.menu_path:
                        tmp_menu_selected = tmp_menu_selected[key_path]     
                    attribute_name = tmp_menu_selected["attribute_name"]
                    attribute_value = getattr(self.get_current_data_pointer(), attribute_name)
                    self.current_menu_selected = attribute_value
                    self.current_menu_value = attribute_value
                self.OLED.set_need_display()
        elif  self.display_screen == DisplayScreen.MOT_POT_SCREEN:
            self.load_self_preset_pressed = not  self.load_self_preset_pressed            
            self.OLED.set_need_display()
        elif self.display_screen == DisplayScreen.CV_GATE_SCREEN:
            self.display_screen = DisplayScreen.CONFIG_SCREEN   
            self.OLED.set_need_display()
    def get_current_data_pointer(self):
        tmp_menu_selected = self.menu_navigation_map
        i = 0
        for key_path in self.menu_path:
            tmp_menu_selected = tmp_menu_selected[key_path]
            if "data_pointer" in tmp_menu_selected.keys():
                return tmp_menu_selected["data_pointer"]
        return None
    
    def get_current_menu_keys(self):
        in_last_sub_menu = False
        if len(self.menu_path) == 0:
            current_keys = list(self.menu_navigation_map.keys())
        else:
            tmp_menu_selected = self.menu_navigation_map
            for key_path in self.menu_path:
                tmp_menu_selected = tmp_menu_selected[key_path]
                
            current_keys = list(tmp_menu_selected.keys())
        if "values" in current_keys:
            tmp_menu_selected = self.menu_navigation_map
            for key_path in self.menu_path:
                tmp_menu_selected = tmp_menu_selected[key_path]
            current_keys = tmp_menu_selected["values"]
            in_last_sub_menu  = True
        if "data_pointer" in current_keys:
            current_keys.remove("data_pointer")
        return current_keys, in_last_sub_menu
        

