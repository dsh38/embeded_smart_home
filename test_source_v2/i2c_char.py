import time
import smbus2

I2C_ADDR = 0x27
LCD_CHR = 1
LCD_CMD = 0

LINE1 = 0x80
LINE2 = 0xC0

BACKLIGHT = 0x08
ENABLE = 0b00000100

# CGRAM (사용자 정의 문자 저장소) 시작 주소
LCD_SETCGRAMADDR = 0x40

bus = smbus2.SMBus(1)

# --- [특수 문자 픽셀 데이터 정의] ---
# 1. '도(°)' 기호 (0번 슬롯에 저장할 예정)
DEGREE_CHAR = [0x1C, 0x12, 0x1C, 0x00, 0x00, 0x00, 0x00, 0x00]

# 2. '물방울(습도)' 기호 (1번 슬롯에 저장할 예정)
DROP_CHAR = [0x04, 0x04, 0x0E, 0x0E, 0x1F, 0x1F, 0x0E, 0x00]


def lcd_byte(bits, mode):
    bits_high = mode | (bits & 0xF0) | BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | BACKLIGHT
    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
    time.sleep(0.001)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.001)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.001)

def lcd_init():
    time.sleep(0.05)
    lcd_byte(0x33, LCD_CMD) 
    time.sleep(0.005)
    lcd_byte(0x32, LCD_CMD) 
    time.sleep(0.005)
    lcd_byte(0x06, LCD_CMD) 
    time.sleep(0.005)
    lcd_byte(0x0C, LCD_CMD) 
    time.sleep(0.005)
    lcd_byte(0x28, LCD_CMD) 
    time.sleep(0.005)
    lcd_byte(0x01, LCD_CMD) 
    time.sleep(0.01)

# --- [핵심: 커스텀 문자 등록 함수] ---
def lcd_create_char(location, pattern):
    # location: 0번부터 7번까지 총 8개만 가능
    if location < 0 or location > 7:
        return
    # LCD에게 "이제부터 몇 번 슬롯에 그림 그릴게"라고 명령
    lcd_byte(LCD_SETCGRAMADDR | (location << 3), LCD_CMD)
    # 8줄의 픽셀 데이터를 순서대로 전송
    for i in range(8):
        lcd_byte(pattern[i], LCD_CHR)

def lcd_string(message, line):
    message = message.ljust(16, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(16):
        lcd_byte(ord(message[i]), LCD_CHR)

# --- [특수문자를 중간에 섞어 쓰는 출력 함수] ---
def display_onion(temp, humidity):
    # 1번째 줄: Temp: 24.5[도]C
    lcd_byte(LINE1, LCD_CMD)
    # "Temp: 24.5" 먼저 출력
    str1 = f"Temp: {temp}"
    for char in str1:
        lcd_byte(ord(char), LCD_CHR)
    lcd_byte(0, LCD_CHR)  # 0번 슬롯에 저장된 '도(°)' 출력
    lcd_byte(ord('C'), LCD_CHR) # 마지막에 대문자 C 출력
    
    # 남은 칸 공백 채우기 (전체 16칸 중 남은 칸)
    for _ in range(16 - len(str1) - 2):
        lcd_byte(ord(' '), LCD_CHR)

    # 2번째 줄: [물방울] Humid: 55.0 %
    lcd_byte(LINE2, LCD_CMD)
    lcd_byte(1, LCD_CHR)  # 1번 슬롯에 저장된 '물방울' 출력
    str2 = f" Humid: {humidity} %"
    for char in str2:
        lcd_byte(ord(char), LCD_CHR)
        
    for _ in range(16 - len(str2) - 1):
        lcd_byte(ord(' '), LCD_CHR)


# 메인 실행
try:
    print("LCD 및 커스텀 문자 초기화 중...")
    lcd_init()
    
    # 생성한 패턴을 LCD 내부 메모리에 등록 (0번과 1번 등록)
    lcd_create_char(0, DEGREE_CHAR)
    lcd_create_char(1, DROP_CHAR)
    print("초기화 완료!")

    while True:
        print("\n--- 온습도 입력 모드 ---")
        t_input = input("온도를 입력하세요 (예: 24.5): ")
        h_input = input("습도를 입력하세요 (예: 55): ")
        
        # 화면에 특수문자와 함께 출력
        display_onion(t_input, h_input)
        print("LCD에 온습도가 표시되었습니다.")

except KeyboardInterrupt:
    lcd_byte(0x01, LCD_CMD)
    print("\n프로그램을 종료합니다.")