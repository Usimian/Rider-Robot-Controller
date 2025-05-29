#导入xgoedu
import os, time, sys
import xgolib
import xgoscreen.LCD_2inch as LCD_2inch
from key import Button
from PIL import Image, ImageDraw, ImageFont
import sys

sys.path.append("..")


button=Button()

display = LCD_2inch.LCD_2inch()
display.Init()
display.clear()
splash = Image.new("RGB", (320, 240), "black")
draw = ImageDraw.Draw(splash)
display.ShowImage(splash)

font1 = ImageFont.truetype("/home/pi/model/msyh.ttc", 16)
font2 = ImageFont.truetype("/home/pi/model/msyh.ttc", 20)

def lcd_text(x, y, content):
    draw.text((x, y), content, fill="RED", font=font2)
    display.ShowImage(splash)

lcd_text(50,80,'SDCard NO.58')
lcd_text(50,120,'Yahboom system')
lcd_text(50,150,'V1.0.0')


while True:
    time.sleep(0.01)
    if button.press_a():
        break
    elif button.press_b():
        os._exit(0)



