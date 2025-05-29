import os, socket, sys, time
import spidev as SPI
import xgoscreen.LCD_2inch as LCD_2inch
from PIL import Image, ImageDraw, ImageFont
from key import Button

from uiutils import *

path = os.getcwd()

# define colors
color_bg = (8, 10, 26)
color_unselect = (89, 99, 149)
color_select = (24, 47, 223)

# const
firmware_info = "v1.0"
# font
font1 = ImageFont.truetype("/home/pi/model/msyh.ttc", 12)
font2 = ImageFont.truetype("/home/pi/model/msyh.ttc", 20)


# draw methods
def display_cjk_string(
    splash,
    x,
    y,
    text,
    color=(255, 255, 255),
    font_size=1,
    scale=1,
    mono_space=False,
    auto_wrap=True,
    background_color=(0, 0, 0),
):
    splash.text((x, y), text, fill=color, font=font_size)


def lcd_rect(x, y, w, h, color, thickness):
    if thickness:
        draw.rectangle([(x, y), (w, h)], color, width=thickness)
    else:
        draw.rectangle([(x, y), (w, h)], fill=None, outline=color_bg, width=2)


lcd_rect(0, 0, 320, 240, color=color_bg, thickness=-1)
display.ShowImage(splash)

MENU_ITEM_PARENT_PATH = "./pics/"

if dog_type == "M" or dog_type == "L":
    MENU_ITEMS = [
        # pic kinds program show
        ("dog_show", "1movement", "dog_show", la["DEMOEN"]["SHOW"]),
        ("network", "18vision", "network", la["DEMOEN"]["NETWORK"]),
        ("gpt_free", "10voice", "gpt_free", la["DEMOEN"]["GPTFREE"]),
        ("chatgpt", "10voice", "chatgpt", la["DEMOEN"]["CHATGPT"]),
        ("speech", "10voice", "speech", la["DEMOEN"]["SPEECH"]),
        ("gpt_draw", "10voice", "gpt_draw", la["DEMOEN"]["GPTDRAW"]),
        ("gpt_rec", "10voice", "gpt_rec", la["DEMOEN"]["GPTREC"]),
        ("face_mask", "3vision", "face_mask", la["DEMOEN"]["MASK"]),
        ("face_decetion", "7vision", "face_decetion", la["DEMOEN"]["FACETRACK"]),
        ("hands", "4vision", "hands", la["DEMOEN"]["HANDS"]),
        ("height", "13vision", "handh", la["DEMOEN"]["HEIGHT"]),
        ("pose", "8vision", "pose_dog", la["DEMOEN"]["POSE"]),
        # ("follow_person", "10voice", "follow_person", la["DEMOEN"]["FOLLOWPERSON"]),
        ("color", "11vision", "color", la["DEMOEN"]["COLOR"]),
        ("qrcode", "9vision", "qrcode", la["DEMOEN"]["QRCODE"]),
        ("group", "2vision", "group", la["DEMOEN"]["GROUP"]),
        # ("ball_trace", "2vision", "ball_catch", la["DEMOEN"]["CATCH"]),
        # ("vision", "5movement", "vision", la["DEMOEN"]["TEACH"]),
        # ("follow_line", "10voice", "follow_line", la["DEMOEN"]["FOLLOWLINE"]),
        ("wifi_set", "15vision", "wifi_set", la["DEMOEN"]["WIFISET"]),
        # ("wpa_set", "16vision", "wpa_set", la["DEMOEN"]["WAPSET"]),
        ("language", "20vision", "language", la["DEMOEN"]["LANGUAGE"]),
        ("volume", "21vision", "volume", la["DEMOEN"]["VOLUME"]),
        ("device", "19vision", "device", la["DEMOEN"]["DEVICE"]),
        # ("sound", "12vision", "sound", la["DEMOEN"]["SOUND"]),
        # ("segmentation", "6vision", "segmentation", la["DEMOEN"]["SEGMENT"]),
        # ("yolo", "14vision", "yolofast", la["DEMOEN"]["YOLO"]),
        # ("burn", "17vision", "burn", la["DEMOEN"]["BURN"]),
        # ("gpt_cmd", "10voice", "gpt_cmd", la["DEMOEN"]["GPTCMD"]),
    ]
