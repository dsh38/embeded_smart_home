import time
import smbus2

# I2C 설정
I2C_ADDR = 0x27
LCD_CHR = 1  # 데이터 모드
LCD_CMD = 0  # 명령 모드

LINE1 = 0x80  # 1번째 줄 주소
LINE2 = 0xC0  # 2번째 줄 주소

BACKLIGHT = 0x08  # 켜짐
ENABLE = 0b00000100  # Enable 비트

bus = smbus2.SMBus(1)

def lcd_byte(bits, mode):
    bits_high = mode | (bits & 0xF0) | BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | BACKLIGHT

    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bits_high)

    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
    # 라즈베리파이 4의 속도를 고려해 대기 시간을 0.0005 -> 0.001초로 상향
    time.sleep(0.001)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.001)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.001)

def lcd_init():
    # LCD 초기화 시퀀스 및 지연 시간 확보
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
    lcd_byte(0x01, LCD_CMD)  # 화면 Clear
    time.sleep(0.01)

def lcd_string(message, line):
    # 16칸 공백 맞춤 (영문/숫자 기준)
    message = message.ljust(16, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(16):
        lcd_byte(ord(message[i]), LCD_CHR)

# 메인 루프
try:
    print("LCD 초기화 중...")
    lcd_init()
    print("초기화 완료!")
    
    # 안내 문구 잠시 출력
    lcd_string("Ready to Type", LINE1)
    lcd_string("Look at Terminal", LINE2)
    time.sleep(2)

    while True:
        # 터미널에서 글자 입력 받기
        print("\n--- LCD 입력 모드 ---")
        text1 = input("1번째 줄에 넣을 글자 (최대 16자): ")
        text2 = input("2번째 줄에 넣을 글자 (최대 16자): ")
        
        # 알파벳과 숫자만 지원합니다 (1602 LCD 기본 사양)
        lcd_string(text1[:16], LINE1)
        lcd_string(text2[:16], LINE2)
        print("LCD에 반영되었습니다.")

except KeyboardInterrupt:
    # Ctrl + C로 종료 시 LCD 깨끗하게 비우기
    lcd_byte(0x01, LCD_CMD)
    print("\n프로그램을 종료합니다.")