import pigpio
import time

# 기본 설정
IR_PIN = 18 
FREQ = 38000 

class PI_IRTransmitter:
    def __init__(self, pi, pin):
        self.pi = pi
        self.pin = pin
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        
    def _create_carrier_pulse(self, duration_us):
        cycle = 1000000 / FREQ
        cycles = int(duration_us / cycle)
        pulses = []
        for _ in range(cycles):
            pulses.append(pigpio.pulse(1 << self.pin, 0, int(cycle / 2)))
            pulses.append(pigpio.pulse(0, 1 << self.pin, int(cycle / 2)))
        return pulses

    def send_nec_code(self, address, command):
        self.pi.wave_clear()
        full_pulses = []

        # NEC 헤더
        full_pulses.extend(self._create_carrier_pulse(9000))
        full_pulses.append(pigpio.pulse(0, 1 << self.pin, 4500))

        # 데이터 구성 (Address + Inv_Addr + Command + Inv_Cmd)
        addr_data = address | ((~address & 0xFF) << 8)
        cmd_data = command | ((~command & 0xFF) << 8)
        
        for data in [addr_data, cmd_data]:
            for i in range(16):
                full_pulses.extend(self._create_carrier_pulse(560))
                if data & (1 << i):
                    full_pulses.append(pigpio.pulse(0, 1 << self.pin, 1690))
                else:
                    full_pulses.append(pigpio.pulse(0, 1 << self.pin, 560))

        full_pulses.extend(self._create_carrier_pulse(560)) # 종료 펄스

        self.pi.wave_add_generic(full_pulses)
        wave_id = self.pi.wave_create()
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.01)
            self.pi.wave_delete(wave_id)

# 테스트 후보 리스트
TV_CANDIDATES = [
    {'name': 'LG 계열', 'addr': 0x04, 'cmd': 0x08},
    {'name': '삼성 계열', 'addr': 0x07, 'cmd': 0x02},
    {'name': '중소기업 표준 1 (0x12)', 'addr': 0x00, 'cmd': 0x12}, # 
    {'name': '중소기업 표준 2 (0x02)', 'addr': 0x00, 'cmd': 0x02},
    {'name': '대우/아남 계열', 'addr': 0x08, 'cmd': 0x1E},
    {'name': '기타 중소기업 (Full FF)', 'addr': 0x00, 'cmd': 0xFF},
    {'name': 'TCL/하이센스 계열', 'addr': 0x40, 'cmd': 0x12},
]

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("pigpiod 데몬을 먼저 실행하세요! (sudo pigpiod)")
        return

    ir = PI_IRTransmitter(pi, IR_PIN)

    print("\n" + "="*50)
    print("      TV 제조사 식별 도구 (NEC Protocol)")
    print("="*50)

    while True:
        print("\n[테스트 메뉴]")
        for i, tv in enumerate(TV_CANDIDATES, 1):
            print(f"{i}. {tv['name']} (Addr: {hex(tv['addr'])}, Cmd: {hex(tv['cmd'])})")
        print("0. 프로그램 종료")
        
        try:
            choice = input("\n테스트할 번호를 선택하세요: ")
            if choice == '0':
                break
            
            idx = int(choice) - 1
            if 0 <= idx < len(TV_CANDIDATES):
                target = TV_CANDIDATES[idx]
                print(f"\n>>> [{target['name']}] 신호 전송 중...")
                
                # 확실한 수신을 위해 3회 반복 송출
                for _ in range(3):
                    ir.send_nec_code(target['addr'], target['cmd'])
                    time.sleep(0.1)
                
                print("전송 완료! TV의 반응을 확인하세요.")
            else:
                print("잘못된 번호입니다.")
        
        except ValueError:
            print("숫자를 입력해 주세요.")
        except KeyboardInterrupt:
            break

    pi.stop()
    print("\n테스트를 종료합니다.")

if __name__ == "__main__":
    main()