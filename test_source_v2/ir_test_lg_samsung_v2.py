import pigpio
import time
import json
import os

# 기본 설정
IR_PIN = 18
SAMSUNG_JSON_FILE = "completed_signals.json"

class UniversalACTransmitter:
    def __init__(self, pi, pin):
        self.pi = pi
        self.pin = pin
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.samsung_signals = self._load_samsung_json()
        
    def _load_samsung_json(self):
        """삼성 에어컨용 정밀 파형 JSON 파일 로드"""
        if os.path.exists(SAMSUNG_JSON_FILE):
            try:
                with open(SAMSUNG_JSON_FILE, 'r', encoding='utf-8') as f:
                    print(f"✅ 삼성 에어컨 파형 데이터 로드 완료 ({SAMSUNG_JSON_FILE})")
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"❌ {SAMSUNG_JSON_FILE} 파일 형식이 올바르지 않습니다.")
                return {}
        else:
            print(f"⚠️ {SAMSUNG_JSON_FILE} 파일이 없습니다. 삼성 제어 기능은 비활성화됩니다.")
            return {}
        
    def _create_carrier_pulse(self, duration_us):
        """누적 타이밍 오차를 줄이기 위한 38kHz 캐리어 주파수 펄스 생성"""
        actual_cycle_us = 26  # 13us High + 13us Low = 26us (약 38.4kHz로 수신호환성 최적)
        cycles = int(duration_us / actual_cycle_us)
        
        pulses = []
        for _ in range(cycles):
            pulses.append(pigpio.pulse(1 << self.pin, 0, 13))
            pulses.append(pigpio.pulse(0, 1 << self.pin, 13))
        return pulses

    def send_raw_signal(self, time_list):
        """마이크로초(us) 타이밍 리스트를 실제 IR 캐리어 신호로 묶어 송출"""
        while self.pi.wave_tx_busy():
            time.sleep(0.02)
            
        self.pi.wave_clear()
        full_pulses = []

        for idx, duration in enumerate(time_list):
            if idx % 2 == 0:  # 짝수 인덱스는 Mark (신호 켜짐 + 캐리어 실림)
                full_pulses.extend(self._create_carrier_pulse(duration))
            else:             # 홀수 인덱스는 Space (신호 꺼짐)
                full_pulses.append(pigpio.pulse(0, 1 << self.pin, duration))

        self.pi.wave_add_generic(full_pulses)
        wave_id = self.pi.wave_create()
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.01)
            self.pi.wave_delete(wave_id)

    # ==========================================
    # 1. LG 에어컨 알고리즘 구동부 (기존 로직 보존)
    # ==========================================
    def generate_lg_ac_on_time_list(self, temp):
        n1 = 8; n2 = 8; n3 = 0; n4 = 0
        n5 = temp - 15  
        n6 = 4  # 강풍 고정
        n7 = (n1 + n2 + n3 + n4 + n5 + n6) & 0x0F
        
        code_28bit = (n1 << 24) | (n2 << 20) | (n3 << 16) | (n4 << 12) | (n5 << 8) | (n6 << 4) | n7
        time_list = [8600, 4050]
        
        for i in range(27, -1, -1):
            time_list.append(520)
            if (code_28bit >> i) & 1:
                time_list.append(1560)
            else:
                time_list.append(520)
        time_list.append(520)  
        return time_list

    def get_lg_ac_off_time_list(self):
        code_28bit = 0x88C0051
        time_list = [8600, 4050]
        
        for i in range(27, -1, -1):
            time_list.append(520)
            if (code_28bit >> i) & 1:
                time_list.append(1560)
            else:
                time_list.append(520)
        time_list.append(520)
        return time_list

    # ==========================================
    # 2. 삼성 에어컨 데이터 연동 구동부 (신규 추가)
    # ==========================================
    def send_samsung_command(self, temp, speed):
        """JSON 데이터베이스에서 온도와 바람세기를 조합하여 명령 전송"""
        key_name = f"cold_{temp}_{speed}"
        if key_name in self.samsung_signals:
            time_list = self.samsung_signals[key_name]
            self.send_raw_signal(time_list)
            return True
        else:
            print(f"❌ 삼성 에어컨 데이터에 '{key_name}' 조합이 존재하지 않습니다.")
            return False

    def send_samsung_off(self):
        """삼성 에어컨 끄기 (기존 녹화본에 off 혹은 다른 정적 키가 있다면 매핑 가능)"""
        # 만약 학습 시 'off'라는 키로 저장하셨다면 해당 파형을 쏩니다.
        if "off" in self.samsung_signals:
            self.send_raw_signal(self.samsung_signals["off"])
            return True
        else:
            print("⚠️ JSON 파일에 'off' 신호가 등록되어 있지 않습니다.")
            print("💡 팁: 'ir_record.py'를 켜서 'off'라는 이름으로 끄기 버튼을 하나 녹화해 두시면 완벽히 연동됩니다.")
            return False


