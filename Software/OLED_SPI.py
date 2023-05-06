from machine import Pin,SPI
import framebuf
import time
import font.arial6 as arial6
import font.arial8 as arial8
import font.arial10 as arial10
import font.font10 as font10
import font.font6 as font6
import writer
from multiToolMidiConfig import *
import multiToolMidiConfig 
from random import randrange

import _thread

DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

def pict_to_fbuff(path,x,y):
    with open(path, 'rb') as f:
        f.readline() # Magic number
        f.readline() # Creator comment
        f.readline() # Dimensions
        data = bytearray(f.read())
    return framebuf.FrameBuffer(data, x, y, framebuf.MONO_HLSB)


class OLED_2inch23(framebuf.FrameBuffer):
    def __init__(self, multiToolMidiConfig):        
        self.multiToolMidiConfig = multiToolMidiConfig
        
        self.show_lock = _thread.allocate_lock()
        
        self.need_display = False
        
        self.width = 128
        self.height = 32
        
        self.screensaver_active = False
        self.screesaver_pixels = [[0]*2]*20
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,4000_000)
        self.spi = SPI(1,4000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()
        
        self.white =   0xffff
        self.black =   0x0000

        self.font_writer_arial6 = writer.Writer(self, arial6)
        self.font_writer_arial8 = writer.Writer(self, arial8)
        self.font_writer_arial10 = writer.Writer(self, arial10)
        self.font_writer_font10 = writer.Writer(self, font10)
        self.font_writer_font6 = writer.Writer(self, font6)
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)
        
    def display_helixbyte(self):
        with open('pictures/lxb32x32.pbm', 'rb') as f:
            f.readline() # Magic number
            f.readline() # Creator comment
            f.readline() # Dimensions
            data = bytearray(f.read())
        lxb_fbuf = framebuf.FrameBuffer(data, 32, 32, framebuf.MONO_HLSB)

        self.blit(lxb_fbuf, 48, 0)
        self.show()
        
    def display_programming_mode(self):     
        self.fill(self.black)#smallest
        self.font_writer_arial10.text("Programming mode",0,0)
        self.show()
        time.sleep(1)

    def init_display(self):
        """Initialize dispaly"""  
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)#turn off OLED display*/
    
        self.write_cmd(0x04)#turn off OLED display*/

        self.write_cmd(0x10)#turn off OLED display*/	
    
        self.write_cmd(0x40)#set lower column address*/ 
        self.write_cmd(0x81)#set higher column address*/ 
        self.write_cmd(0x80)#--set start line address  Set Mapping RAM Display Start Line (0x00~0x3F, SSD1305_CMD)
        self.write_cmd(0xA1)#--set contrast control register
        self.write_cmd(0xA6)# Set SEG Output Current Brightness 
        self.write_cmd(0xA8)#--Set SEG/Column Mapping	
        self.write_cmd(0x1F)#Set COM/Row Scan Direction   
        self.write_cmd(0xC8)#--set normal display  
        self.write_cmd(0xD3)#--set multiplex ratio(1 to 64)
        self.write_cmd(0x00)#--1/64 duty
        self.write_cmd(0xD5)#-set display offset	Shift Mapping RAM Counter (0x00~0x3F) 
        self.write_cmd(0xF0)#-not offset
        self.write_cmd(0xD8) #--set display clock divide ratio/oscillator frequency
        self.write_cmd(0x05)#--set divide ratio, Set Clock as 100 Frames/Sec
        self.write_cmd(0xD9)#--set pre-charge period
        self.write_cmd(0xC2)#Set Pre-Charge as 15 Clocks & Discharge as 1 Clock
        self.write_cmd(0xDA) #--set com pins hardware configuration 
        self.write_cmd(0x12)   
        self.write_cmd(0xDB) #set vcomh
        self.write_cmd(0x08)#Set VCOM Deselect Level
        self.write_cmd(0xAF); #-Set Page Addressing Mode (0x00/0x01/0x02)
        
    def set_need_display(self):
        self.need_display= True
        
    def display(self):        
        self.fill(0x0000)
        if  self.multiToolMidiConfig.display_menu == False:
            channel_letters = ["A", "B", "C", "D"]
            for i in range(0,4):
                midi_channel = self.multiToolMidiConfig.gate_cv_mode_modules[i].midi_channel
                if midi_channel == 0:
                    midi_channel_str = "all"
                else:
                    midi_channel_str = str(midi_channel)
                    
                if self.multiToolMidiConfig.gate_cv_mode_modules[i].cv_max == 0:
                    cv_max = "0..10 v"
                else:
                    cv_max = "0..5 v"
                if i%2==1:
                    self.rect(1+i*32,0,6,1,self.black)
                    self.font_writer_arial8.text(str(channel_letters[i]),1+i*32,1)
                    self.font_writer_arial8.text("ch:",3+i*32,7)
                    self.font_writer_arial10.text(midi_channel_str,15+i*32,5)
                    if self.multiToolMidiConfig.gate_cv_mode_modules[i].gate_level == 0:
                        self.line(2+i*32,19,4+i*32,19, self.white)
                        self.line(4+i*32,19,4+i*32,14, self.white)
                        self.line(4+i*32,14,6+i*32,14, self.white)
                    else:                        
                        self.line(2+i*32,14,4+i*32,14, self.white)
                        self.line(4+i*32,19,4+i*32,14, self.white)
                        self.line(4+i*32,19,6+i*32,19, self.white)
                    self.font_writer_arial8.text(cv_max,9+i*32, 14)
                    self.rect(0+i*32,0,32,22,self.white)
                else:
                    self.fill_rect(0+i*32,0,32,22,self.white)
                    self.font_writer_arial8.text(str(channel_letters[i]),1+i*32,1,True)
                    self.font_writer_arial8.text("ch:",3+i*32,7, True)
                    self.font_writer_arial10.text(midi_channel_str,15+i*32,5,True)
                    if self.multiToolMidiConfig.gate_cv_mode_modules[i].gate_level == 0:
                        self.line(2+i*32,19,4+i*32,19, self.black)
                        self.line(4+i*32,19,4+i*32,14, self.black)
                        self.line(4+i*32,14,6+i*32,14, self.black)
                    else:                        
                        self.line(2+i*32,14,4+i*32,14, self.black)
                        self.line(4+i*32,19,4+i*32,14, self.black)
                        self.line(4+i*32,19,6+i*32,19, self.black)
                    self.font_writer_arial8.text(cv_max,9+i*32, 14, True)
            pot_design_x = 96
            pot_design_y = 22
            pot_design_width = 32
            pot_design_height = 4
            for i in range(0,3):
                self.rect(pot_design_x,pot_design_y+(pot_design_height-1)*i,pot_design_width,pot_design_height,self.white)                
                self.fill_rect(pot_design_x,pot_design_y+(pot_design_height-1)*i,int(pot_design_width*self.multiToolMidiConfig.mot_pot_percent_value[i]/100),pot_design_height,self.white)
            self.font_writer_arial8.text("tdi v: "+multiToolMidiConfig.timeDivToStr(self.multiToolMidiConfig.sync_out_module.time_division),57, 23)
            self.rect(47,21,50,11,self.white)
            
            if self.multiToolMidiConfig.sync_out_module.clock_polarity == 0:
                self.line(49,28,49,23, self.white)
                self.line(49,23,51,23, self.white)
                self.line(51,23,51,28, self.white)
                self.line(51,28,55,28, self.white)
            elif self.multiToolMidiConfig.sync_out_module.clock_polarity == 1:
                self.line(49,23,49,28, self.white)
                self.line(49,28,51,28, self.white)
                self.line(51,23,51,28, self.white)
                self.line(51,23,55,23, self.white)
            elif self.multiToolMidiConfig.sync_out_module.clock_polarity == 2:
                self.line(49,28,49,23, self.white)
                self.line(49,23,52,23, self.white)
                self.line(52,23,52,28, self.white)
                self.line(52,28,55,28, self.white)
                self.line(55,28,55,23, self.white)
        else:
            
            path = "/"
            for sub_path in self.multiToolMidiConfig.menu_path:
                path = path + sub_path + "/"
            self.fill_rect(0,0,128,8,self.white)
            self.font_writer_arial8.text(path,1,1,True)
            
            current_keys, in_last_sub_menu = self.multiToolMidiConfig.get_current_menu_keys()
                
            if self.multiToolMidiConfig.current_menu_selected >= self.multiToolMidiConfig.current_menu_len-2 and self.multiToolMidiConfig.current_menu_len>1:
                range_low = self.multiToolMidiConfig.current_menu_len-2
            else:
                range_low = self.multiToolMidiConfig.current_menu_selected
            
            range_high = range_low + 2
            if range_high > (self.multiToolMidiConfig.current_menu_len):
               range_high = (self.multiToolMidiConfig.current_menu_len)
            general_index = 0
            
            for i in range(range_low,range_high):
                    
                if i == self.multiToolMidiConfig.current_menu_selected:
                    self.fill_rect(0,9+10*general_index,128,10,self.white)
                    to_add = ""
                    if in_last_sub_menu and self.multiToolMidiConfig.current_menu_value == i:
                        to_add = "> "
                    self.font_writer_arial10.text(to_add+current_keys[i],1,9+10*general_index, True)  
                else:
                    to_add = ""
                    if in_last_sub_menu and self.multiToolMidiConfig.current_menu_value == i:
                        to_add = "> "
                    self.font_writer_arial10.text(to_add+current_keys[i],1,9+10*general_index)
                    
                print(current_keys[i])
                general_index = general_index+1
            
            #delimitation line between menu and top path
            self.line(0,8,128,8,self.black)
            
            #side scrollbar
            self.fill_rect(124,9, 4, 23, self.black)
            self.rect(125,9, 3, 23, self.white)
            
            max_scrollbar_size_float = 22 / self.multiToolMidiConfig.current_menu_len
            max_scrollbar_size = int(max_scrollbar_size_float)
            if max_scrollbar_size == 0:
                max_scrollbar_size = 1
                        
            self.rect(126,9+int(max_scrollbar_size_float*self.multiToolMidiConfig.current_menu_selected ), 1, max_scrollbar_size, self.white)
            
            """
            self.multiToolMidiConfig.menu_navigation_map = get_menu_navigation_map()

            self.multiToolMidiConfig.display_menu = True # TODO start in menu
            self.multiToolMidiConfig.current_menu_len = len(self.menu_navigation_map)
            self.multiToolMidiConfig.current_menu_selected = 0
            self.multiToolMidiConfig.menu_path = []
            """
                
        self.show()
        self.need_display = False
        
        
    def show(self):
        self.show_lock.acquire()
        for page in range(0,4):
            self.write_cmd(0xb0 + page)
            self.write_cmd(0x04)
            self.write_cmd(0x10)
            self.dc(1)
            for num in range(0,128):
                self.write_data(self.buffer[page*128+num])
        self.show_lock.release()        
    def is_screensaver(self):
        return self.screensaver_active
    
    def is_screensaver(self):
        return self.screensaver_active
        
    def set_screensaver_mode(self):
        self.screensaver_active = True
        for i in range(0,len(self.screesaver_pixels)):
            self.screesaver_pixels[i] = [randrange(0,128), randrange(0,32)]
        self.fill(self.black)  
        
        for pix in self.screesaver_pixels:
            self.rect(pix[0],pix[1],1,1,self.white)
            
        self.show()
        
    def update_screensaver(self):        
        for i in range(0,len(self.screesaver_pixels)):
            self.screesaver_pixels[i][1] += 1
            if self.screesaver_pixels[i][1] > 31:                
                self.screesaver_pixels[i] = [randrange(0,128), 0]
        self.fill(self.black)        
        
        for pix in self.screesaver_pixels:
            self.rect(pix[0],pix[1],1,1,self.white)
            
        self.show()
        
    def reset_screensaver_mode(self): 
        self.screensaver_active = False
        self.display()
        
