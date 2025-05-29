import cv2
# 线程功能操作库 Thread function operation library
import threading
import inspect
import ctypes
import HSV_Config
import spidev as SPI
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image
from xgolib import XGO
from key import Button

g_car = XGO(port='/dev/ttyAMA0',version="xgolite")

#屏幕清除
mydisplay = LCD_2inch.LCD_2inch()
mydisplay.clear()
splash = Image.new("RGB", (mydisplay.height, mydisplay.width ),"black")
mydisplay.ShowImage(splash)
button = Button()

def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        
def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


image = cv2.VideoCapture(0)  #打开摄像头/dev/video0 Open the camera /dev/video0
image.set(3, 320)
image.set(4, 240)
image.set(5, 30) 
update_hsv = HSV_Config.update_hsv()


# 颜色到灯珠颜色编号的映射
color_to_number = {
        'red': 0,
        'green': 1,
        'blue': 2,
        'yellow': 3
    }
def light_2leds(color1,color2):
    # 获取颜色对应的灯珠颜色编号
    color1_number = color_to_number.get(color1, None)
    color2_number = color_to_number.get(color2, None)

    color1_list = [0,0,0]
    color2_list = [0,0,0]

    if color1_number == 0:
        color1_list = [255,0,0]
    elif color1_number == 1:
        color1_list = [0,255,0]
    elif color1_number == 2:
        color1_list = [0,0,255]
    elif color1_number == 3:
        color1_list = [255,255,0]

    if color2_number == 0:
        color2_list = [255,0,0]
    elif color2_number == 1:
        color2_list = [0,255,0]
    elif color2_number == 2:
        color2_list = [0,0,255]
    elif color2_number == 3:
        color2_list = [255,255,0]

    # 分配灯珠
    # 前 5 个灯珠
    g_car.rider_led(1, color1_list)
    g_car.rider_led(2, color1_list)

    # 后 5 个灯珠
    g_car.rider_led(3, color2_list)
    g_car.rider_led(4, color2_list)


def light_3leds(color1,color2,color3):
    # 获取颜色对应的灯珠颜色编号
    color1_number = color_to_number.get(color1, None)
    color2_number = color_to_number.get(color2, None)
    color3_number = color_to_number.get(color3, None)

    color1_list = [0,0,0]
    color2_list = [0,0,0]
    color3_list = [0,0,0]

    if color1_number == 0:
        color1_list = [255,0,0]
    elif color1_number == 1:
        color1_list = [0,255,0]
    elif color1_number == 2:
        color1_list = [0,0,255]
    elif color1_number == 3:
        color1_list = [255,255,0]

    if color2_number == 0:
        color2_list = [255,0,0]
    elif color2_number == 1:
        color2_list = [0,255,0]
    elif color2_number == 2:
        color2_list = [0,0,255]
    elif color2_number == 3:
        color2_list = [255,255,0]

    if color3_number == 0:
        color3_list = [255,0,0]
    elif color3_number == 1:
        color3_list = [0,255,0]
    elif color3_number == 2:
        color3_list = [0,0,255]
    elif color3_number == 3:
        color3_list = [255,255,0]

    g_car.rider_led(1, color1_list)

    g_car.rider_led(2, color2_list)
    g_car.rider_led(3, color2_list)

    g_car.rider_led(4, color3_list)

    

