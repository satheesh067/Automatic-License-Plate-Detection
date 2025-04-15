import cv2
import numpy as np
import matplotlib.pyplot as plt
import easyocr
import mysql.connector
from mysql.connector import Error
plt.style.use('dark_background')
img_ori = cv2.imread('images/Cars111.png')
height, width, channel = img_ori.shape
gray = cv2.cvtColor(img_ori, cv2.COLOR_BGR2GRAY)
structuringElement = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
imgTopHat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, structuringElement)
imgBlackHat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, structuringElement)
gray = cv2.add(gray, imgTopHat)
gray = cv2.subtract(gray, imgBlackHat)
img_blurred = cv2.GaussianBlur(gray, ksize=(5, 5), sigmaX=0)
img_thresh = cv2.adaptiveThreshold(
    img_blurred, 
    maxValue=255.0, 
    adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    thresholdType=cv2.THRESH_BINARY_INV, 
    blockSize=19, 
    C=9
)
contours, _ = cv2.findContours(img_thresh, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
contours_dict = []
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    contours_dict.append({
        'contour': contour,
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'cx': x + (w / 2),
        'cy': y + (h / 2)
    })
MIN_AREA = 80
MIN_WIDTH, MIN_HEIGHT = 2, 8
MIN_RATIO, MAX_RATIO = 0.25, 1.0
possible_contours = []
cnt = 0
for d in contours_dict:
    area = d['w'] * d['h']
    ratio = d['w'] / d['h']
    if area > MIN_AREA and d['w'] > MIN_WIDTH and d['h'] > MIN_HEIGHT and MIN_RATIO < ratio < MAX_RATIO:
        d['idx'] = cnt
        cnt += 1
        possible_contours.append(d)
MAX_DIAG_MULTIPLYER = 5
MAX_ANGLE_DIFF = 12.0
MAX_AREA_DIFF = 0.5
MAX_WIDTH_DIFF = 0.8
MAX_HEIGHT_DIFF = 0.2
MIN_N_MATCHED = 3
def find_chars(contour_list):
    matched_result_idx = []
    for d1 in contour_list:
        matched_contours_idx = []
        for d2 in contour_list:
            if d1['idx'] == d2['idx']:
                continue
            dx = abs(d1['cx'] - d2['cx'])
            dy = abs(d1['cy'] - d2['cy'])
            distance = np.linalg.norm(np.array([d1['cx'], d1['cy']]) - np.array([d2['cx'], d2['cy']]))
            diagonal_length1 = np.sqrt(d1['w'] ** 2 + d1['h'] ** 2)
            angle_diff = np.degrees(np.arctan(dy / dx)) if dx != 0 else 90
            area_diff = abs(d1['w'] * d1['h'] - d2['w'] * d2['h']) / (d1['w'] * d1['h'])
            width_diff = abs(d1['w'] - d2['w']) / d1['w']
            height_diff = abs(d1['h'] - d2['h']) / d1['h']
            if distance < diagonal_length1 * MAX_DIAG_MULTIPLYER and angle_diff < MAX_ANGLE_DIFF \
                and area_diff < MAX_AREA_DIFF and width_diff < MAX_WIDTH_DIFF and height_diff < MAX_HEIGHT_DIFF:
                matched_contours_idx.append(d2['idx'])
        matched_contours_idx.append(d1['idx'])
        if len(matched_contours_idx) < MIN_N_MATCHED:
            continue
        matched_result_idx.append(matched_contours_idx)
        unmatched_contour_idx = [d4['idx'] for d4 in contour_list if d4['idx'] not in matched_contours_idx]
        unmatched_contour = np.take(possible_contours, unmatched_contour_idx)
        recursive_contour_list = find_chars(unmatched_contour)
        for idx in recursive_contour_list:
            matched_result_idx.append(idx)
        break
    return matched_result_idx

result_idx = find_chars(possible_contours)
matched_result = [np.take(possible_contours, idx_list) for idx_list in result_idx]
PLATE_WIDTH_PADDING = 1.3
PLATE_HEIGHT_PADDING = 1.5
MIN_PLATE_RATIO = 3
MAX_PLATE_RATIO = 10

plate_imgs = []
plate_infos = []

for i, matched_chars in enumerate(matched_result):
    sorted_chars = sorted(matched_chars, key=lambda x: x['cx'])
    plate_cx = (sorted_chars[0]['cx'] + sorted_chars[-1]['cx']) / 2
    plate_cy = (sorted_chars[0]['cy'] + sorted_chars[-1]['cy']) / 2
    plate_width = (sorted_chars[-1]['x'] + sorted_chars[-1]['w'] - sorted_chars[0]['x']) * PLATE_WIDTH_PADDING
    sum_height = sum(d['h'] for d in sorted_chars)
    plate_height = int(sum_height / len(sorted_chars) * PLATE_HEIGHT_PADDING)
    triangle_height = sorted_chars[-1]['cy'] - sorted_chars[0]['cy']
    triangle_hypotenus = np.linalg.norm(
        np.array([sorted_chars[0]['cx'], sorted_chars[0]['cy']]) - 
        np.array([sorted_chars[-1]['cx'], sorted_chars[-1]['cy']])
    )
    angle = np.degrees(np.arcsin(triangle_height / triangle_hypotenus))
    rotation_matrix = cv2.getRotationMatrix2D(center=(plate_cx, plate_cy), angle=angle, scale=1.0)
    img_rotated = cv2.warpAffine(img_thresh, M=rotation_matrix, dsize=(width, height))
    img_cropped = cv2.getRectSubPix(
        img_rotated, 
        patchSize=(int(plate_width), int(plate_height)), 
        center=(int(plate_cx), int(plate_cy))
    )
    if img_cropped.shape[1] / img_cropped.shape[0] < MIN_PLATE_RATIO or \
       img_cropped.shape[1] / img_cropped.shape[0] > MAX_PLATE_RATIO:
        continue
    plate_imgs.append(img_cropped)
    plate_infos.append({
        'x': int(plate_cx - plate_width / 2),
        'y': int(plate_cy - plate_height / 2),
        'w': int(plate_width),
        'h': int(plate_height)
    })
reader = easyocr.Reader(['en'], gpu=False)
plate_1_text = None

for i, plate_img in enumerate(plate_imgs):
    plate_img_resized = cv2.resize(plate_img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    result = reader.readtext(plate_img_resized)
    text = result[0][1] if result else "[No text detected]"
    if text != "[No text detected]":
        plate_1_text = text
        plate_1_img = plate_img_resized
        break
if plate_1_text:
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.imshow(cv2.cvtColor(img_ori, cv2.COLOR_BGR2RGB))
    plt.title("Original Image")
    plt.axis('off')
    plt.subplot(1, 2, 2)
    plt.imshow(cv2.cvtColor(plate_1_img, cv2.COLOR_BGR2RGB))
    #plt.title(f"Detected Plate 1: {plate_1_text}")
    plt.axis('off')

    plt.show()

    print(f"Detected Text on Plate 1: {plate_1_text}")
else:
    print("No valid plates detected.")
import mysql.connector
db = mysql.connector.connect(
    host="localhost",      
    user="root", 
    password="Satheesh@11", 
    database="IIP"  
)
cursor = db.cursor()
if plate_1_text:
    plate_1_text = plate_1_text.strip()
    print(f"Detected Text on Plate: {plate_1_text}")

    query = "SELECT * FROM vehicle_registry WHERE plate_number LIKE %s"
    like_pattern = "%" + plate_1_text + "%" 
    print(f"Executing Query: {query} With parameter: {like_pattern}")

    cursor.execute(query, (like_pattern,))
    result = cursor.fetchone()

    if result:
        print(f"\nPlate Info Found in MySQL:")
        print(f"Plate Number: {result[1]}")  
        print(f"Owner ID    : {result[2]}")  
        print(f"Vehicle Type: {result[3]}")  
        print(f"Make        : {result[4]}") 
        print(f"Model       : {result[5]}")  
        print(f"Color       : {result[6]}") 
        print(f"Insurance Status : {result[7]}")  
        print(f"Insurance Expiry: {result[8]}") 
        print(f"Registration Number: {result[9]}")  
        print(f"Registration Date: {result[10]}")  
        print(f"Registration Expiry: {result[11]}") 
    else:
        print("\nPlate number not found in database.")
cursor.close()
db.close()