elif dog_type == "R":
    MENU_ITEMS = [
        # pic kinds program show
        ("dog_show", "1movement", "dog_show", la["DEMOEN"]["SHOW"]),
        ("network", "18vision", "network", la["DEMOEN"]["NETWORK"]),
        ("gpt_free", "10voice", "gpt_free", la["DEMOEN"]["GPTFREE"]),
        ("chatgpt", "10voice", "chatgpt", la["DEMOEN"]["CHATGPT"]),
        ("speech", "10voice", "speech", la["DEMOEN"]["SPEECH"]),
        ("gpt_draw", "10voice", "gpt_draw", la["DEMOEN"]["GPTDRAW"]),
        ("gpt_rec", "10voice", "gpt_rec", la["DEMOEN"]["GPTREC"]),
        ("face_mask", "3vision", "face_mask", la["DEMOEN"]["MASK"]),
        ("face_decetion", "7vision", "face_decetion", la["DEMOEN"]["FACETRACK"]),
        ("hands", "4vision", "hands", la["DEMOEN"]["HANDS"]),
        ("height", "13vision", "handh", la["DEMOEN"]["HEIGHT"]),
        ("pose", "8vision", "pose_dog", la["DEMOEN"]["POSE"]),
        # ("follow_person", "10voice", "follow_person", la["DEMOEN"]["FOLLOWPERSON"]),
        ("color", "11vision", "color", la["DEMOEN"]["COLOR"]),
        ("qrcode", "9vision", "qrcode", la["DEMOEN"]["QRCODE"]),  
        #yahboom 改动 #在此后面添加功能 #第二个参数随便填
        ("yolo", "14vision", "myyolofast", la["DEMOEN"]["YOLO"]),#物体检测
        ("mycolor", "112vision", "mycolor_detection", la["DEMOEN"]["MYCOLOR"]), #颜色识别
        ("CarFollow", "16vision","mycolor_follow", la["DEMOEN"]["COLORFOLLOW"]),#颜色跟随
        ("liPlate", "112vision", "mycamera_license", la["DEMOEN"]["NUMPLATE"]), #车牌识别 
        ("myobject", "16vision", "myobject_recognition", la["DEMOEN"]["OBJDETECTION"]), #物体检测
        ("mytarget", "16vision", "mytarget_detection", la["DEMOEN"]["CHEAK"]), #目标检测
        ("myFace01", "16vision", "myFaceDetection", la["DEMOEN"]["FACEDECTET"]), #人脸检测
        ("myFace02", "16vision", "myFaceLandmarks", la["DEMOEN"]["FACELAMRK"]), #人脸特效
        ("FingerCtrl", "16vision", "myFingerCtrl", la["DEMOEN"]["FINGER"]), #手指识别
        ("QRCar", "16vision","myqrcodesport", la["DEMOEN"]["QRCONTROL"]),#二维码控制运动
        ("Gesture", "16vision","myGesture_follows", la["DEMOEN"]["GTFOLLOW"]),#手势跟随
        ("3D", "16vision","myObjectron", la["DEMOEN"]["3DDETECT"]),#3维物体检测
        #yahboom
        ("wifi_set", "15vision", "wifi_set", la["DEMOEN"]["WIFISET"]),
        #("wpa_set", "16vision", "wpa_set", la["DEMOEN"]["WAPSET"]),
        ("language", "20vision", "language", la["DEMOEN"]["LANGUAGE"]),
        ("volume", "21vision", "volume", la["DEMOEN"]["VOLUME"]),
        ("device", "19vision", "device", la["DEMOEN"]["DEVICE"]),
        ("system", "19vision", "system", la["DEMOEN"]["SYSTEM"]),
        # ("group", "2vision", "group", la["DEMOEN"]["GROUP"]),
        # ("sound", "12vision", "sound", la["DEMOEN"]["SOUND"]),
        # ("segmentation", "6vision", "segmentation", la["DEMOEN"]["SEGMENT"]),
        #("yolo", "14vision", "yolofast", la["DEMOEN"]["YOLO"]),
        # ("burn", "17vision", "burn", la["DEMOEN"]["BURN"]),
    ]

