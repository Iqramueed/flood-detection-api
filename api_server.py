# -*- coding: utf-8 -*-
"""api_server.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Rm0Irxbk8QgBndOl1uZyJk_x0bMiHr5Z
"""

from flask import Flask, jsonify
import cv2
import numpy as np
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

app = Flask(__name__)

latest_alert = {'water_height': 0, 'status': 'NORMAL'}

# Email Configuration
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "iqramueed3@gmail.com"
sender_password = "kojuvflliazkwzku"  # App Password from Google
recipient_emails = ["iqra.mueed@giki.edu.pk"]

@app.route('/latest_alert', methods=['GET'])
def get_latest_alert():
    return jsonify(latest_alert)

def get_vertical_patches(image, patch_width, overlap):
    patches = []
    _, img_width = image.shape[:2]
    step_x = patch_width - overlap
    for x in range(0, img_width - patch_width + 1, step_x):
        patch = image[:, x:x + patch_width]
        patches.append(patch)
    if (img_width - patch_width) % step_x != 0:
        patch = image[:, img_width - patch_width:img_width]
        patches.append(patch)
    return patches

def calculate_water_height_from_bottom(strip, water_intensity_range=(70, 255)):
    lower, upper = water_intensity_range
    water_mask = cv2.inRange(strip, lower, upper)
    water_height = 0
    for i in range(len(water_mask) - 1, -1, -1):
        if water_mask[i] > 0:
            water_height += 1
        else:
            break
    return water_height

def pixels_to_meters(pixels, pixels_per_meter=111.93):
    return pixels / pixels_per_meter

def send_email_alert(water_height):
    message = MIMEMultipart("alternative")
    message["Subject"] = "🚨 Flood Alert: Water Level Exceeded Threshold!"
    message["From"] = sender_email
    message["To"] = ", ".join(recipient_emails)

    text = f"""
    URGENT: The flood detection system detected a water height of {water_height:.2f} meters,
    which exceeds the safe threshold. Immediate action is recommended.
    """
    html = f"""
    <html>
      <body>
        <h2>🚨 Flood Alert</h2>
        <p><strong>Water Level:</strong> {water_height:.2f} meters</p>
        <p style='color:red;'>Immediate action is recommended.</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, message.as_string())
        print("✅ Email alert sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def flood_detection():
    global latest_alert
    rtsp_url = "rtsp://admin:khan@321@10.1.139.235:554/Streaming/Channels/101"
    cap = cv2.VideoCapture(rtsp_url)
    threshold = 6  # meters

    if not cap.isOpened():
        print("Failed to open video stream.")
        return

    print("Live flood detection started...")

    patch_width, overlap = 50, 25
    K, attempts = 8, 50
    water_intensity_range = (50, 255)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    pixels_per_meter = 111.93

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        vertical_patches = get_vertical_patches(img, patch_width, overlap)
        max_height_meters = 0

        for patch in vertical_patches:
            vectorized = patch.reshape((-1, 1)).astype(np.float32)
            _, label, center = cv2.kmeans(vectorized, K, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
            res = center[label.flatten()]
            result_image = res.reshape((patch.shape))
            strip = np.array(result_image).mean(axis=1)

            water_height_pixels = calculate_water_height_from_bottom(strip, water_intensity_range)
            water_height_meters = pixels_to_meters(water_height_pixels, pixels_per_meter)

            if water_height_meters > max_height_meters:
                max_height_meters = water_height_meters

        if max_height_meters > threshold:
            latest_alert['water_height'] = round(max_height_meters, 2)
            latest_alert['status'] = 'FLOOD ALERT 🚨'
            send_email_alert(max_height_meters)
        else:
            latest_alert['water_height'] = round(max_height_meters, 2)
            latest_alert['status'] = 'NORMAL'

        print(f"Live Water Height: {max_height_meters:.2f} m | Status: {latest_alert['status']}")
        time.sleep(1)

    cap.release()

if __name__ == '__main__':
    detection_thread = threading.Thread(target=flood_detection)
    detection_thread.daemon = True
    detection_thread.start()

    app.run(host='0.0.0.0', port=5000)