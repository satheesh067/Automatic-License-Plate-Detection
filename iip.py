import cv2
from matplotlib import pyplot as plt
import numpy as np
import imutils
import easyocr
import os

# === Load Image ===
image_path = r'C:\vs code\IIp\image3.jpg'
img = cv2.imread(image_path)

if img is None:
    print("Error: Image not found. Check the file path.")
    exit()

# === Preprocess Image ===
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
bfilter = cv2.bilateralFilter(gray, 11, 17, 17)
edged = cv2.Canny(bfilter, 30, 200)

# === Find Contours ===
keypoints = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
contours = imutils.grab_contours(keypoints)
contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

location = None
for contour in contours:
    approx = cv2.approxPolyDP(contour, 0.018 * cv2.arcLength(contour, True), True)
    if len(approx) == 4:
        location = approx
        break

if location is None:
    print("No license plate contour detected.")
    exit()

# === Mask and Crop ===
mask = np.zeros(gray.shape, np.uint8)
new_image = cv2.drawContours(mask, [location], 0, 255, -1)
new_image = cv2.bitwise_and(img, img, mask=mask)

(x, y) = np.where(mask == 255)
(x1, y1) = (np.min(x), np.min(y))
(x2, y2) = (np.max(x), np.max(y))
cropped_image = gray[x1:x2 + 1, y1:y2 + 1]

# === OCR ===
reader = easyocr.Reader(['en'])
result = reader.readtext(cropped_image)

if result:
    text = result[0][-2]
    print(f"Detected Number Plate Text: {text}")
else:
    text = "No text found"
    print("OCR did not detect any text.")

# === Annotate Image ===
font = cv2.FONT_HERSHEY_SIMPLEX
res = cv2.putText(img, text=text, org=(location[0][0][0], location[1][0][1]+60), 
                  fontFace=font, fontScale=1, color=(0,255,0), thickness=2, lineType=cv2.LINE_AA)
res = cv2.rectangle(img, tuple(location[0][0]), tuple(location[2][0]), (0,255,0), 3)

# === Show Final Output ===
plt.figure(figsize=(10, 6))
plt.imshow(cv2.cvtColor(res, cv2.COLOR_BGR2RGB))
plt.title("Detected License Plate")
plt.axis('off')
plt.show()