def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("pigpiod 데몬을 실행해 주세요! (sudo pigpiod)")
        return

    remocon = UniversalACTransmitter(pi, IR_PIN)

    print("\n" + "="*50)
    print("      LG / SAMSUNG 에어컨 통합 원격 제어 모듈")
    print("="*50)

    while True:
        print("\n[제조사 선택]")
        print("1. LG 휘센 에어컨 제어")
        print("2. 삼성 에어컨 제어 (JSON 데이터 기반)")
        print("0. 프로그램 종료")
        
        brand = input("\n원하는 제조사 번호를 입력하세요: ").strip()
        
        if brand == '0':
            break
            
        # ------------------------------------------
        # LG 에어컨 제어 로직
        # ------------------------------------------
        elif brand == '1':
            print("\n--- [LG 휘센 에어컨 메뉴] ---")
            print("1. 에어컨 켜기 및 온도 설정 (18°C ~ 30°C)")
            print("2. 에어컨 끄기")
            choice = input("동작을 선택하세요: ").strip()
            
            if choice == '1':
                try:
                    temp = int(input("설정할 희망 온도를 입력하세요 (18 ~ 30): "))
                    if 18 <= temp <= 30:
                        print(f"\n>>> LG 휘센 [켜기 및 {temp}°C] 신호 송출...")
                        lg_list = remocon.generate_lg_ac_on_time_list(temp)
                        remocon.send_raw_signal(lg_list)
                        print("송출 완료!")
                    else:
                        print("❌ 18도에서 30도 사이만 입력 가능합니다.")
                except ValueError:
                    print("❌ 숫자를 입력해 주세요.")
            elif choice == '2':
                print("\n>>> LG 휘센 [끄기] 신호 송출...")
                lg_list = remocon.get_lg_ac_off_time_list()
                remocon.send_raw_signal(lg_list)
                print("송출 완료!")

        # ------------------------------------------
        # 삼성 에어컨 제어 로직
        # ------------------------------------------
        elif brand == '2':
            if not remocon.samsung_signals:
                print("❌ 삼성 데이터셋 파일이 없어 접근할 수 없습니다.")
                continue
                
            print("\n--- [삼성 에어컨 메뉴] ---")
            print("1. 에어컨 켜기 및 세부 설정")
            print("2. 에어컨 끄기")
            choice = input("동작을 선택하세요: ").strip()
            
            if choice == '1':
                try:
                    temp = int(input("설정할 희망 온도를 입력하세요 (18 ~ 30): "))
                    if not (18 <= temp <= 30):
                        print("❌ 18도에서 30도 사이만 가능합니다.")
                        continue
                        
                    print("바람세기 선택: high, middle, low, auto")
                    speed = input("바람세기를 입력하세요: ").strip().lower()
                    if speed not in ['high', 'middle', 'low', 'auto']:
                        print("❌ 올바른 바람세기를 입력하세요 (high/middle/low/auto)")
                        continue
                        
                    print(f"\n>>> 삼성 [{temp}°C / 바람세기: {speed}] 복합 신호 송출...")
                    if remocon.send_samsung_command(temp, speed):
                        print("송출 완료!")
                except ValueError:
                    print("❌ 올바른 온도를 숫자로 입력해 주세요.")
                    
            elif choice == '2':
                print("\n>>> 삼성 [끄기] 신호 송출...")
                if remocon.send_samsung_off():
                    print("송출 완료!")

    print("\n프로그램을 종료합니다.")
    pi.stop()

if __name__ == "__main__":
    main()