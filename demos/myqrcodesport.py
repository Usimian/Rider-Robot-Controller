import cv2
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image,ImageDraw,ImageFont
from key import Button
import numpy as np
import time
from xgolib import XGO 

g_car = XGO("xgorider")

display = LCD_2inch.LCD_2inch()
display.clear()
splash = Image.new("RGB", (display.height, display.width ),"black")
display.ShowImage(splash)
button=Button()
#-----------------------COMMON INIT-----------------------
import pyzbar.pyzbar as pyzbar

def cv2AddChineseText(img, text, position, textColor=(0, 255, 0), textSize=30):
    if (isinstance(img, np.ndarray)):  
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    fontStyle = ImageFont.truetype(
        "/home/pi/model/msyh.ttc", textSize, encoding="utf-8")
    draw.text(position, text, textColor, font=fontStyle)
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

 
font = cv2.FONT_HERSHEY_SIMPLEX 
cap=cv2.VideoCapture(0)
cap.set(3,320)
cap.set(4,240)
if(not cap.isOpened()):
    print("[camera.py:cam]:can't open this camera")

while(True):
    barcodeData = ""
    ret, img = cap.read() 
    img_ROI_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    barcodes = pyzbar.decode(img_ROI_gray) 
    for barcode in barcodes:
        barcodeData = barcode.data.decode("utf-8")
        barcodeType = barcode.type
        text = "{} ({})".format(barcodeData, barcodeType)
        img=cv2AddChineseText(img,text, (10, 30),(0, 255, 0), 30)
        print("[INFO] Found {} barcode: {}".format(barcodeType, barcodeData))

    
    b,g,r = cv2.split(img)
    img = cv2.merge((r,g,b))
    imgok = Image.fromarray(img)
    display.ShowImage(imgok)

    # r,g,b = cv2.split(img)
    # img1 = cv2.merge((b,g,r))
    # cv2.imshow("image1",img1)


    if(barcodeData == "goahead"):
        g_car.rider_move_x(0.5,0.2) #前进0.2s
    elif(barcodeData == "goback"):
        g_car.rider_move_x(-0.5,0.2) #后退0.2s

    elif(barcodeData == "turnright"):
        g_car.rider_turn(-200,0.2) #右转0.2s
    elif(barcodeData == "turnleft"):
        g_car.rider_turn(200,0.2) #左转0.2s

    elif(barcodeData == "updown"):
        g_car.rider_periodic_z(2) 
        time.sleep(2.5)#蹲起2.5s
        g_car.rider_periodic_z(0) 

    elif(barcodeData == "shake"):
        g_car.rider_periodic_roll(2) #左右晃动2.5s
        time.sleep(2.5)
        g_car.rider_periodic_roll(0)


    if (cv2.waitKey(1)) == ord('q'):
        break
    if button.press_b():
        break

cap.release()
