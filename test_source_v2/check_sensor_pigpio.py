import time
import pigpio
import DHT

# 1. pigpio 데몬 연결
pi = pigpio.pi()
if not pi.connected:
    print("pigpiod 데몬이 실행 중인지 확인하세요 (sudo systemctl start pigpiod)")
    exit()

# 2. 센서 객체 생성 (GPIO 18번 핀, 모델 DHT22(DHTXX) 지정)
# DHT.py 라이브러리 내부 상수를 사용합니다.
sensor = DHT.sensor(pi, 4, model=DHT.DHTXX)

print("--- pigpio 정밀 측정 시작 (종료: Ctrl+C) ---")

try:
    while True:
        # read() 메서드가 신호를 트리거하고 결과를 바로 반환합니다.
        timestamp, gpio, status, temp, hum = sensor.read()
        
        # status가 0(DHT_GOOD)일 때만 정상 데이터입니다.
        if status == DHT.DHT_GOOD:
            print(f"[{time.strftime('%H:%M:%S')}] 온도: {temp:0.1f}°C | 습도: {hum:0.1f}%")
        elif status == DHT.DHT_TIMEOUT:
            print("응답 시간 초과: 연결을 확인하세요.")
        elif status == DHT.DHT_BAD_CHECKSUM:
            print("체크섬 오류: 데이터가 깨졌습니다. (일시적 현상일 수 있음)")
        else:
            print(f"기타 오류 (Status: {status}): 측정 중...")

        # DHT11의 물리적 한계로 최소 2초 간격을 유지해야 합니다.
        time.sleep(2.0)

except KeyboardInterrupt:
    print("\n측정 종료")
finally:
    sensor.cancel()
    pi.stop()