SELECT_BOX = [80, 68]
MENU_ITEM_COORD = [
    [0, 36, SELECT_BOX[0], SELECT_BOX[1]],
    [80, 36, SELECT_BOX[0], SELECT_BOX[1]],
    [160, 36, SELECT_BOX[0], SELECT_BOX[1]],
    [240, 36, SELECT_BOX[0], SELECT_BOX[1]],
    [0, 104, SELECT_BOX[0], SELECT_BOX[1]],
    [80, 104, SELECT_BOX[0], SELECT_BOX[1]],
    [160, 104, SELECT_BOX[0], SELECT_BOX[1]],
    [240, 104, SELECT_BOX[0], SELECT_BOX[1]],
    [0, 172, SELECT_BOX[0], SELECT_BOX[1]],
    [80, 172, SELECT_BOX[0], SELECT_BOX[1]],
    [160, 172, SELECT_BOX[0], SELECT_BOX[1]],
    [240, 172, SELECT_BOX[0], SELECT_BOX[1]],
]
MENU_TEXT_COORD = [
    [0, 84],
    [0 + 80, 84],
    [0 + 160, 84],
    [0 + 240, 84],
    [0, 152],
    [0 + 80, 152],
    [0 + 160, 152],
    [0 + 240, 152],
    [0, 220],
    [0 + 80, 220],
    [0 + 160, 220],
    [0 + 240, 220],
]
MENU_PIC_COORD = [
    [26, 47],
    [26 + 80, 47],
    [26 + 160, 47],
    [26 + 240, 47],
    [26, 115],
    [26 + 80, 115],
    [26 + 160, 115],
    [26 + 240, 115],
    [26, 183],
    [26 + 80, 183],
    [26 + 160, 183],
    [26 + 240, 183],
]


MENU_TOTAL_ITEMS = len(MENU_ITEMS) - 1
MENU_TOTAL_PAGES = MENU_TOTAL_ITEMS // 12
MENU_CURRENT_SELECT = 0
MENU_PAGE_SWAP_COUNT = 0
print("CALC MENUS")
print(MENU_TOTAL_ITEMS, MENU_TOTAL_PAGES)


def draw_item(row, type, realindex):
    if type == "unselected":
        lcd_rect(
            MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][1],
            MENU_ITEM_COORD[row][2] + MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][3] + MENU_ITEM_COORD[row][1],
            color=color_bg,
            thickness=-1,
        )
        picpath = "./pics/" + MENU_ITEMS[realindex][0] + ".png"
        nav_up = Image.open(picpath)
        draw.bitmap((MENU_PIC_COORD[row][0], MENU_PIC_COORD[row][1]), nav_up)
        l = len(MENU_ITEMS[realindex][3])
        im = (10 - l) * 2 - 2
        display_cjk_string(
            draw,
            MENU_TEXT_COORD[row][0] + im,
            MENU_TEXT_COORD[row][1],
            MENU_ITEMS[realindex][3],
            font_size=font1,
            color=color_unselect,
            background_color=color_bg,
        )
    elif type == "selected":
        lcd_rect(
            MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][1],
            MENU_ITEM_COORD[row][2] + MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][3] + MENU_ITEM_COORD[row][1],
            color=color_select,
            thickness=1,
        )
        picpath = "./pics/" + MENU_ITEMS[realindex][0] + ".png"
        nav_up = Image.open(picpath)
        draw.bitmap((MENU_PIC_COORD[row][0], MENU_PIC_COORD[row][1]), nav_up)
        l = len(MENU_ITEMS[realindex][3])
        im = (10 - l) * 2 - 2
        display_cjk_string(
            draw,
            MENU_TEXT_COORD[row][0] + im,
            MENU_TEXT_COORD[row][1],
            MENU_ITEMS[realindex][3],
            font_size=font1,
            color=color_white,
            background_color=color_select,
        )
    elif type == "clearup":
        row = row - 1
        lcd_rect(
            MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][1],
            MENU_ITEM_COORD[row][2] + MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][3] + MENU_ITEM_COORD[row][1],
            color=color_bg,
            thickness=-1,
        )
        picpath = "./pics/" + MENU_ITEMS[realindex][0] + ".png"
        nav_up = Image.open(picpath)
        draw.bitmap((MENU_PIC_COORD[row][0], MENU_PIC_COORD[row][1]), nav_up)
        l = len(MENU_ITEMS[realindex][3])
        im = (10 - l) * 2 - 2
        display_cjk_string(
            draw,
            MENU_TEXT_COORD[row][0] + im,
            MENU_TEXT_COORD[row][1],
            MENU_ITEMS[realindex][3],
            font_size=font1,
            color=color_unselect,
            background_color=color_bg,
        )
    elif type == "cleardown":
        row = row + 1
        lcd_rect(
            MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][1],
            MENU_ITEM_COORD[row][2] + MENU_ITEM_COORD[row][0],
            MENU_ITEM_COORD[row][3] + MENU_ITEM_COORD[row][1],
            color=color_bg,
            thickness=-1,
        )
        if realindex == 28:
            realindex = 0
        print(realindex)
        picpath = "./pics/" + MENU_ITEMS[realindex][0] + ".png"
        nav_up = Image.open(picpath)
        draw.bitmap((MENU_PIC_COORD[row][0], MENU_PIC_COORD[row][1]), nav_up)
        l = len(MENU_ITEMS[realindex][3])
        im = (10 - l) * 2 - 2
        display_cjk_string(
            draw,
            MENU_TEXT_COORD[row][0] + im,
            MENU_TEXT_COORD[row][1],
            MENU_ITEMS[realindex][3],
            font_size=font1,
            color=color_unselect,
            background_color=color_bg,
        )


