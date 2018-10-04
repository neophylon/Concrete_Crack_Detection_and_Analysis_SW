# 1. 사전에 학습시킨 균열 탐지 딥러닝 weight와 Single Shot Multibox Detector model을 불러옵니다. 

# 1. Upload the pre-trained deep learning weight and Single Shot Multibox Detector model for crack detection.

from keras import backend as K
from keras.models import load_model
from keras.preprocessing import image
from keras.optimizers import Adam
from imageio import imread
import numpy as np
from matplotlib import pyplot as plt
import cv2
import time

from models.keras_ssd300 import ssd_300
from keras_loss_function.keras_ssd_loss import SSDLoss
from keras_layers.keras_layer_AnchorBoxes import AnchorBoxes
from keras_layers.keras_layer_DecodeDetections import DecodeDetections
from keras_layers.keras_layer_DecodeDetectionsFast import DecodeDetectionsFast
from keras_layers.keras_layer_L2Normalization import L2Normalization

from ssd_encoder_decoder.ssd_output_decoder import decode_detections, decode_detections_fast

from data_generator.object_detection_2d_data_generator import DataGenerator
from data_generator.object_detection_2d_photometric_ops import ConvertTo3Channels
from data_generator.object_detection_2d_geometric_ops import Resize
from data_generator.object_detection_2d_misc_utils import apply_inverse_transforms

%matplotlib inline

img_height = 300
img_width = 300

K.clear_session() 

# 변수 값은 Single Shot Multibox Detector의 원래 수치를 변경하지 않고 사용하였습니다.
# The original value of parameters of 'Single Shot Multibox Detector' was used without any changes.
model = ssd_300(image_size=(img_height, img_width, 3),
                n_classes=2,
                mode='inference',
                l2_regularization=0.0005,
                scales=[0.1, 0.2, 0.37, 0.54, 0.71, 0.88, 1.05], 
                aspect_ratios_per_layer=[[1.0, 2.0, 0.5],
                                         [1.0, 2.0, 0.5, 3.0, 1.0/3.0],
                                         [1.0, 2.0, 0.5, 3.0, 1.0/3.0],
                                         [1.0, 2.0, 0.5, 3.0, 1.0/3.0],
                                         [1.0, 2.0, 0.5],
                                         [1.0, 2.0, 0.5]],
                two_boxes_for_ar1=True,
                steps=[8, 16, 32, 64, 100, 300],
                offsets=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                clip_boxes=False,
                variances=[0.1, 0.1, 0.2, 0.2],
                normalize_coords=True,
                subtract_mean=[123, 117, 104],
                swap_channels=[2, 1, 0],
                confidence_thresh=0.5,
                iou_threshold=0.45,
                top_k=200,
                nms_max_output_size=400)

# 학습된 weight를 불러오는 경로를 입력합니다.
# Input your own path for pre-trained weight.
#----------------------서버 경로로 변경---------------------------
weights_path = 'C:\\Users\\user\\keras\\ssd_keras\\ssd300_pascal_07+12_epoch-08_loss-1.9471_val_loss-1.9156.h5'

model.load_weights(weights_path, by_name=True)

adam = Adam(lr=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)

ssd_loss = SSDLoss(neg_pos_ratio=3, alpha=1.0)

model.compile(optimizer=adam, loss=ssd_loss.compute_loss)

# 2. 드론이 촬영한 콘크리트 외벽 영상에서 프레임을 추출합니다(4fps).
#    이 프레임 이미지들을 균열 탐지 딥러닝 엔진에 입력하여 inference를 합니다.
#    Inference의 결과 값으로 균열의 위치를 bounding box의 형태로 report합니다.

# 2. Extract frames out of the video which recorded the concrete surface shoot by drone(4fps).
#    Input the frame images into the deep learning engine for inference.
#    The positional information will be reported as a bounding box, as a result of the inference.


# 드론으로 촬영한 영상의 경로를 입력합니다.
# Input the path of the video shoot by drone.
#----------------------서버 경로로 변경---------------------------
vidcap = cv2.VideoCapture('C:\\Users\\user\Desktop\\video5.mp4')
success,imagefile = vidcap.read()
count = 0
while success:
    if(count%6==0):
# 추출된 프레임 이미지들을 저장할 경로를 입력합니다.
# Input the path to save the extracted frame images.
#----------------------서버 경로로 변경---------------------------
        cv2.imwrite("C:\\Users\\user\Desktop\\frames\\frame%d.jpg" % count, imagefile)    
    success,imagefile = vidcap.read()
    count += 1

orig_images = [] 
input_images = [] 

