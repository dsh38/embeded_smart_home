import os

class Config:
    # Flask 비밀키 (세션 서명용)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smarthome_iot_secure_session_key_9f3c1a2'
    
    # 데이터 파일 경로 설정
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
    
    # 삼성 에어컨 파형 파일 명칭 (기존 recorded_signals.json 사용)
    SAMSUNG_SIGNALS_FILE = os.path.join(BASE_DIR, 'recorded_signals.json')
    
    # 하드웨어 핀 설정
    IR_PIN = 18
    DHT_PIN = 4 # DHT22 기본 GPIO 핀 번호
    I2C_ADDR = 0x27 # I2C 1602 LCD 기본 주소 (보통 0x27 또는 0x3f)
    
    # 접속 도메인 주소 설정
    # 사용자가 도메인을 지정(예: 'example.com')하면 해당 주소가 LCD에 우선 표기되고,
    # None 또는 빈 값으로 지정 시 기기의 공인 IP 또는 로컬 LAN IP를 자동 감지하여 표기합니다.
    SYSTEM_URL = None
    
    # 웹 서버 구동 포트 설정
    PORT = 5000
    
    # 자동 로그인 세션 만료 기간 (30일)
    PERMANENT_SESSION_LIFETIME = 2592000
