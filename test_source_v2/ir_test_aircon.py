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
        """
        [보정된 함수] 누적 타이밍 오차를 줄이기 위해 
        실제 생성되는 26us(13us ON + 13us OFF) 주기에 맞춰 사이클 수를 계산합니다.
        """
        actual_cycle_us = 26  # 13us High + 13us Low = 26us (약 38.4kHz로 수신호환성 최적)
        cycles = int(duration_us / actual_cycle_us)
        
        pulses = []
        for _ in range(cycles):
            # 13마이크로초 동안 켜고, 13마이크로초 동안 끔
            pulses.append(pigpio.pulse(1 << self.pin, 0, 13))
            pulses.append(pigpio.pulse(0, 1 << self.pin, 13))
        return pulses

    def send_raw_signal(self, time_list):
        # 파형 송출 중 혹시 모를 충돌을 방지하기 위해 비지 상태 체크 강화
        while self.pi.wave_tx_busy():
            time.sleep(0.02)
            
        self.pi.wave_clear()
        full_pulses = []

        for idx, duration in enumerate(time_list):
            if idx % 2 == 0:
                full_pulses.extend(self._create_carrier_pulse(duration))
            else:
                full_pulses.append(pigpio.pulse(0, 1 << self.pin, duration))

        self.pi.wave_add_generic(full_pulses)
        wave_id = self.pi.wave_create()
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.01)
            self.pi.wave_delete(wave_id)

    def generate_lg_ac_on_time_list(self, temp):
        n1 = 8; n2 = 8; n3 = 0; n4 = 0
        n5 = temp - 15  
        n6 = 4  # 강풍
        n7 = (n1 + n2 + n3 + n4 + n5 + n6) & 0x0F
        
        code_28bit = (n1 << 24) | (n2 << 20) | (n3 << 16) | (n4 << 12) | (n5 << 8) | (n6 << 4) | n7
        
        # LG 표준 헤더 타이밍 보정 (8600us / 4050us)
        time_list = [8600, 4050]
        
        for i in range(27, -1, -1):
            time_list.append(520)  # Mark 기준값 보정
            if (code_28bit >> i) & 1:
                time_list.append(1560)  # Bit 1 Space
            else:
                time_list.append(520)   # Bit 0 Space
                
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

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("pigpiod 데몬을 실행해 주세요! (sudo pigpiod)")
        return

    ir = PI_IRTransmitter(pi, IR_PIN)

    print("\n" + "="*50)
    print("      LG 휘센 에어컨 타이밍 보정 버전 (DFR0095)")
    print("="*50)

    while True:
        print("\n[메뉴 선택]")
        print("1. 에어컨 켜기 및 온도 설정 (18°C ~ 30°C)")
        print("2. 에어컨 끄기 (종료)")
        print("0. 프로그램 종료")
        
        choice = input("\n원하는 동작 번호를 입력하세요: ")
        
        if choice == '1':
            try:
                temp = int(input("설정할 희망 온도를 입력하세요 (18 ~ 30): "))
                if 18 <= temp <= 30:
                    print(f"\n>>> LG 휘센 [켜기 및 {temp}°C] 신호 송출...")
                    dynamic_time_list = ir.generate_lg_ac_on_time_list(temp)
                    ir.send_raw_signal(dynamic_time_list)
                    print("송출 완료!")
                else:
                    print("❌ 18도에서 30도 사이만 입력 가능합니다.")
            except ValueError:
                print("❌ 숫자를 입력해 주세요.")
                
        elif choice == '2':
            print("\n>>> LG 휘센 [끄기] 신호 송출...")
            static_time_list = ir.get_lg_ac_off_time_list()
            ir.send_raw_signal(static_time_list)
            print("송출 완료!")
        elif choice == '0':
            break

    pi.stop()

if __name__ == "__main__":
    main()