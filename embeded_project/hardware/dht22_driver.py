import time
import random
from config import Config

# pigpio 및 DHT 모듈 라이브러리 동적 로드 (로컬/원격 호환)
PIGPIO_AVAILABLE = False
DHT_AVAILABLE = False

try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    print("⚠️ 'pigpio' 모듈을 찾을 수 없습니다. DHT22는 시뮬레이션 모드로 작동합니다.")

try:
    import DHT
    DHT_AVAILABLE = True
except ImportError:
    print("⚠️ 'DHT' (pigpio 기반) 모듈을 찾을 수 없습니다. DHT22는 시뮬레이션 모드로 작동합니다.")

class DHT22SensorReader:
    def __init__(self):
        self.pi = None
        self.sensor = None
        self.pin = Config.DHT_PIN
        
        # 캐싱 및 시뮬레이션 기본 데이터 세팅
        self.last_temp = 24.5
        self.last_humi = 52.0
        
        # 하드웨어 초기화 시도
        self._initialize_hardware()

    def _initialize_hardware(self):
        if PIGPIO_AVAILABLE and DHT_AVAILABLE:
            try:
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    print("⚠️ [DHT22] pigpiod 데몬에 연결하지 못했습니다. 시뮬레이션 모드로 동작합니다.")
                    self.pi = None
                    return
                    
                # DHT.py 객체 생성 (GPIO 핀, DHTXX 모델 지정)
                # DHT.DHTXX는 DHT22 및 AM2302 계열 센서를 의미합니다.
                self.sensor = DHT.sensor(self.pi, self.pin, model=DHT.DHTXX)
                print(f"✅ [DHT22] pigpio DHT22 물리 센서 드라이버가 GPIO {self.pin} 핀에 등록되었습니다.")
            except Exception as e:
                print(f"❌ [DHT22] 센서 물리 초기화 실패: {str(e)}. 시뮬레이션 모드로 동작합니다.")
                self.pi = None
                self.sensor = None
        else:
            print("💡 [DHT22] 시뮬레이션 센서 모드가 활성화되었습니다. 가상 온습도가 실시간 생성됩니다.")

    def read_data(self):
        """온도와 습도를 읽어서 (temperature, humidity) 튜플 반환. 실패 시 캐싱된 값 또는 가상 데이터 반환."""
        if self.sensor and self.pi:
            try:
                # DHT 센서 물리 값 읽기
                # timestamp, gpio, status, temp, hum = sensor.read()
                timestamp, gpio, status, temp, hum = self.sensor.read()
                
                # status가 0 (DHT.DHT_GOOD) 일 때만 유효한 측정 데이터입니다.
                if status == DHT.DHT_GOOD:
                    self.last_temp = round(temp, 1)
                    self.last_humi = round(hum, 1)
                    return self.last_temp, self.last_humi
                
                # TIMEOUT 이나 CHECKSUM 에러가 날 경우 이전 캐싱 데이터 반환 (화면의 출렁거림 방지)
                elif status == DHT.DHT_TIMEOUT:
                    print(f"⚠️ [DHT22] 센서 타임아웃 오류 (Status: {status}). 직전 값({self.last_temp}°C / {self.last_humi}%)을 유지합니다.")
                elif status == DHT.DHT_BAD_CHECKSUM:
                    print(f"⚠️ [DHT22] 센서 체크섬 불량 오류 (Status: {status}). 직전 값({self.last_temp}°C / {self.last_humi}%)을 유지합니다.")
                else:
                    print(f"⚠️ [DHT22] 센서 기타 상태 코드 오류 (Status: {status}). 직전 값({self.last_temp}°C / {self.last_humi}%)을 유지합니다.")
                
                return self.last_temp, self.last_humi
            except Exception as e:
                print(f"❌ [DHT22] 센서 데이터 획득 물리적 예외: {str(e)}")
                return self.last_temp, self.last_humi
        
        # ---------------------------------------------
        # Fallback: 시뮬레이션 모드 (Mock Data Generator)
        # ---------------------------------------------
        temp_delta = random.choice([-0.2, -0.1, 0.0, 0.1, 0.2])
        humi_delta = random.choice([-0.5, -0.2, 0.0, 0.2, 0.5])
        
        self.last_temp = round(max(18.0, min(32.0, self.last_temp + temp_delta)), 1)
        self.last_humi = round(max(30.0, min(80.0, self.last_humi + humi_delta)), 1)
        
        return self.last_temp, self.last_humi

    def close(self):
        """리소스 정리"""
        if self.sensor:
            try:
                self.sensor.cancel()
                print("🧹 [DHT22] 센서 콜백 리소스 정리 완료")
            except Exception:
                pass
            self.sensor = None
            
        if self.pi:
            try:
                self.pi.stop()
                print("🧹 [DHT22] pigpio 연결 해제 완료")
            except Exception:
                pass
            self.pi = None

    def __del__(self):
        self.close()
