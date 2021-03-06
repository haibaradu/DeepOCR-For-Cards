# -*- coding: utf-8 -*-
import cv2
import numpy as np
from ocr.ocr import OCR
import time
import threading
import socket
import base64
from opencv_pkg.z_seg import process
import numpy


def get_image(path):
    #获取图片
    img=cv2.imread(path,255)
    gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return img, gray

def Gaussian_Blur(gray):
    # 高斯去噪
    blurred = cv2.GaussianBlur(gray, (9, 9),0)

    return blurred

def Sobel_gradient(blurred):
    # 索比尔算子来计算x、y方向梯度
    gradX = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=1, dy=0)
    gradY = cv2.Sobel(blurred, ddepth=cv2.CV_32F, dx=0, dy=1)

    gradient = cv2.subtract(gradX, gradY)
    gradient = cv2.convertScaleAbs(gradient)

    return gradX, gradY, gradient

def Thresh_and_blur(gradient):

    blurred = cv2.GaussianBlur(gradient, (9, 9),0)
    #thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 101, 10);
    (_, thresh) = cv2.threshold(blurred, 90, 255, cv2.THRESH_BINARY)

    return thresh

def image_morphology(total_area, thresh):
    horizontal = np.mat(thresh)
    vertical = np.mat(thresh)
    scale = 60
    horizontalsize = int(horizontal.shape[0] / scale)
    verticalsize = int(vertical.shape[1] / scale)
    # 建立一个椭圆核函数
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
    # 执行图像形态学, 细节直接查文档，很简单
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    closed = cv2.erode(closed, None, iterations=4)
    closed = cv2.dilate(closed, None, iterations=4)
    (_, cnts, hierarchy) = cv2.findContours(closed.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    con_hor = 1
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w*h > 0.5*total_area:
            con_hor = 0
            break

    if con_hor == 1:
        horizontalkernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontalsize, 1))
        closed = cv2.erode(closed, horizontalkernel, None, iterations=1)
        closed = cv2.dilate(closed, horizontalkernel, None, iterations=10)
    return closed
""" con_ver = 1
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w*h > 0.5*total_area:
            con_ver = 0
            break

    if con_ver == 1:
        verticalkernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, verticalsize))
        closed = cv2.erode(closed, verticalkernel, None, iterations=1)
        closed = cv2.dilate(closed, verticalkernel, None, iterations=10)"""