#!!! (중요) 영상의 재생 시간을 play_time_secs에 입력합니다. 초단위입니다.
#!!! (Important) Input the play time of the video into 'play_time_secs' variable, in seconds.
#--------------------영상을 UI에서 입력하면, 영상 재생 시간이 자동으로 변수에 입력되게 바꾸자!!!!!------------------- 
play_time_secs = 13
frames_count = 24*play_time_secs

for i in range(0,frames_count):
    if(i%6==0):
# 저장한 프레임 이미지들을 다시 불러올 수 있도록 동일한 경로를 입력합니다.
# Input the same path used before to load the saved frame images.
#----------------------서버 경로로 변경---------------------------
        img_path = 'C:\\Users\\user\Desktop\\frames\\frame%d.jpg'%i
        orig_images.append(imread(img_path))
        img = image.load_img(img_path, target_size=(img_height, img_width))
        img = image.img_to_array(img)
        img = np.array(img)
        input_images.append(img)
        
input_images = np.array(input_images)
orig_images = np.array(orig_images)

# !!! (중요) 한 번에 처리되는 프레임 이미지의 갯수를 입력합니다. 보유 GPU에 따라 줄여야 할 수 있습니다.
# !!! (Important) Input the number of -------------------
#--------------------------여기 변수 어떻게 처리할까?---------------------------
num_of_frames = 16
counting = 0
saving_bounding_boxes = []

print("Predicted boxes:\n")
print('   class   conf xmin   ymin   xmax   ymax')

for i in range(0, 4):
    y_pred = model.predict(input_images[i])
    confidence_threshold = 0.4

    y_pred_thresh = [y_pred[k][y_pred[k,:,1] > confidence_threshold] for k in range(y_pred.shape[0])]
    np.set_printoptions(precision=2, suppress=True, linewidth=90)

    for j in range(0, num_of_frames):
        print('frame :',counting)
        for box in y_pred_thresh[j]:
            xmin = box[2] * orig_images[0].shape[1] / img_width
            ymin = box[3] * orig_images[0].shape[0] / img_height
            xmax = box[4] * orig_images[0].shape[1] / img_width
            ymax = box[5] * orig_images[0].shape[0] / img_height
            print('xmin : ',xmin, '  ymin : ',ymin, '  xmax : ',xmax, '  ymax : ',ymax)
            # 균열이 탐지된 프레임의 bounding box 위치정보를 saving_bounding_boxes 리스트에 저장합니다.
            # Append the positional information of the bounding box of the detected frame at'saving_bounding_boxes' list.
            saving_bounding_boxes.append([counting, xmin,ymin,xmax,ymax])
        counting += 6
        if(counting>frames_count): break;



# 3. 균열탐지 딥러닝 엔진이 리포트 한 균열 위치에 맞게 프레임 이미지를 잘라냅니다.
# 3. Crop the frame image using the positional information of the crack reported by crack detection deep learning engine.

from skimage import io

cropped_frames = []

for i in range(0, len(saving_bounding_boxes)):
    frame_count = saving_bounding_boxes[i][0]//6
    frame = orig_images[frame_count]
    if(saving_bounding_boxes[i][1] < 0):
        saving_bounding_boxes[i][1] = 0
    xmin = int(saving_bounding_boxes[i][1])
    if(saving_bounding_boxes[i][2] < 0):
        saving_bounding_boxes[i][2] = 0
    ymin = int(saving_bounding_boxes[i][2])
    xmax = int(saving_bounding_boxes[i][3])
    ymax = int(saving_bounding_boxes[i][4])
    print(xmin,ymin,xmax,ymax)
    cropped_frame = orig_images[frame_count][ymin:ymax, xmin:xmax, :]
    cropped_frame = cropped_frame.astype('uint8')
# 잘라낸 프레임 이미지를 저장할 경로를 입력합니다.
# Input the path of the cropped images.
#--------------------------경로를 서버에 맞게 변경--------------------------------
    img_path = '../../Desktop/detected_crack/%d.jpg'%frame_count
    print(img_path)
    cropped_frames.append(cropped_frame)
    io.imsave(img_path, cropped_frame)

# 4. 균열 탐지 딥러닝 엔진이 잘라낸 프레임 이미지에 전처리를 합니다.
#    전처리는 총 3단계로 구성됩니다.
#   1) Image Binarization : 균열인 부분과 균열이 아닌 부분을 분리합니다.
#   2) Skeletonize : 균열의 뼈대를 추출합니다.
#   3) Edge detection : 균열의 외곽선을 추출합니다.

#   이 단계에서는 Image Binarization을 진행합니다.

# 4. Preprocess the frame images cropped by crack detection deep learning engine.
#    The preprocess consists of 3 stages.
#   1) Image Binarization : seperate crack section and the noncrack section.
#   2) Skeletonize : extract the central skeleton of the crack.
#   3) Edge detection : extract the edge of the crack.

#   At this stage, Image Binarization will be done.

