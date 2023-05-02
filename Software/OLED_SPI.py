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
        
    def display(self):        
        self.fill(0x0000)
        if  self.multiToolMidiConfig.display_menu == False:
            channel_letters = ["A", "B", "C", "D"]
            for i in range(0,4):
                if i%2==0:
                    self.rect(0+i*32,0,32,16,self.white)
                    self.font_writer_arial8.text(str(channel_letters[i]),2+i*32,2)
                    self.font_writer_arial10.text("Ch:"+str(self.multiToolMidiConfig.midi_channels_for_modules[i]),8+i*32,5)
                else:
                    self.fill_rect(0+i*32,0,32,16,self.white)
                    self.font_writer_arial8.text(str(channel_letters[i]),2+i*32,2,True)
                    self.font_writer_arial10.text("Ch:"+str(self.multiToolMidiConfig.midi_channels_for_modules[i]),8+i*32,5,True)
        self.show()

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