def debug():

    OLED = OLED_2inch23()
    OLED.fill(0x0000) 
    OLED.show()
    OLED.display_helixbyte()
    time.sleep(0.5)
    OLED.rect(0,0,128,32,OLED.white)
    OLED.rect(10,6,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.fill_rect(40,6,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.rect(70,6,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    OLED.fill_rect(100,6,20,20,OLED.white)
    time.sleep(0.5)
    OLED.show()
    time.sleep(1)
    
    OLED.fill(0x0000)
    OLED.line(0,0,5,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,20,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,35,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,65,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,95,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,21,OLED.white)
    OLED.show()
    time.sleep(0.1)
    OLED.line(0,0,125,11,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(0,0,125,3,OLED.white)
    OLED.show()
    time.sleep(0.01)
    
    OLED.line(127,1,125,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,110,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,95,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,65,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,35,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,31,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,21,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,11,OLED.white)
    OLED.show()
    time.sleep(0.01)
    OLED.line(127,1,1,1,OLED.white)
    OLED.show()
    time.sleep(1)
    
    OLED.fill(0x0000) 
    OLED.text("128 x 32 Pixels",1,2,OLED.white)
    OLED.text("Pico-OLED-2.23",1,12,OLED.white)
    OLED.text("SSD1503",1,22,OLED.white)  
    OLED.show()
    
    time.sleep(1)
    OLED.fill(0xFFFF)