import time
import matplotlib
import matplotlib.pyplot as plt
import cv2
from skimage import io
from skimage import data
from skimage.color import rgb2gray
from skimage.data import page
from skimage.filters import (threshold_sauvola)
from PIL import Image

sauvola_frames_Pw_bw = []
sauvola_frames_Pw = []

for i in range(0,len(cropped_frames)):
    img = cropped_frames[i]
    img_gray = rgb2gray(img)

    # window size와 k값은 'Concrete Crack Identification Using a UAV Incorporating Hybrid Image Processing' 논문이 제시한 값을
    # 그대로 사용하였습니다.
    
    # window size and k value were used without any changes from the
    # 'Concrete Crack Identification Using a UAV Incorporating Hybrid Image Processing' thesis.
    window_size_Pw = 71
    thresh_sauvola_Pw = threshold_sauvola(img_gray, window_size=window_size_Pw, k=0.42)

    binary_sauvola_Pw = img_gray > thresh_sauvola_Pw
    binary_sauvola_Pw_bw = img_gray > thresh_sauvola_Pw

    binary_sauvola_Pw_bw.dtype = 'uint8'

    binary_sauvola_Pw_bw *= 255
    
    sauvola_frames_Pw_bw.append(binary_sauvola_Pw_bw)
    sauvola_frames_Pw.append(binary_sauvola_Pw)
    
#------------------------------서버에 맞게 경로 변경------------------------------------
    img_path_Pw = '../../Desktop/Sauvola/Sauvola_Pw_%d.jpg'%i
    
    io.imsave(img_path_Pw, binary_sauvola_Pw_bw)


# 2. Extract the skeletons of each images

from skimage.morphology import skeletonize
from skimage.util import invert

skeleton_frames_Pw = []

for i in range(0,len(cropped_frames)):
# Invert the binarized images
    img_Pw = invert(sauvola_frames_Pw[i])

    # Below are skeletonized images
    skeleton_Pw = skeletonize(img_Pw)

    skeleton_Pw.dtype = 'uint8'

    skeleton_Pw *= 255

    skeleton_frames_Pw.append(skeleton_Pw)
    
    img_path_Pw = "../../Desktop/Skeleton/skeleton_Pw_%d.jpg"%i
    io.imsave(img_path_Pw, skeleton_Pw)
    


# 3. Detect the edges of each images
### edge detection 할 때, 좋은 parameter를 찾아야 한다. 지금은 edge가 너무 두꺼움 (overestimation됨) ###
import numpy as np
from scipy import ndimage as ndi
from skimage import feature

edges_frames_Pw = []
edges_frames_Pl = []

for i in range(0,len(cropped_frames)):
    # Compute the Canny filter for two values of sigma
    # canny(image, sigma=1.0, low_threshold=None, high_threshold=None, mask=None, use_quantiles=False)
    # sigma가 1이었으나, 0.1로 조정하여 실제 균열 edge와 거의 같게 만듦.
    # 정확도에서 문제가 생긴다면 1. skeleton의 방향 설정 방법을 바꾸던가, 2. 여기서 시그마 값을 살짝 늘리거나 줄여가면서 정확도를 테스트 해볼 것
    edges_Pw = feature.canny(sauvola_frames_Pw[i], 0.09)
    #edges_Pl = feature.canny(sauvola_frames_Pl[i], 0.09)

    edges_Pw.dtype = 'uint8'
    #edges_Pl.dtype = 'uint8'

    edges_Pw *= 255
    #edges_Pl *= 255

    edges_frames_Pw.append(edges_Pw)
    #edges_frames_Pl.append(edges_Pl)
    
    img_path_Pw = "../../Desktop/edges/edges_Pw_%d.jpg"%i
    #img_path_Pl = "../../Desktop/edges/edges_Pl_%d.jpg"%i
    
    io.imsave(img_path_Pw, edges_Pw)
    #io.imsave(img_path_Pl, edges_Pl)


#Crack만이 detection되어서 넘어왔다는 가정이 있어야 함. 아니면 외부 배경 이미지도 균열 계산에 포함 됨

import queue
import math

#5픽셀이 기준 or above
dx_dir_right = [-5,-5,-5,-4,-3,-2,-1,0,1,2,3,4,5,5]
dy_dir_right = [0,1,2,3,4,5,5,5,5,5,4,3,2,1]

dx_dir_left = [5,5,5,4,3,2,1,0,-1,-2,-3,-4,-5,-5]
dy_dir_left = [0,-1,-2,-3,-4,-5,-5,-5,-5,-5,-4,-3,-2,-1]

dx_bfs = [-1,-1,0,1,1,1,0,-1]
dy_bfs = [0,1,1,1,0,-1,-1,-1]

start_time = time.time() 

