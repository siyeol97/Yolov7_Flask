import io
from operator import truediv
import os
import json
from PIL import Image
import cv2
import torch
from flask import Flask, jsonify, url_for, render_template, request, redirect, session, flash
from flask import Flask, render_template, Response, stream_with_context, Request
import csv
import sqlite3
import time
import datetime
from word.chatbot import Chatbot
from collections import defaultdict
import torch.nn as nn
from flask_sqlalchemy import SQLAlchemy

video = cv2.VideoCapture(0)
app = Flask(__name__)
chatbot = Chatbot()

RESULT_FOLDER = os.path.join('static')
app.config['RESULT_FOLDER'] = RESULT_FOLDER


def find_model():  # 모델찾는 함수, 디렉토리에 하나의 모델만
    for f in os.listdir():
        if f.endswith(".pt"):
            return f


model_name = find_model()  # 모델 불러오기
model = torch.hub.load('./yolov7', 'custom',
                       model_name, source='local')
model.eval()


conn = sqlite3.connect("test.db", isolation_level=None,
                       check_same_thread=False)  # sqlite db에 'test.db' 생성하고 연결
curs = conn.cursor()
curs.execute(  # detected 라는 table이 없으면 생성
    "CREATE TABLE IF NOT EXISTS detected (xmin, ymin, xmax, ymax, confidence, label TEXT, name TEXT, time)")