def light_4leds(color1,color2,color3,color4):
    # 获取颜色对应的灯珠颜色编号
    color1_number = color_to_number.get(color1, None)
    color2_number = color_to_number.get(color2, None)
    color3_number = color_to_number.get(color3, None)
    color4_number = color_to_number.get(color4, None)
    
    color1_list = [0,0,0]
    color2_list = [0,0,0]
    color3_list = [0,0,0]
    color4_list = [0,0,0]

    if color1_number == 0:
        color1_list = [255,0,0]
    elif color1_number == 1:
        color1_list = [0,255,0]
    elif color1_number == 2:
        color1_list = [0,0,255]
    elif color1_number == 3:
        color1_list = [255,255,0]

    if color2_number == 0:
        color2_list = [255,0,0]
    elif color2_number == 1:
        color2_list = [0,255,0]
    elif color2_number == 2:
        color2_list = [0,0,255]
    elif color2_number == 3:
        color2_list = [255,255,0]

    if color3_number == 0:
        color3_list = [255,0,0]
    elif color3_number == 1:
        color3_list = [0,255,0]
    elif color3_number == 2:
        color3_list = [0,0,255]
    elif color3_number == 3:
        color3_list = [255,255,0]

    if color4_number == 0:
        color4_list = [255,0,0]
    elif color4_number == 1:
        color4_list = [0,255,0]
    elif color4_number == 2:
        color4_list = [0,0,255]
    elif color4_number == 3:
        color4_list = [255,255,0]

    g_car.rider_led(1, color1_list)

    g_car.rider_led(2, color2_list)
    g_car.rider_led(3, color3_list)

    g_car.rider_led(4, color4_list)
    
def light_leds(unique_colors):
    color_all_list = [0,0,0]
    if(len(unique_colors)==0):
        g_car.rider_led(1, color_all_list)
        g_car.rider_led(2, color_all_list)
        g_car.rider_led(3, color_all_list)
        g_car.rider_led(4, color_all_list)
    elif(len(unique_colors)==1): ################################改
        if color_to_number.get(*unique_colors, None) == 0:
            color_all_list = [255,0,0]
        elif color_to_number.get(*unique_colors, None) == 1:
            color_all_list = [0,255,0]
        elif color_to_number.get(*unique_colors, None) == 2:
            color_all_list = [0,0,255]
        elif color_to_number.get(*unique_colors, None) == 3:
            color_all_list = [255,255,0]

        g_car.rider_led(1, color_all_list)
        g_car.rider_led(2, color_all_list)
        g_car.rider_led(3, color_all_list)
        g_car.rider_led(4, color_all_list)

    elif(len(unique_colors)==2): 
        light_2leds(*unique_colors)
    elif(len(unique_colors)==3):   
        light_3leds(*unique_colors)
    elif(len(unique_colors)==4):   
        light_4leds(*unique_colors)


color_hsv  = {"red"   : ((0, 70, 72), (7, 255, 255)),
              "green" : ((54, 109, 78), (77, 255, 255)),
              "blue"  : ((92, 100, 62), (121, 251, 255)),
              "yellow": ((26, 100, 91), (32, 255, 255))}

def TEST():
    unique_colorstemp=None
    global color_hsv
    while True:
        ret, frame = image.read() #usb摄像头 usb camera
        frame, binary,hsvname=update_hsv.get_contours(frame,color_hsv)
        unique_colors = list(dict.fromkeys(hsvname))
        # 根据列表的长度来决定如何分割字符串
        num_colors = len(unique_colors)
        # 如果列表中有4个元素
        if num_colors == 4:
            first_line = ', '.join(unique_colors[:2])
            second_line = ', '.join(unique_colors[2:])
        elif num_colors == 3:
            first_line = ', '.join(unique_colors[:2])
            second_line = unique_colors[2]
        elif num_colors == 2:
            first_line = ', '.join(unique_colors)
            second_line = ""
        elif num_colors == 1:
            first_line = unique_colors[0]
            second_line = ""
        else:
            first_line = ""
            second_line = ""
        if(unique_colors!=unique_colorstemp):
            light_leds(unique_colors)
            unique_colorstemp=unique_colors.copy()
        
        #显示在小车的lcd屏幕上
        b,g,r = cv2.split(frame)
        img = cv2.merge((r,g,b))
        imgok = Image.fromarray(img)
        mydisplay.ShowImage(imgok)
        if button.press_b():
            g_car.reset()
            g_car.rider_led(1, [0,0,0])
            g_car.rider_led(2, [0,0,0])
            g_car.rider_led(3, [0,0,0])
            g_car.rider_led(4, [0,0,0])
            # stop_thread(thread1)
            break


try:
    TEST()
        

except:
    # stop_thread(thread1)
    g_car.reset()
    image.release()






