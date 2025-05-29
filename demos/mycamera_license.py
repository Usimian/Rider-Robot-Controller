# import opencv
import cv2
# import hyperlpr3
import hyperlpr3 as lpr3
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image,ImageDraw,ImageFont
import time
import numpy as np
import mediapipe as mp
from xgolib import XGO
from key import Button

# Instantiate object
# 中文字体加载 Chinese font loading
font_ch = ImageFont.truetype("/home/pi/model/platech.ttf", 20, 0)
# 实例化识别对象 Instantiate the recognition object
catcher = lpr3.LicensePlateCatcher()#DETECT_LEVEL_HIGH640*640

#清屏
mydisplay = LCD_2inch.LCD_2inch()
mydisplay.clear()
splash = Image.new("RGB", (mydisplay.height, mydisplay.width ),"black")
mydisplay.ShowImage(splash)

button = Button()
g_car = XGO(port='/dev/ttyAMA0',version="xgolite")
fm=g_car.read_firmware()
if fm[0]=='M':
    print('XGO-MINI')
    g_car = XGO(port='/dev/ttyAMA0',version="xgomini")
    dog_type='M'
elif fm[0]=='L':
    print('XGO-LITE')
    dog_type='L'
elif fm[0]=='R':
    print('XGO-RIDER')
    g_car = XGO(port='/dev/ttyAMA0',version="xgorider")
    dog_type='R'


# 在图像上绘制车牌框及文字 Draw the license plate frame and text on the image
def draw_plate_on_image(img, box, text, font):
    x1, y1, x2, y2 = box
    cv2.rectangle(img, (x1, y1), (x2, y2), (225, 32, 39), 2, cv2.LINE_AA)
    cv2.rectangle(img, (x1, y1 - 20), (x2, y1), (225, 32, 39), -1)
    data = Image.fromarray(img)
    draw = ImageDraw.Draw(data)
    draw.text((x1 + 1, y1 - 18), text, (255, 255, 255), font=font)
    res = np.asarray(data)
    return res

try:
    camera = cv2.VideoCapture(0)     # 定义摄像头对象，参数0表示第一个摄像头，默认640x480
    camera.set(3, 320)
    camera.set(4, 240)
    pTime, cTime = 0, 0

    while True:
        ret, frame = camera.read()
        # 执行识别算法
        results = catcher(frame)

        # 计算帧率
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        text = "FPS : " + str(int(fps))
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        # 初始化图像变量 Initialize image variables
        image = frame.copy()  # 使用原始帧作为默认图像 Use original frame as default image
        for code, confidence, type_idx, box in results:
                text = f"{code} - {confidence:.2f}"
                image = draw_plate_on_image(frame, box, text, font=font_ch)
        
        if results and len(results) > 0:
            code, confidence, _, _ = results[0]
            carcher_str = f'carcher : {code}'
            confidence_str = f'confidence: {confidence:.2f}'

        # cv2.imshow("image",image)

        #显示在小车的lcd屏幕上
        b,g,r = cv2.split(image)
        img = cv2.merge((r,g,b))
        imgok = Image.fromarray(img)
        mydisplay.ShowImage(imgok)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if button.press_b():
            break

except:
    cv2.destroyAllWindows()
    camera.release() 
