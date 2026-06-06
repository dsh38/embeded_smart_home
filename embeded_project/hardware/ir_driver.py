import os
import time
import json
from config import Config

# pigpio 모듈 라이브러리 로드 예외 처리 (원격 SSH 환경 대비 및 로컬 폴백)
try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False
    print("⚠️ 'pigpio' 모듈을 찾을 수 없습니다. IR 제어는 시뮬레이션 모드로 동작합니다.")

class UniversalACTransmitter:
    def __init__(self):
        self.pi = None
        self.pin = Config.IR_PIN
        self.samsung_signals = self._load_samsung_json()
        
        # pigpio 데몬 연결 시도
        if PIGPIO_AVAILABLE:
            try:
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    print("⚠️ pigpiod 데몬이 실행 중이지 않습니다. 'sudo pigpiod'가 필요합니다. IR 제어 시뮬레이션 모드로 동작합니다.")
                    self.pi = None
                else:
                    self.pi.set_mode(self.pin, pigpio.OUTPUT)
                    print(f"✅ pigpio 연결 성공! IR 송출 핀: GPIO {self.pin}")
            except Exception as e:
                print(f"❌ pigpio 초기화 중 예외 발생: {str(e)}. 시뮬레이션 모드로 작동합니다.")
                self.pi = None
        else:
            print("💡 시뮬레이션 모드 활성화: 실제 IR 신호는 송출되지 않으나 명령은 정상적으로 처리됩니다.")

    def _load_samsung_json(self):
        """삼성 에어컨용 정밀 파형 JSON 파일 로드"""
        filepath = Config.SAMSUNG_SIGNALS_FILE
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ 삼성 에어컨 파형 데이터 로드 완료: {len(data)}개 신호 ({filepath})")
                    return data
            except json.JSONDecodeError:
                print(f"❌ {filepath} 파일 형식이 올바르지 않습니다.")
                return {}
        else:
            print(f"⚠️ {filepath} 파일이 없습니다. 삼성 제어 기능은 시뮬레이션으로만 처리됩니다.")
            return {}
        
    def _create_carrier_pulse(self, duration_us):
        """누적 타이밍 오차를 줄이기 위한 38kHz 캐리어 주파수 펄스 생성"""
        if not self.pi:
            return []
            
        actual_cycle_us = 26  # 13us High + 13us Low = 26us (약 38.4kHz)
        cycles = int(duration_us / actual_cycle_us)
        
        pulses = []
        for _ in range(cycles):
            pulses.append(pigpio.pulse(1 << self.pin, 0, 13))
            pulses.append(pigpio.pulse(0, 1 << self.pin, 13))
        return pulses

    def send_raw_signal(self, time_list):
        """마이크로초(us) 타이밍 리스트를 실제 IR 캐리어 신호로 묶어 송출"""
        if not self.pi:
            print(f"📺 [IR 시뮬레이터] IR 파형 송출 (타이밍 개수: {len(time_list)})")
            return True

        try:
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
                print(f"📡 [IR 물리 송출] 펄스 파형 송출 성공 (wave_id: {wave_id})")
                return True
            else:
                print("❌ IR wave_create 실패!")
                return False
        except Exception as e:
            print(f"❌ IR 물리 송출 실패: {str(e)}")
            return False

    # ==========================================
    # 1. LG 에어컨 알고리즘 구동부
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
    # 2. 삼성 에어컨 데이터 연동 구동부
    # ==========================================
    def send_samsung_command(self, temp, speed):
        """JSON 데이터베이스에서 온도와 바람세기를 조합하여 명령 전송"""
        # UI에서 넘어온 한글 바람세기를 JSON 키 규격에 맞게 변환
        speed_map = {
            'high': 'high',
            'medium': 'middle',
            'low': 'low',
            'auto': 'auto'
        }
        mapped_speed = speed_map.get(speed, 'middle')
        key_name = f"cold_{temp}_{mapped_speed}"
        
        if key_name in self.samsung_signals:
            time_list = self.samsung_signals[key_name]
            print(f"📡 삼성 에어컨 신호 송출 키: {key_name}")
            return self.send_raw_signal(time_list)
        else:
            print(f"❌ 삼성 에어컨 데이터에 '{key_name}' 조합이 존재하지 않습니다.")
            # 만약 해당 온도/세기가 없으면 25도 기준으로 대체 시도 (일반적인 Fallback 제공)
            fallback_key = f"cold_25_{mapped_speed}"
            if fallback_key in self.samsung_signals:
                print(f"⚠️ 대체 신호 송출: {fallback_key}")
                return self.send_raw_signal(self.samsung_signals[fallback_key])
            return False

    def send_samsung_off(self):
        """삼성 에어컨 끄기"""
        if "power_off" in self.samsung_signals:
            print("📡 삼성 에어컨 전원 꺼짐(power_off) 신호 송출")
            return self.send_raw_signal(self.samsung_signals["power_off"])
        elif "power_off_v2" in self.samsung_signals:
            print("📡 삼성 에어컨 전원 꺼짐(power_off_v2) 신호 송출")
            return self.send_raw_signal(self.samsung_signals["power_off_v2"])
        else:
            print("❌ JSON 파일에 전원 끄기(power_off) 신호가 등록되어 있지 않습니다.")
            return False

    def control_ac(self, brand, is_active, mode, target_temp, fan_speed):
        """상위 컨트롤러에서 제조사 구분 없이 하나의 인터페이스로 전송할 수 있는 어댑터 메서드"""
        brand = brand.lower()
        if not is_active:
            # 에어컨 전원 끄기
            if brand == "lg":
                time_list = self.get_lg_ac_off_time_list()
                return self.send_raw_signal(time_list)
            elif brand == "samsung":
                return self.send_samsung_off()
        else:
            # 에어컨 조작/켜기
            if brand == "lg":
                # LG는 기존 코드상 바람세기가 강풍(4)으로 고정되어 온도값만 받음
                time_list = self.generate_lg_ac_on_time_list(target_temp)
                return self.send_raw_signal(time_list)
            elif brand == "samsung":
                return self.send_samsung_command(target_temp, fan_speed)
        return False
        
    def close(self):
        """연결 닫기 및 리소스 회수"""
        if self.pi:
            self.pi.stop()
            self.pi = None
