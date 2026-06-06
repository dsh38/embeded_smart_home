import time
from config import Config

# smbus 라이브러리 동적 로드 (smbus / smbus2 호환)
SMBUS_AVAILABLE = False
try:
    import smbus
    SMBUS_AVAILABLE = True
except ImportError:
    try:
        import smbus2 as smbus
        SMBUS_AVAILABLE = True
    except ImportError:
        pass

# PCF8574 LCD 백팩 핀 맵 상수 정의
MASK_RS = 0x01  # Register Select (0 = Command, 1 = Data)
MASK_RW = 0x02  # Read/Write (0 = Write, 1 = Read)
MASK_EN = 0x04  # Enable Clock
MASK_BACKLIGHT = 0x08  # 백라이트 컨트롤 (1 = On, 0 = Off)

# LCD 명령어 상수
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# LCD 라인 주소
LCD_LINE_1 = 0x80 # 1번째 줄 시작 주소
LCD_LINE_2 = 0xC0 # 2번째 줄 시작 주소

class I2CLcd1602:
    def __init__(self):
        self.address = Config.I2C_ADDR
        self.bus = None
        self.backlight_state = MASK_BACKLIGHT
        self.simulated = False
        
        # 1602 2줄 버퍼 (중복 쓰기 최소화 및 디버깅용)
        self.line1_buffer = " " * 16
        self.line2_buffer = " " * 16
        
        if SMBUS_AVAILABLE:
            try:
                # 라즈베리파이 기본 I2C 버스는 1번입니다.
                self.bus = smbus.SMBus(1)
                self._lcd_init()
                print(f"✅ [I2C LCD] LCD 모듈이 I2C 주소 0x{self.address:02x}에 등록되었습니다.")
            except Exception as e:
                print(f"⚠️ [I2C LCD] 물리 LCD 초기화 중 예외: {str(e)}. 시뮬레이션 모드로 작동합니다.")
                self.simulated = True
        else:
            print("💡 [I2C LCD] smbus 라이브러리가 없습니다. LCD 시뮬레이션 모드가 실행됩니다.")
            self.simulated = True

    def _write_byte_i2c(self, val):
        """I2C 버스를 통해 8비트 데이터 전송"""
        if self.bus and not self.simulated:
            try:
                self.bus.write_byte(self.address, val)
            except IOError:
                # 일시적 I2C 에러 발생 시 시뮬레이션 모드로 스위칭
                self.simulated = True
                print("⚠️ [I2C LCD] I2C 전송 오류 발생. 시뮬레이션 모드로 전환되었습니다.")

    def _pulse_enable(self, data):
        """LCD Enable 핀 토글링"""
        self._write_byte_i2c(data | MASK_EN)
        time.sleep(0.0005)
        self._write_byte_i2c(data & ~MASK_EN)
        time.sleep(0.0001)

    def _write_4bits(self, value, mode=0):
        """상위/하위 4비트로 쪼개서 LCD로 전송"""
        # 상위 4비트
        high_nibble = value & 0xF0
        self._write_byte_i2c(high_nibble | mode | self.backlight_state)
        self._pulse_enable(high_nibble | mode | self.backlight_state)
        
        # 하위 4비트
        low_nibble = (value << 4) & 0xF0
        self._write_byte_i2c(low_nibble | mode | self.backlight_state)
        self._pulse_enable(low_nibble | mode | self.backlight_state)

    def _write_cmd(self, cmd):
        """LCD 명령 제어 바이트 쓰기"""
        self._write_4bits(cmd, mode=0)

    def _write_data(self, data):
        """LCD 문자 데이터 바이트 쓰기"""
        self._write_4bits(data, mode=MASK_RS)

    def _lcd_init(self):
        """1602 LCD 초기 4비트 모드 설정 시퀀스 실행"""
        time.sleep(0.05)
        # 4비트 모드 진입 초기화 명령 시퀀스 (연속 전송)
        self._write_4bits(0x30, mode=0)
        time.sleep(0.005)
        self._write_4bits(0x30, mode=0)
        time.sleep(0.001)
        self._write_4bits(0x32, mode=0)  # 4비트 모드 진입 명령
        
        # LCD 세부 세팅
        self._write_cmd(0x28)  # 4비트 모드, 2라인 표시, 5x8 폰트
        self._write_cmd(0x0C)  # 디스플레이 On, 커서 Off, 블링킹 Off
        self._write_cmd(0x06)  # 주소 증가 모드, 시프트 없음
        self.clear()

    def clear(self):
        """LCD 화면 전체 삭제"""
        self.line1_buffer = " " * 16
        self.line2_buffer = " " * 16
        if not self.simulated:
            self._write_cmd(LCD_CLEARDISPLAY)
            time.sleep(0.002)
        else:
            print("📺 [LCD 화면 지움]")

    def backlight_on(self):
        """LCD 백라이트 켜기"""
        self.backlight_state = MASK_BACKLIGHT
        self._write_byte_i2c(self.backlight_state)

    def backlight_off(self):
        """LCD 백라이트 끄기"""
        self.backlight_state = 0x00
        self._write_byte_i2c(self.backlight_state)

    def display_string(self, string, line):
        """특정 줄(1 또는 2)에 문자열 출력 (최대 16자 자동 절단)"""
        # 한글/특수문자 필터 및 ASCII 범위 문자 다듬기
        # LCD 1602 폰트 한계로 도 기호(°)는 ' ' 등으로 대체하여 표시
        safe_string = string.replace('°', '')
        
        # 16자 폭에 맞춰 공백 패딩 또는 자르기
        formatted_str = f"{safe_string:<16}"[:16]
        
        if line == 1:
            if formatted_str == self.line1_buffer:
                return # 이전 문자열과 동일하면 쓰기 생략 (I2C 부하 감소)
            self.line1_buffer = formatted_str
            start_addr = LCD_LINE_1
        elif line == 2:
            if formatted_str == self.line2_buffer:
                return
            self.line2_buffer = formatted_str
            start_addr = LCD_LINE_2
        else:
            return

        if not self.simulated:
            self._write_cmd(start_addr)
            for char in formatted_str:
                self._write_data(ord(char))
        else:
            # 시뮬레이션 모드: 콘솔에 LCD 창 구현 시각화
            border = "+" + "-"*16 + "+"
            print(f"\n{border}\n|{self.line1_buffer}|\n|{self.line2_buffer}|\n{border}")
