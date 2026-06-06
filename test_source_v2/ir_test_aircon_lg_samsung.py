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

        # =====================================================================
        # [핵심 수정 포인트] 소켓 버퍼 오버플로우 방지를 위한 분할 전송(Chunking)
        # 삼성 14바이트 제어 시 발생하는 5,000개 이상의 펄스를 3,000개씩 나눠 보냅니다.
        # =====================================================================
        CHUNK_SIZE = 3000
        for i in range(0, len(full_pulses), CHUNK_SIZE):
            self.pi.wave_add_generic(full_pulses[i:i+CHUNK_SIZE])
        # =====================================================================

        wave_id = self.pi.wave_create()
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.01)
            self.pi.wave_delete(wave_id)

    # ==========================================
    # 1. LG 휘센 에어컨 제어 메소드
    # ==========================================
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

    # ==========================================
    # 2. 삼성 에어컨 제어 메소드
    # ==========================================
    def _bytes_to_samsung_time_list(self, byte_array):
        """
        14바이트(112비트) 헥사 데이터를 삼성 규격 타이밍 데이터로 변환합니다.
        """
        # 시작 헤더: Mark 3000us / Space 3000us
        time_list = [3000, 3000]
        
        for idx, b in enumerate(byte_array):
            # 7바이트(56비트) 전송 직후, 중간 헤더(Mid-Leader)를 한 번 더 삽입
            if idx == 7:
                time_list.extend([3000, 3000])
                
            for i in range(8):  # LSB-first 데이터 비트 변환
                time_list.append(600)  # 데이터 비트 Mark 기본값
                if (b >> i) & 1:
                    time_list.append(1600)  # Bit 1 Space
                else:
                    time_list.append(600)   # Bit 0 Space
                    
        time_list.append(600)  # 종료 마크 (Trailer)
        return time_list

    def generate_samsung_ac_on_time_list(self, temp):
        """
        가장 보편적으로 사용되는 삼성 14바이트 Hex 데이터베이스입니다.
        """
        samsung_temp_database = {
            18: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x10, 0x00, 0x00],
            19: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x11, 0x00, 0x00],
            20: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x12, 0x00, 0x00],
            21: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x13, 0x00, 0x00],
            22: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x14, 0x00, 0x00],
            23: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x15, 0x00, 0x00],
            24: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x16, 0x00, 0x00],
            25: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x17, 0x00, 0x00],
            26: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x18, 0x00, 0x00],
            27: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x19, 0x00, 0x00],
            28: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x1A, 0x00, 0x00],
            29: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x1B, 0x00, 0x00],
            30: [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x1C, 0x00, 0x00],
        }
        byte_array = samsung_temp_database.get(temp, samsung_temp_database[24])
        return self._bytes_to_samsung_time_list(byte_array)

    def get_samsung_ac_off_time_list(self):
        off_bytes = [0x02, 0x92, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x01, 0xD2, 0x0F, 0x00, 0x00, 0x00, 0x00]
        return self._bytes_to_samsung_time_list(off_bytes)

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("pigpiod 데몬을 실행해 주세요! (sudo pigpiod)")
        return

    ir = PI_IRTransmitter(pi, IR_PIN)

    print("\n" + "="*50)
    print("   LG 휘센 & 삼성 에어컨 통합 IR 제어 프로그램 (보정판)")
    print("="*50)

    while True:
        print("\n[제조사 선택]")
        print("1. LG 휘센 에어컨")
        print("2. 삼성 에어컨")
        print("0. 프로그램 종료")
        
        brand_choice = input("\n원하는 제조사 번호를 입력하세요: ")
        
        if brand_choice == '0':
            break
        elif brand_choice not in ['1', '2']:
            print("❌ 올바른 제조사 번호를 입력해 주세요.")
            continue
            
        brand_name = "LG 휘센" if brand_choice == '1' else "삼성"
        
        while True:
            print(f"\n[{brand_name} 에어컨 제어 메뉴]")
            print("1. 에어컨 켜기 및 온도 설정 (18°C ~ 30°C)")
            print("2. 에어컨 끄기")
            print("0. 이전 메뉴로 (제조사 재선택)")
            
            choice = input("\n원하는 동작 번호를 입력하세요: ")
            
            if choice == '0':
                break
                
            elif choice == '1':
                try:
                    temp = int(input("설정할 희망 온도를 입력하세요 (18 ~ 30): "))
                    if 18 <= temp <= 30:
                        print(f"\n>>> {brand_name} [켜기 및 {temp}°C] 신호 송출...")
                        if brand_choice == '1':
                            dynamic_time_list = ir.generate_lg_ac_on_time_list(temp)
                        else:
                            dynamic_time_list = ir.generate_samsung_ac_on_time_list(temp)
                        ir.send_raw_signal(dynamic_time_list)
                        print("송출 완료!")
                    else:
                        print("❌ 18도에서 30도 사이만 입력 가능합니다.")
                except ValueError:
                    print("❌ 숫자를 입력해 주세요.")
                    
            elif choice == '2':
                print(f"\n>>> {brand_name} [끄기] 신호 송출...")
                if brand_choice == '1':
                    static_time_list = ir.get_lg_ac_off_time_list()
                else:
                    static_time_list = ir.get_samsung_ac_off_time_list()
                ir.send_raw_signal(static_time_list)
                print("송출 완료!")
            else:
                print("❌ 올바른 동작 번호를 입력해 주세요.")

    pi.stop()

if __name__ == "__main__":
    main()