def clear_page():
    print("clear page")
    lcd_rect(0, 36, 320, 240, color=color_bg, thickness=-1)


def draw_title_bar(index):
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        77,
        7,
        la["DEMOEN"]["EXAMPLES"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )
    display_cjk_string(
        draw,
        203,
        7,
        str(index + 1) + "/" + str(MENU_TOTAL_ITEMS + 1),
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )


def draw_title_open():
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        85,
        7,
        la["DEMOEN"]["OPENING"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )


def draw_title_error():
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        85,
        7,
        la["DEMOEN"]["FAIL"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )


draw_title_bar(0)

for i in range(0, 12):
    draw_item(i, "unselected", i)
display.ShowImage(splash)
draw_item(0, "selected", 0)

display.ShowImage(splash)

inputkey = ""
while True:

    key_state_left = 0
    key_state_down = 0
    key_state_right = 0

    if button.press_a():
        key_state_down = 1
        key_state_left = 0
        key_state_right = 0
    elif button.press_c():
        key_state_down = 0
        key_state_left = 1
        key_state_right = 0
    elif button.press_d():
        key_state_down = 0
        key_state_left = 0
        key_state_right = 1
    elif button.press_b():
        os.system("pkill mplayer")
        break

    # -----------------------------
    if key_state_left == 1:
        clear_page()
        if MENU_CURRENT_SELECT % 12 == 0:
            if MENU_PAGE_SWAP_COUNT == 0:
                MENU_PAGE_SWAP_COUNT = MENU_TOTAL_PAGES
                MENU_CURRENT_SELECT = MENU_TOTAL_ITEMS
            else:
                MENU_PAGE_SWAP_COUNT -= 1
                MENU_CURRENT_SELECT -= 1
        else:
            MENU_CURRENT_SELECT -= 1

        print(
            "Key A Pressed, MENU_CURRENT_SELECT_ROW_MENU_PAGE_SWAP_COUNT: "
            + str(MENU_CURRENT_SELECT)
            + ", \t"
            + str(MENU_CURRENT_SELECT % 12)
            + ", "
            + str(MENU_PAGE_SWAP_COUNT)
        )

        draw_title_bar(MENU_CURRENT_SELECT)

        if MENU_PAGE_SWAP_COUNT == MENU_TOTAL_PAGES:
            for i in range(MENU_TOTAL_PAGES * 12, MENU_TOTAL_ITEMS + 1, 1):
                print(i)
                draw_item(i % 12, "unselected", i)
        else:
            for i in range(
                MENU_PAGE_SWAP_COUNT * 12, MENU_PAGE_SWAP_COUNT * 12 + 12, 1
            ):
                print(i)
                draw_item(i % 12, "unselected", i)

        draw_item(MENU_CURRENT_SELECT % 12, "selected", MENU_CURRENT_SELECT)

    if key_state_right == 1:
        clear_page()
        if MENU_CURRENT_SELECT == MENU_TOTAL_ITEMS:
            MENU_PAGE_SWAP_COUNT = 0
            MENU_CURRENT_SELECT = 0
        elif MENU_CURRENT_SELECT % 12 == 11:
            MENU_PAGE_SWAP_COUNT += 1
            MENU_CURRENT_SELECT += 1
        else:
            MENU_CURRENT_SELECT += 1

        print(
            "Key B Pressed, MENU_CURRENT_SELECT_ROW_MENU_PAGE_SWAP_COUNT: "
            + str(MENU_CURRENT_SELECT)
            + ", \t"
            + str(MENU_CURRENT_SELECT % 12)
            + ", "
            + str(MENU_PAGE_SWAP_COUNT)
        )

        draw_title_bar(MENU_CURRENT_SELECT)

        if MENU_PAGE_SWAP_COUNT == MENU_TOTAL_PAGES:
            for i in range(MENU_TOTAL_PAGES * 12, MENU_TOTAL_ITEMS + 1, 1):
                print(i)
                draw_item(i % 12, "unselected", i)
        else:
            for i in range(
                MENU_PAGE_SWAP_COUNT * 12, MENU_PAGE_SWAP_COUNT * 12 + 12, 1
            ):
                print(i)
                draw_item(i % 12, "unselected", i)

        draw_item(MENU_CURRENT_SELECT % 12, "selected", MENU_CURRENT_SELECT)

    if key_state_down == 1:
        try:
            display.ShowImage(splash)
            print("Running: " + MENU_ITEMS[MENU_CURRENT_SELECT][2])
            draw_title_open()
            if MENU_ITEMS[MENU_CURRENT_SELECT][2] == "dog_show":
                import demos.dog_show
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "face_mask":
                os.system("python3 ./demos/face_mask.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "hands":
                os.system(" python3 ./demos/hands.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "vision":
                os.system("python3 ./demos/dog_vision_show.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "segmentation":
                os.system("python3 ./demos/segmentation.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "face_decetion":
                os.system("python3 ./demos/face_decetion.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "pose":
                os.system("python3 ./demos/pose.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "image_class":
                os.system("python3 ./demos/image_class.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "image_dete":
                os.system("python3 ./demos/image_dete.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "qrcode":
                os.system("python3 ./demos/qrcode.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "speech":
                os.system("python3 ./demos/speech.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "sound":
                os.system("python3 ./demos/sound.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "handh":
                os.system("python3 ./demos/hp.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "color":
                os.system("python3 ./demos/color.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "yolofast":
                os.system("python3 ./demos/yolofast.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "wifi_set":
                os.system("sudo python3 ./demos/wifi_set.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "wpa_set":
                os.system("sudo python3 ./demos/wpa_set.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "burn":
                os.system("python3 ./demos/ota.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "device":
                os.system("python3 ./demos/device.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "network":
                os.system("sudo python3 ./demos/network.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "group":
                os.system("python3 ./demos/group.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "language":
                os.system("python3 ./demos/language.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "volume":
                os.system("python3 ./demos/volume.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "chatgpt":
                os.system("python3 ./demos/chatgpt.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "gpt_cmd":
                os.system("python3 ./demos/gpt_cmd.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "ball_catch":
                os.system("python3 ./demos/ball_catch.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "gpt_draw":
                os.system("python3 ./demos/gpt_draw.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "gpt_rec":
                os.system("python3 ./demos/gpt_rec.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "follow_person":
                os.system("python3 ./demos/follow_person.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "follow_line":
                os.system("python3 ./demos/follow_line.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "gpt_free":
                os.system("python3 ./demos/gpt_free.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "pose_dog":
                os.system("python3 ./demos/pose_dog.py")
            #yahboom add!
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myyolofast": #yolo
                os.system("python3 ./demos/myyolofast.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "mycamera_license": #车牌
                os.system("python3 ./demos/mycamera_license.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myobject_recognition": #物体识别
                os.system("python3 ./demos/myobject_recognition.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "mytarget_detection": #目标检测
                os.system("python3 ./demos/mytarget_detection.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myFaceDetection": #人脸检测
                os.system("python3 ./demos/myFaceDetection.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myFaceLandmarks": #人脸特效
                os.system("python3 ./demos/myFaceLandmarks.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myFingerCtrl": #手势识别
                os.system("python3 ./demos/myFingerCtrl.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "mycolor_detection": #颜色识别
                os.system("python3 ./demos/mycolor_detection.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myqrcodesport": #二维码控制运动
                os.system("python3 ./demos/myqrcodesport.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "mycolor_follow": #颜色跟随
                os.system("python3 ./demos/mycolor_follow.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myGesture_follows": #手势跟随
                os.system("python3 ./demos/myGesture_follows.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "myObjectron": #3维物体检测
                os.system("python3 ./demos/myObjectron.py")
            elif MENU_ITEMS[MENU_CURRENT_SELECT][2] == "system": #系统信息
                os.system("python3 ./demos/system_img.py")
                
            #yahboom add!

            print("program done")
            draw_title_bar(MENU_CURRENT_SELECT)
        except BaseException as e:
            print(str(e))
            draw_title_bar(MENU_CURRENT_SELECT)
        print("Key C Pressed.")
        time.sleep(0.5)
        draw_title_bar(MENU_CURRENT_SELECT)

    display.ShowImage(splash)

print("quit")