def save_to_db(to_db, time):  # db저장 함수
    time_str = datetime.datetime.fromtimestamp(time).strftime(
        '%Y-%m-%d %H:%M:%S')  # 시간데이터 yyyy-mm-dd hh-mm-ss 형태로
    # detected table에 저장
    curs.execute(
        "INSERT INTO detected (xmin, ymin, xmax, ymax, confidence, label, name, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (to_db[0], to_db[1], to_db[2], to_db[3], to_db[4], to_db[5], to_db[6], time_str))
    conn.commit()


def video_stream():  # 실시간 웹캠 실행, 모델실행, 결과저장 함수
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


def get_prediction(img_bytes):  # 이미지 분석
    img = Image.open(io.BytesIO(img_bytes))
    imgs = [img]  # batched list of images
    results = model(imgs, size=640)  # includes NMS
    return results


@app.route('/home', methods=['GET', 'POST'])  # 홈화면
def predict():
    if 'logFlag' not in session or not session['logFlag']:
        flash('로그인이 필요합니다')
        return redirect(url_for('login_form'))

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


@app.route("/video_feed")  # /webcam_feed 에서 실행됨 - streaming.html에서 실행됨
def video_feed():
    return Response(video_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
# multipart/x-mixed-replace : 클라이언트가 하나의 요청으로 여러개의 응답을 받을 수 있게 해주는 multipart 응답형식
# boundary : 각 응답들을 구분할 구분자를 설정하는 것


@app.route("/webcam_feed")  # 웹캠버튼 누르면 streaming.html 실행
def webcam_feed():
    return render_template("streaming.html")


@app.route('/chatting')  # 챗봇 화면
def chatting():
    return render_template('chatting.html')


@app.route('/chatting_test')
def chatting_test():
    return render_template('chatting_test.html')


@app.route('/chat', methods=['POST'])  # 챗봇 동작
def chat():
    req = request.form['req']
    res = chatbot.chat_rule(req)

    # 채팅 로그 db저장
    conn = sqlite3.connect('test.db')
    curs = conn.cursor()
    curs.execute(  # chatlog 라는 table이 없으면 생성
        "CREATE TABLE IF NOT EXISTS chatlog (chat TEXT, time)")
    time_str = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y-%m-%d %H:%M:%S')
    curs.execute(
        "INSERT INTO chatlog (chat, time) VALUES (?, ?);",
        (req, time_str))
    conn.commit()

    return res


@app.route('/get_data', methods=['GET'])  # 챗봇에 요청하면, db에서 데이터 가져오는 부분
def get_data():
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    c.execute('SELECT name, confidence, time FROM detected')
    rows = c.fetchall()
    result = []
    for row in rows:
        result.append({'name': row[0], 'confidence': row[1], 'time': row[2]})
    return json.dumps(result)


@app.route('/detectResult', methods=['GET', 'POST'])  # 챗봇에 요청하면, 데이터 띄워주는 부분
def detect_result():
    if request.method == 'POST':
        global detected
        detected = request.json
        return render_template('detectResult.html', detected=detected)
    else:
        return render_template('detectResult.html', detected=detected)


@app.route('/regist_user')  # 회원가입 페이지
def regist_user():
    return render_template('regist_user.html')


@app.route('/regist_submit', methods=['POST'])  # 회원가입 버튼 누르면 실행되는 과정
def submit():
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    regist_time = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y-%m-%d %H:%M:%S')

    curs.execute(  # member 라는 table이 없으면 생성
        "CREATE TABLE IF NOT EXISTS member (userID, userPWD, userEmail, registTime)")

    # username이 입력되지 않았을 경우
    if not username:
        flash('아이디를 입력해 주세요.')
        return redirect(url_for('regist_user'))

    # id 중복검사
    curs.execute("SELECT * FROM member WHERE userID=?", (username,))
    user = curs.fetchone()
    if user is not None:
        flash('중복된 아이디입니다.')
        return redirect(url_for('regist_user'))

    # password가 입력되지 않았을 경우
    if not password:
        flash('비밀번호를 입력해 주세요.')
        return redirect(url_for('regist_user'))

    # email이 입력되지 않았을 경우
    if not email:
        flash('이메일을 입력해 주세요.')
        return redirect(url_for('regist_user'))

    curs.execute(  # member table에 저장
        "INSERT INTO member (userID, userPWD, userEmail, registTime) VALUES (?, ?, ?, ?);",
        (username, password, email, regist_time))
    conn.commit()

    flash('회원가입이 완료되었습니다.')
    return redirect(url_for('login_form'))


@app.route('/main')
def main():
    return render_template('main.html')


@app.route('/')  # 로그인 페이지, 첫화면
def login_form():
    return render_template('login/login_form.html')


@app.route('/login_proc', methods=['POST'])  # 로그인 버튼 누르면 실행되는 과정
def login_proc():
    if request.method == 'POST':
        userId = request.form['id']
        userPwd = request.form['pwd']
        if len(userId) == 0 or len(userPwd) == 0:
            flash('아이디를 입력해주세요')
            return redirect(url_for('login_form'))
        else:
            conn = sqlite3.connect('test.db')
            cursor = conn.cursor()
            sql = 'select userID, userPWD, userEmail from member where userId = ?'
            cursor.execute(sql, (userId, ))
            rows = cursor.fetchall()
            for rs in rows:
                if userId == rs[0] and userPwd == rs[1]:
                    session['logFlag'] = True
                    session['userId'] = userId
                    return redirect(url_for('predict'))

            flash('로그인에 실패했습니다. 아이디 또는 비밀번호를 확인해주세요.')
            return redirect(url_for('login_form'))  # 메소드를 호출
    else:
        return '잘못된 접근입니다.'


@app.route('/user_info_edit/<userId>', methods=['GET'])  # 사용자 정보 수정 페이지
def getUser(userId):
    if session.get('logFlag') != True:
        return redirect('login_form')

    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    sql = 'select userEmail from member where userId = ?'
    cursor.execute(sql, (userId,))
    row = cursor.fetchone()
    edit_email = row[0]
    cursor.close()
    conn.close()
    return render_template('users/user_info.html', userId=userId, edit_email=edit_email)


# 사용자 정보 수정 버튼 누르면 실행되는 과정
@app.route('/user_info_edit_proc', methods=['POST'])
def user_info_edit_proc():
    userId = request.form['userId']
    userPwd = request.form['userPwd']
    userEmail = request.form['userEmail']

    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    sql = 'update member set userPwd = ?, userEmail = ? where userId = ?'
    cursor.execute(sql, (userPwd, userEmail, userId))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('predict'))


@app.route('/logout')  # 로그아웃
def logout():
    session.clear()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('login_form'))


@app.route('/chart')  # 차트 최초 접속
def chart():
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()

    # 각 불량 종류별로 발생 횟수를 계산
    cur.execute("SELECT name, COUNT(*) FROM detected GROUP BY name")
    rows = cur.fetchall()

    # 도넛차트를 위한 데이터 생성
    chart_data = []
    for row in rows:
        chart_data.append({'name': row[0], 'value': row[1]})

    # 1시간 단위로 발생한 불량 건수 계산
    cur.execute("SELECT time FROM detected ORDER BY time ASC")
    rows = cur.fetchall()
    hour_dict = defaultdict(int)
    for row in rows:
        time_str = row[0]
        time_obj = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        hour = time_obj.replace(minute=0, second=0, microsecond=0)
        hour_dict[hour] += 1

    # 꺾은선 그래프를 위한 데이터 생성
    line_data = []
    for hour, count in hour_dict.items():
        line_data.append({'time': hour.strftime(
            '%Y-%m-%d %H:%M:%S'), 'count': count})

    return render_template('chart.html', chart_data=chart_data, line_data=line_data)