for k in range(0,len(skeleton_frames_Pw)):
    print('--------------''동영상 내 재생 시간 : ',k*0.25,'초','-----------------')
    start = [0,0]
    next = []
    q = queue.Queue()
    q.put(start)

    len_x = skeleton_frames_Pw[k].shape[0]
    len_y = skeleton_frames_Pw[k].shape[1]

    visit = np.zeros((len_x,len_y))
    count = 0
    crack_width_list = []

    while(q.empty() == 0):
        next = q.get()
        x = next[0]
        y = next[1]
        right_x = right_y = left_x = left_y = -1


        if(skeleton_frames_Pw[k][x][y] == 255):
            for i in range(0, len(dx_dir_right)):
                right_x = x + dx_dir_right[i]
                right_y = y + dy_dir_right[i]
                if(right_x<0 or right_y<0 or right_x>=len_x or right_y>=len_y): 
                    right_x = right_y = -1
                    continue;
                if(skeleton_frames_Pw[k][right_x][right_y] == 255): break;
                if(i==13): right_x = right_y = -1

            if(right_x == -1): 
                right_x = x
                right_y = y

            for i in range(0, len(dx_dir_left)):
                left_x = x + dx_dir_left[i]
                left_y = y + dy_dir_left[i]
                if(left_x <0 or left_y<0 or left_x >=len_x or left_y>=len_y): 
                    left_x = left_y = -1
                    continue;
                if(skeleton_frames_Pw[k][left_x][left_y] == 255): break;
                if(i==13): left_x = left_y = -1

            if(left_x == -1): 
                left_x = x
                left_y = y

            base = right_y - left_y
            height = right_x - left_x
            hypotenuse = math.sqrt(base*base + height*height)

            if(base==0 and height != 0): theta = 90.0
            elif(base==0 and height == 0): continue
            else: theta = math.degrees(math.acos((base * base + hypotenuse * hypotenuse - height * height)/(2.0 * base * hypotenuse)))



            theta += 90
            dist = 0

            for i in range(0,2):


                if(theta>360): theta -= 360
                elif(theta<0): theta += 360    
                #print(theta)
                #print('x : ',x,'y : ',y)
                pix_x=x
                pix_y=y

                #theta에러는 나중에 고치고
                #모든 프레임을 처리하기 위한 루프 먼저 돌릴것
                #결과 값을 UI와 연동하자

                if(theta>0 and theta<90):
                    ratio = abs(math.tan(theta))
                    while(1):
                        if((x - pix_x + 1)/(pix_y - y + 1)> ratio): pix_y+=1
                        else: pix_x-=1

                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta>90 and theta<180):
                    ratio = abs(math.tan(theta))
                    while(1):
                        if((x - pix_x + 1)/(y - pix_y + 1)> ratio): pix_y-=1
                        else: pix_x-=1

                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta>180 and theta<270):
                    ratio = abs(math.tan(theta))
                    while(1):
                        if((pix_x - x + 1)/(y - pix_y+ 1)> ratio): pix_y-=1
                        else: pix_x+=1

                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;     

                elif(theta>270 and theta<360):
                    ratio = abs(math.tan(theta))
                    while(1):
                        if((pix_x - x + 1)/(pix_y - y + 1)> ratio): pix_y+=1
                        else: pix_x+=1

                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta == 0.0 or 360.0):
                     while(1):
                        pix_y+=1
                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta == 90.0):
                    while(1):
                        pix_x-=1
                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta == 180.0):
                    while(1):
                        pix_y-=1
                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;

                elif(theta == 270.0):
                     while(1):
                        pix_x+=1
                        if(pix_x<0 or pix_y<0 or pix_x>=len_x or pix_y>=len_y):
                            pix_x = x
                            pix_y = y
                            break;
                        if(edges_frames_Pw[k][pix_x][pix_y]==255): break;            

                dist += math.sqrt((y-pix_y)**2 + (x-pix_x)**2)
                theta += 180        

                #print('pix_x : ',pix_x,'pix_y : ',pix_y,'dist : ', dist,'\n')

            crack_width_list.append(dist)
        
            #해당 위치와 균열 폭을 힘께 저장하는 새로운 리스트 사용하기
        for i in range(0,8):
            next_x = x + dx_bfs[i]
            next_y = y + dy_bfs[i]

            if(next_x<0 or next_y<0 or next_x>=len_x or next_y>=len_y): continue;
            if(visit[next_x][next_y] == 0): 
                q.put([next_x,next_y])
                visit[next_x][next_y] = 1
    
    print('높이 10m 지점, ','좌측 ',k*0.5,'m 지점')
    print('균열 폭 : ',max(crack_width_list)/100,'mm')
    print('위험군 : 상','\n')
        
print("--- %s seconds ---" %(time.time() - start_time))

