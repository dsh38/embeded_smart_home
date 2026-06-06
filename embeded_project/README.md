# 🏠 스마트홈 IoT 제어 시스템 (SmartHome IoT System)

라즈베리파이 4B (Debian Trixie 타겟) 기반으로 동작하며, I2C 1602 LCD 모니터링 모듈과 DHT22 온습도 센서, 그리고 pigpio 기반 IR(적외선) 송신기 코드를 통합한 파이썬 Flask 기반 스마트홈 IoT 웹 애플리케이션입니다.

---

## 🚀 1. 주요 기능 및 보안 탑재 사항

1. **MVC 패턴 기반 설계**:
   * 개발 및 유지보수가 쉽도록 Model, View, Controller 구조를 적용하였습니다.
   * 기기 생성은 **팩토리 패턴(Factory Pattern)**, 삼성/LG 에어컨 신호 전송은 **어댑터 패턴(Adapter Pattern)**으로 추상화되어 확장성이 뛰어납니다.
2. **SQLite 미사용 파일 기반 영구 저장 (Persistence)**:
   * 가벼운 배포를 위해 DB 설치 없이 `data/config.json` 및 `data/login_attempts.json` 파일로 데이터(로그인 암호 해시, 등록 기기, 차단 기록)를 안전하게 관리합니다.
3. **보안 강화 로그인 시스템**:
   * 회원가입 기능은 제공하지 않으며, 초기 관리자 계정은 `admin` / `admin` 입니다. (비밀번호는 PBKDF2:SHA256 암호 해시화되어 안전하게 보존됩니다.)
   * 마이페이지(우측 상단 드롭다운)에서 ID와 비밀번호 변경이 가능하며, 변경 시 기존 해시 암호 검증(3단계 비밀번호)을 요구합니다.
   * **브루트포스 방지**: 동일 IP에서 연속 **10회 로그인 실패 시 24시간 동안 강제 차단**되며, 차단 시점 및 차단 중 시도 시 서버 콘솔에 `[WARNING]` 경고 로그가 실시간 출력됩니다.
4. **Cloudflare Tunnel 및 Proxy 호환**:
   * Cloudflare 프록시 터널을 통한 도메인 연동 시 실제 접속 IP가 `127.0.0.1`로 뭉개지는 현상을 교정하기 위해 **ProxyFix 미들웨어** 및 `CF-Connecting-IP` 추출 필터링을 결합하였습니다.
5. **실시간 온습도 & LCD 모니터링**:
   * DHT22 센서 값을 10초 주기로 수집하여 웹 대시보드에 페이드 효과와 함께 갱신합니다.
   * I2C 1602 LCD 문자 모듈을 통해 **프로젝트 명칭, 현재 실측 온습도, 서버 접속 IP/도메인**을 3초 주기로 순환 출력하며, 서버가 다운되면 즉시 `System offline`으로 자동 정돈됩니다.

---

## 🔌 2. 하드웨어 배선 및 라즈베리파이 설정 가이드

### 1) 하드웨어 핀 배선 맵핑
라즈베리파이 4B의 실물 GPIO 핀 배치 가이드입니다.

| 센서 / 모듈 | 센서 핀 | 라즈베리파이 GPIO | 핀 설명 |
| :--- | :---: | :---: | :--- |
| **DHT22 (온습도)** | VCC / DATA / GND | **GPIO 4** (Pin 7) | DATA 선에 10kΩ 풀업 저항 장착 권장 (VCC 3.3V 연결) |
| **IR 송신 LED** | Anode(+) / Cathode(-) | **GPIO 18** (Pin 12) | TR(PN2222 등)을 거쳐 전류 증폭 후 연결 권장 |
| **I2C 1602 LCD** | VCC / GND / SDA / SCL | **GPIO 2** (Pin 3) / **GPIO 3** (Pin 5) | I2C 통선 (VCC 5V 또는 3.3V 연결) |

*핀 번호는 **[config.py](config.py)**에서 언제든 원하시는 포트로 변경하실 수 있습니다.*

### 2) 라즈베리파이 OS (Debian Trixie) 초기 셋업
웹 서버 실행 전에 라즈베리파이 내부에서 아래의 드라이버 패키지들을 설치 및 가동해야 합니다.

#### ① I2C 버스 활성화
```bash
sudo raspi-config
# [Interface Options] -> [I2C] -> [Enable(Yes)] 선택 후 완료 및 리부팅
```
설치 후 LCD 칩셋의 I2C 주소를 감지합니다:
```bash
sudo apt-get install i2c-tools -y
sudo i2cdetect -y 1
# 보통 0x27 또는 0x3f로 표시됩니다. 주소가 0x3f인 경우 config.py의 I2C_ADDR를 0x3f로 변경하십시오.
```

#### ② pigpiod 데몬 설치 및 자동 부팅 등록 (IR 송출용)
```bash
sudo apt-get install pigpio python3-pigpio -y
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

#### ③ DHT.py 모듈 복사
물리 센서 실측을 완료하기 위해서는, 동봉된 **`DHT.py`** (pigpio 연동 온습도 전용 라이브러리) 스크립트 파일을 **본 프로젝트 폴더 루트 경로**(`D:\Antigravity_Project\embeded_project\`) 바로 아래에 배치해 주십시오.

---

## 🏃 3. 실행 방법 (How to Run)

### 1) 패키지 종속성 설치
```bash
pip install Flask
```
*(테스트 장비에 `smbus` 또는 `pigpio`가 없더라도, 드라이버 내의 **자동 시뮬레이터(Mock)** 가 활성화되어 윈도우 환경 및 센서 무연결 상태에서도 웹 서버와 디스플레이 흐름이 에러 없이 실행됩니다.)*

### 2) 서버 가동
프로젝트 폴더 내에서 파이썬 명령을 실행합니다:
```bash
python app.py
```

### 3) 접속 테스트
* 기본 포트는 `5000`입니다.
* **로컬 테스트**: 브라우저 주소창에 `http://localhost:5000`을 입력하여 접속합니다.
* **원격 테스트 (모바일/PC)**: 동일 공유기상 네트워크에서 모바일 기기로 `http://[라즈베리파이_IP_주소]:5000`으로 접속이 가능합니다.
* **초기 계정**: ID `admin` / PW `admin` (로그인 후 헤더 '내 계정' 드롭다운을 통해 즉시 변경할 수 있습니다.)

---

## 📄 4. 라이선스 (License)

본 프로젝트는 [MIT License](LICENSE) 하에 배포됩니다. 자유롭게 복제, 수정 및 재배포하여 스마트홈 구축에 활용하실 수 있습니다.
