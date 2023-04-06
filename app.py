import io
from operator import truediv
import os
import json
from PIL import Image
import cv2
import torch
from flask import Flask, jsonify, url_for, render_template, request, redirect
from flask import Flask, render_template, Response, stream_with_context, Request
import csv
import sqlite3
import time
import datetime
from word.chatbot import Chatbot

video = cv2.VideoCapture(0)
app = Flask(__name__)
chatbot = Chatbot()

RESULT_FOLDER = os.path.join('static')
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# 모델찾는 함수, 디렉토리에 하나의 모델만


def find_model():
    for f in os.listdir():
        if f.endswith(".pt"):
            return f


# 모델 불러오기
model_name = find_model()
model = torch.hub.load('../yolov7', 'custom', model_name, source='local')
model.eval()

# sqlite db에 'test.db' 생성하고 연결
conn = sqlite3.connect("test.db", isolation_level=None,
                       check_same_thread=False)
curs = conn.cursor()
curs.execute(  # detected 라는 table이 없으면 생성
    "CREATE TABLE IF NOT EXISTS detected (xmin, ymin, xmax, ymax, confidence, label TEXT, name TEXT, time)")

# db저장 함수


def save_to_db(to_db, time):
    time_str = datetime.datetime.fromtimestamp(time).strftime(
        '%Y-%m-%d %H:%M:%S')  # 시간데이터 yyyy-mm-dd hh-mm-ss 형태로
    # detected table에 저장
    curs.execute(
        "INSERT INTO detected (xmin, ymin, xmax, ymax, confidence, label, name, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (to_db[0], to_db[1], to_db[2], to_db[3], to_db[4], to_db[5], to_db[6], time_str))
    conn.commit()

# 실시간 웹캠 실행, 모델실행, 결과저장 함수


def video_stream():
    prev_time = 0
    FPS = 30  # 1초에 30번
    db_save_interval = 1  # DB에 저장되는 간격을 설정 1초마다
    db_save_time = 0  # DB 저장시간 초기화

    while True:
        ret, frame = video.read()
        if not ret:
            break
        else:
            current_time = time.time() - prev_time
            if current_time > 1/FPS:  # 1/30초마다
                results = model(frame)
                annotated_frame = results.render()

                # 결과에서 bounding box 정보 추출
                df = results.pandas().xyxy[0]

                # bounding box 레이블을 데이터베이스에 저장
                for i in range(len(df)):
                    to_db = df.iloc[i].tolist()
                    to_db[5] = to_db[5].astype('str')  # numpy array를 문자열로 변환
                    if to_db[5] == '0':
                        pass
                    else:
                        if time.time() - db_save_time > db_save_interval:
                            save_to_db(to_db, time.time())
                            db_save_time = time.time()  # 저장시간 업데이트

                ret, buffer = cv2.imencode('.jpeg', frame)
                frame = buffer.tobytes()

                yield (b'--frame\r\n' b'Content-type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                prev_time = time.time()  # 이전 프레임처리 시간을 현재시간으로 업데이트

    conn.close()

# 이미지 분석


def get_prediction(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    imgs = [img]  # batched list of images
# Inference
    results = model(imgs, size=640)  # includes NMS
    return results

# 메인화면


@app.route('/', methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files.get('file')
        if not file:
            return

        img_bytes = file.read()
        results = get_prediction(img_bytes)
        results.save(save_dir='static')
        filename = 'image0.jpg'

        return render_template('result.html', result_image=filename, model_name=model_name)

    return render_template('index.html')

# /webcam_feed 에서 실행됨 - streaming.html에서 실행됨


@app.route("/video_feed")
def video_feed():
    return Response(video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
# multipart/x-mixed-replace : 클라이언트가 하나의 요청으로 여러개의 응답을 받을 수 있게 해주는 multipart 응답형식
# boundary : 각 응답들을 구분할 구분자를 설정하는 것

# 웹캠버튼 누르면 streaming.html 실행


@app.route("/webcam_feed")
def webcam_feed():
    return render_template("streaming.html")


@app.route('/chatting')
def chatting():
    return render_template('chatting.html')


@app.route('/chat', methods=['POST'])
def chat():
    req = request.form['req']
    res = chatbot.chat_rule(req)
    return res


@app.route('/get_data', methods=['GET'])
def get_data():
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute('SELECT label, time FROM detected')
    rows = c.fetchall()
    result = []
    for row in rows:
        result.append({'label': row[0], 'time': row[1]})
    return json.dumps(result)


if __name__ == "__main__":
    app.run(debug=True)
