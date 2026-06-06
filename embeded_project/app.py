import os
import time
import threading
import atexit
from flask import Flask, render_template, redirect, url_for, session
from config import Config
from models.auth_model import AuthModel
from hardware.i2c_lcd_driver import I2CLcd1602

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Cloudflare Tunnel(프록시) 환경 대응: X-Forwarded-For 헤더를 실제 request.remote_addr로 복원
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

app.config.from_object(Config)
app.debug = True

# 데이터 디렉토리 및 초기 설정 파일 로드
AuthModel.initialize_config()

# 블루프린트 등록
from controllers.auth_controller import auth_bp
from controllers.device_controller import device_bp
from controllers.sensor_controller import sensor_bp

app.register_blueprint(auth_bp)
app.register_blueprint(device_bp)
app.register_blueprint(sensor_bp)

import urllib.request
import socket

# I2C 1602 LCD 백그라운드 구동 변수 정의
lcd = I2CLcd1602()
lcd_active = True
lcd_thread = None

def get_system_address():
    """접속 주소 결정 (1순위: Config 설정 도메인, 2순위: 외부 공인 IP, 3순위: 로컬 LAN IP - 포트 정보 결합)"""
    if Config.SYSTEM_URL:
        return Config.SYSTEM_URL
        
    ip_addr = "No Network IP"
    # 외부 공인 IP 확인 시도 (2초 타임아웃)
    try:
        req = urllib.request.Request('https://api.ipify.org', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            public_ip = response.read().decode('utf-8').strip()
            if public_ip:
                ip_addr = public_ip
    except Exception:
        # 로컬 LAN IP 확인 시도
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) # DNS 주소로 임시 바인드
            local_ip = s.getsockname()[0]
            s.close()
            ip_addr = local_ip
        except Exception:
            pass
            
    if ip_addr != "No Network IP":
        # IP 주소 뒤에 Flask 가동 포트 자동 결합 (예: 192.168.0.1:5000)
        return f"{ip_addr}:{Config.PORT}"
    return ip_addr

def lcd_loop():
    """I2C 1602 LCD 3초 순환 표기용 백그라운드 스레드 루프"""
    global lcd_active
    from controllers.sensor_controller import dht_reader
    
    # 3초 순환 상태 카운터
    display_state = 0
    
    # 기동 시 초기 On 상태 표기
    lcd.display_string("Smart Home Iot", 1)
    
    while lcd_active:
        try:
            if display_state == 0:
                # 1번째 화면: 프로젝트 이름 + 온습도 데이터 (24.5C 52.0%)
                temp, humi = dht_reader.read_data()
                if temp is not None and humi is not None:
                    lcd.display_string("Smart Home Iot", 1)
                    lcd.display_string(f"{temp:0.1f}C {humi:0.1f}%", 2)
                else:
                    lcd.display_string("Smart Home Iot", 1)
                    lcd.display_string("Sensor Glitch", 2)
                display_state = 1
                
                # 3초 동안 대기하면서 lcd_active 해제 반응성을 높이기 위해 0.1초씩 분할 대기
                for _ in range(30):
                    if not lcd_active:
                        break
                    time.sleep(0.1)
            else:
                # 2번째 화면: 프로젝트 이름 + 접속 주소 (자동 룩업 IP 또는 도메인)
                addr = get_system_address()
                if len(addr) <= 16:
                    lcd.display_string("Smart Home Iot", 1)
                    lcd.display_string(addr, 2)
                    # 3초 동안 대기
                    for _ in range(30):
                        if not lcd_active:
                            break
                        time.sleep(0.1)
                else:
                    # 16자를 초과하는 경우: 좌우 스크롤(Marquee) 작동
                    L = len(addr)
                    max_step = L - 16
                    for step in range(max_step + 1):
                        if not lcd_active:
                            break
                        window = addr[step:step+16]
                        lcd.display_string("Smart Home Iot", 1)
                        lcd.display_string(window, 2)
                        
                        # 대기 시간 설정 (시작 시점 1.0초, 끝 지점 1.5초, 이동 중 0.35초)
                        if step == 0:
                            delay = 1.0
                        elif step == max_step:
                            delay = 1.5
                        else:
                            delay = 0.35
                            
                        # 반응성 있는 분할 대기 (0.05초 단위)
                        sub_steps = int(delay / 0.05)
                        for _ in range(sub_steps):
                            if not lcd_active:
                                break
                            time.sleep(0.05)
                display_state = 0
        except Exception as e:
            print(f"⚠️ [I2C LCD] 디스플레이 루프 예외 발생: {str(e)}")
            time.sleep(1.0)
            
    # 서버 기동 해제 시 (Off 상태로 이행)
    try:
        lcd.display_string("Smart Home Iot", 1)
        lcd.display_string("System offline", 2)
        print("🔌 [I2C LCD] LCD에 System offline 출력 완료.")
    except Exception:
        pass

def cleanup():
    """애플리케이션 종료 시 백그라운드 스레드 중단 및 리소스 회수 후크"""
    global lcd_active, lcd_thread
    print("🧹 [Cleanup] LCD 백그라운드 스레드 및 I2C 리소스를 해제합니다.")
    lcd_active = False
    if lcd_thread:
        lcd_thread.join(timeout=1.0)

# Flask 종료 시 리소스 자동 회수 등록
atexit.register(cleanup)

@app.route('/')
def index():
    """메인 경로: 로그인 유무에 따라 대시보드 또는 로그인 페이지로 이동"""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """로그인 페이지 렌더링"""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """메인 대시보드 패널 렌더링"""
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')

@app.route('/devices/<int:device_id>')
def device_detail(device_id):
    """기기 제어 상세 패널 렌더링"""
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template('device_detail.html', device_id=device_id)

if __name__ == '__main__':
    # Flask 디버그 리로더에 의한 이중 구동 방지 검사 후 스레드 실행
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        lcd_thread = threading.Thread(target=lcd_loop)
        lcd_thread.daemon = True
        lcd_thread.start()
        print("🚀 [I2C LCD] 백그라운드 LCD 롤링 데몬 스레드가 활성화되었습니다.")
        
    # 0.0.0.0 호스트로 실행하여 동일 네트워크상의 모바일/PC에서 접속 가능하도록 설정
    app.run(host='0.0.0.0', port=Config.PORT, debug=True)