@app.route('/data1')  # 1초마다 반영
def data1():
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()

    # 각 불량 종류별로 발생 횟수를 계산
    cur.execute("SELECT name, COUNT(*) FROM detected GROUP BY name")
    rows = cur.fetchall()

    # 도넛차트를 위한 데이터 생성
    chart_data = []
    for row in rows:
        chart_data.append({'name': row[0], 'value': row[1]})

    return jsonify(chart_data)


@app.route('/data2')  # 1초마다 반영
def data2():
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()

    # 1시간 단위로 발생한 불량 건수 계산
    cur.execute("SELECT time FROM detected ORDER BY time ASC")
    rows = cur.fetchall()
    hour_dict = defaultdict(int)
    for row in rows:
        time_str = row[0]
        time_obj = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        hour = time_obj.replace(minute=0, second=0, microsecond=0)
        hour_dict[hour] += 1

    # 꺾은선 그래프를 위한 데이터 생성
    line_data = []
    for hour, count in hour_dict.items():
        line_data.append({'time': hour.strftime(
            '%Y-%m-%d %H:%M:%S'), 'count': count})

    return jsonify(line_data)


#######################################기계이상 탐지############################################
RESULT_FOLDER = os.path.join('static')
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/pknu_web/sf5/sf5app/sf5_database.db'
db = SQLAlchemy(app)


# 기계이상 탐지
class test(db.Model):
    index = db.Column(db.Integer, primary_key=True)
    sensor1 = db.Column(db.Integer)
    sensor2 = db.Column(db.Integer)
    sensor3 = db.Column(db.Integer)
    sensor4 = db.Column(db.Integer)

    def __init__(self, index=1, sensor1=None, sensor2=None, sensor3=None, sensor4=None):
        self.index = index
        self.sensor1 = sensor1
        self.sensor2 = sensor2
        self.sensor3 = sensor3
        self.sensor4 = sensor4

    def __repr__(self):
        return '<%r, %r, %r, %r>' % (self.sensor1, self.sensor2, self.sensor3, self.sensor4)


class KAMP_DNN(nn.Module):
    # __init__(self): initialize; 내가 사용하고 싶은, 내 신경망 모델에 사용될 구성품들을 정의 및 초기화 하는 메소드
    def __init__(self):
        super(KAMP_DNN, self).__init__()
        # nn.Linear(): 선형계층으로 weight와 bias을 사용하여 선형 변환을 적용하는 모듈
        self.layer1 = nn.Linear(in_features=4, out_features=100)
        self.layer2 = nn.Linear(in_features=100, out_features=100)
        self.layer3 = nn.Linear(in_features=100, out_features=100)
        self.layer4 = nn.Linear(in_features=100, out_features=4)

        self.dropout = nn.Dropout(0.2)
        self.relu = nn.ReLU()

    def forward(self, input):
        out = self.layer1(input)
        out = self.relu(out)
        out = self.dropout(out)

        out = self.layer2(out)
        out = self.relu(out)
        out = self.dropout(out)

        out = self.layer3(out)
        out = self.relu(out)
        out = self.dropout(out)

        out = self.layer4(out)
        return out


def read_row():  # 머신러닝 위한 행 불러오기
    conn = sqlite3.connect("my_database.db")
    c = conn.cursor()
    c.execute('SELECT * FROM test')
    row = c.fetchone()  # 첫 번째 행을 읽어옴
    conn.close()
    ret = list(row[1:5])
    return ret


@app.route("/machpred")
def machpred():
    # 임시 데이터
    file = torch.as_tensor([read_row()])

    # 데이터 전처리

    # 가중치 불러오기
    model = torch.load('./model.pt')
    model.eval()

    # 예측
    t_hat = model(file)
    _, predicted = torch.max(t_hat.data, dim=1)

    sort = ["정상상태", "질량불균형 고장상태", "지지불량 고장상태", "질량불균형과 지지불량 고장상태"]

    result = sort[int(predicted)]

    return (result)


if __name__ == '__main__':
    app.secret_key = '19970128'
    app.debug = True
    #app.run(host='0.0.0.0', port=9900)
    app.run()