def findcnts_and_box_point(closed):
    # 这里opencv3返回的是三个参数
    (_, cnts, hierarchy) = cv2.findContours(closed.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    c = sorted(cnts, key=cv2.contourArea, reverse=True)[0]
    # compute the rotated bounding box of the largest contour
    rect = cv2.minAreaRect(c)
    box = np.int0(cv2.boxPoints(rect))

    return box

def drawcnts_and_cut(original_img, box):
    # 因为这个函数有极强的破坏性，所有需要在img.copy()上画
    # draw a bounding box arounded the detected barcode and display the image
    draw_img = cv2.drawContours(original_img.copy(), [box], -1, (0, 0, 255), 3)

    Xs = [i[0] for i in box]
    Ys = [i[1] for i in box]
    x1 = min(Xs)
    x2 = max(Xs)
    y1 = min(Ys)
    y2 = max(Ys)
    hight = y2 - y1
    width = x2 - x1
    crop_img = original_img[y1:y1+hight, x1:x1+width]

    return draw_img, crop_img

def get_word_and_pic(crop_img):
    imgray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(imgray, 90, 255, cv2.THRESH_BINARY)
    (_, cnts, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    c = sorted(cnts, key=cv2.contourArea, reverse=True)[0]
    x, y, w, h = cv2.boundingRect(c)
    approx = np.float32([[0, 0], [0, h], [w, 0], [w, h]])
    corners = np.float32([[0, 0], [0, 540], [860, 0], [860, 540]])
    t = cv2.getPerspectiveTransform(approx, corners)
    card = cv2.warpPerspective(crop_img, t, (860, 540))

    pic = card[50:330, 40:270]
    word = card[330:540, 30:345]
    return card, pic, word

def get_output(path):

    img_path = path
    original_img, gray = get_image(img_path)
    total_area = original_img.shape[0] * original_img.shape[1]
    blurred = Gaussian_Blur(gray)
    gradX, gradY, gradient = Sobel_gradient(blurred)
    thresh = Thresh_and_blur(gradient)
    closed = image_morphology(total_area, thresh)
    box = findcnts_and_box_point(closed)
    draw_img, crop_img = drawcnts_and_cut(original_img, box)
    card, pic, word = get_word_and_pic(crop_img)
    from matplotlib import pyplot as plt
    def fix_color(img):
        # opencv读图像是奇怪的BGR的顺序，在plot输出的时候重新排序成RGB
        (b, g, r) = cv2.split(img)
        return cv2.merge([r, g, b])
    # cv2.namedWindow('draw_img',0)
    # cv2.imshow('draw_img', draw_img)
    # cv2.namedWindow('card')
    # cv2.imshow('card', card)
    # cv2.namedWindow('pic',0)
    # cv2.imshow('pic', pic)
    # word=fix_color(word)
    # plt.imshow(word)
    # plt.show()
    # cv2.namedWindow('word',0)
    # cv2.imshow('word', word)
    # cv2.namedWindow('thresh',0)
    # cv2.imshow('thresh', thresh)
    # cv2.namedWindow('closed',0)
    # cv2.imshow('closed', closed)
    # cv2.waitKey(0)

    return word, card


def tcp_link(sock, addr):
    a=1
    file_type = sock.recv(1024)
    file_type = file_type.decode("utf-8")
    b_len = sock.recv(1024)
    s_len = b_len.decode("utf-8")
    length = int(s_len)
    print(length)
    buf = 4096
    times = length/buf
    result = ""

    # ff=b""
    # d = sock.recv(buf)
    # while (a <= times + 2):
    #     print (a)
    #     a = a + 1
    #     # time.sleep(0.1)
    #     ff+=d
    #     d = sock.recv(buf)
    # print("read finish!")
    # image = np.asarray(bytearray(ff), dtype="uint8")
    # image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    # print (image)
    # #ss=OCR(ff)
    # #print (ss)


    with open("../pics/"+s_len+file_type,'wb') as f:
        d = sock.recv(buf)
        sock.settimeout(2)
        while True:
        # while (a <= times + 2):
            print (a)
            a = a + 1
            # time.sleep(0.1)
            # if d == "exit".encode("utf-8"):
            #     break
            f.write(d)
            try:
                d = sock.recv(buf)
            except Exception:
                break
        print("read finish!")
        try:
            word, card = get_output("../pics/" + s_len + file_type)
            _, my_byte = cv2.imencode(".jpg", word)
            my_byte = my_byte.tobytes()
            dict = OCR(my_byte)
            print (dict)
            print ("===")
            if ((dict['department'] == "") | (dict['id'] == "")):
                raise Exception
            result = str(dict)
        except Exception:
            try:
                dict = process()
                print (dict)
                if ((dict['department'] == "") | (dict['id'] == "")):
                    raise Exception
                result = str(dict)
            except Exception:
                try:
                    # todo: 正式版本中应该是读管道
                    img = cv2.imread("../pics/" + s_len + file_type)
                    # 引入ocr函数进行识别
                    _, my_byte = cv2.imencode(".jpg", img)
                    my_byte = my_byte.tobytes()
                    dict = OCR(my_byte)
                    print (dict)
                    if ((dict['department'] == "") | (dict['id'] == "")):
                        raise Exception
                    result = str(dict)
                except Exception :
                    result = "error"
                    print("报错内容")


    # data = b''.join(buffer)

    # data = sock.recv(buf)
    # print(data.decode("utf-8"))
    sock.send(result.encode("utf-8"))


# if __name__ == "__main__":
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.bind(('0.0.0.0', 10290))
#     s.listen(100)
#     print("Waiting for connection.")
#     while True:
#         sock, addr = s.accept()
#         t = threading.Thread(target=tcp_link, args=(sock, addr))
#         t.start()
    '''   
    try:
        word, card = get_output("../pics/card5.jpeg")
        _, my_byte = cv2.imencode(".png", word)
        my_byte = my_byte.tobytes()
        dict = OCR(my_byte)
        if ((dict['department'] == "") | (dict['id'] == "")):
            raise Exception
        print (dict)
    except Exception:
        try:
            # todo: 正式版本中应该是读管道
            img = cv2.imread("../pics/card5.jpeg")
            # 引入ocr函数进行识别
            _, my_byte = cv2.imencode(".png", img)
            my_byte = my_byte.tobytes()
            dict=OCR(my_byte)
            if((dict['department']=="")|(dict['id']=="")):
                 raise Exception
            print (dict)
        except Exception:
            print("报错内容")
        '''


