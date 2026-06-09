# 스마트홈 IoT 시스템 프로젝트 진행 상황 인계서 (DEV_STATUS.md - v8 개편)

이 문서는 Antigravity IDE 및 원격 Raspberry Pi 4B (Debian Trixie) 환경에서 개발과 테스트를 연속성 있게 진행할 수 있도록 설계된 프로젝트 상태 정의 및 인계용 요약 파일입니다.

---

## 1. 프로젝트 개요 및 아키텍처 (v8 개편)

* **프로젝트명**: 스마트홈 IoT 시스템 (SmartHome IoT System)
* **디자인 패턴**: MVC 패턴 적용 및 어댑터/팩토리 패턴을 통한 하드웨어 제어 추상화.
* **보안성**: 비밀번호 암호 해싱 저장 (PBKDF2/SHA256) 및 현재 비밀번호 해시 대조 확인 3단계 프로세스.
* **IP 필터링**: Cloudflare Proxy 호환 실제 접속 IP 탐색 헬퍼 탑재 (`CF-Connecting-IP` -> `X-Forwarded-For` -> `remote_addr`).
* **브루트포스 방지**: IP별 10회 로그인 실패 시 24시간 로그인 접속 차단 기능 구현. attempts 파일 기반 영구 저장 (`data/login_attempts.json`).
* **DHT22 드라이버**: pigpio 및 DHT.py 파이썬 라이브러리를 연동한 DHT22 수집 기법 구현. 일시적 통신 불량 시 직전 값 안전 캐싱 기능 적용. (GPIO 4)
* **I2C 1602 LCD**: 16x2 문자 LCD 모듈 I2C 연결 연동. Flask 구동 시 백그라운드 데몬 스레드로 온습도/접속 주소 순환 교차 표기. (I2C 기본 주소: 0x27)
* **긴 접속 주소 Marquee**: 접속 주소(IP + 포트번호 등)가 16자를 초과하는 경우, 첫 화면 1.0초 정지 -> 0.35초 간격 좌우 스크롤(Marquee) -> 마지막 화면 1.5초 정지 구조를 탑재하여 글자 잘림을 완전 해결. 스크롤 완료 후 온습도 화면으로 즉각 리턴.
* **Flask 디버그 이중 구동 방지**: `app.debug = True`를 사전 명시 선언하여 디버그 리로더 작동 시 LCD 스레드가 2개 중복 생성되는 I2C 버스 및 시뮬레이션 충돌 해결.
* **IP 자동 감지**: 설정된 도메인(`config.py` 내 `SYSTEM_URL`)이 없을 경우, **외부 공인 IP 또는 로컬 LAN IP 주소를 자동 탐지**하여 LCD에 교차 표기 기능 탑재.
* **배포 문서 구축**: GitHub 릴리즈를 위해 설치 가이드 및 아키텍처 매뉴얼 문서([README.md](README.md))와 초안에서부터의 상세 개발 히스토리 요약서([HISTORY.md](HISTORY.md)) 작성 완료.
* **디자인**: 프리미엄 Glassmorphism UI 및 화이트 테마 기본 적용.
* **레이아웃**: 헤더 우측 상단 '내 계정' 드롭다운 메뉴로 계정 관리 통합.

---

## 2. 파일 목록 및 역할 정의

```text
embeded_project/
├── app.py                      # Flask 진입점, LCD 데몬 스레드 구동(Marquee 스크롤 포함), IP 자동 탐색 및 종료 후크 제어
├── config.py                   # 비밀키 설정, 파일 경로 및 GPIO 핀 정의 (SYSTEM_URL = None 기본값 설정)
├── LICENSE                     # [NEW] 오픈소스 배포를 위한 MIT 라이선스 문서
├── README.md                   # [NEW] GitHub 배포용 통합 상세 매뉴얼 및 하드웨어 배선 가이드
├── HISTORY.md                  # [NEW] 초안에서부터 v8 개편에 이르는 개발 변천사 상세 요약서
├── DEV_STATUS.md               # [본 문서] 진행 상황 및 원격 이식 인계 정보
├── recorded_signals.json       # [유저 업로드] 삼성 AC 제어용 원시 IR 파형 딕셔너리
├── ir_test_lg_samsung_v2.py    # [유저 업로드] 원본 pigpio 기반 에어컨 테스트 스크립트
├── check_sensor_pigpio.py      # [유저 업로드] 원본 pigpio 및 DHT.py 연동 DHT22 검증용 스크립트
├── data/                       # 파일 기반 저장소 디렉토리
│   ├── config.json             # 사용자 계정(비밀번호 해시) 및 등록 가전 정보 (자동 생성)
│   └── login_attempts.json     # IP별 로그인 실패 횟수 및 차단 기한 기록 (자동 생성)
├── models/                     # [M - Model] 파일 입출력 및 검증 데이터 모델
│   ├── auth_model.py           # 계정 인증 관리, 현재 암호 대조 수정, IP별 LoginAttemptTracker 탑재
│   └── device_model.py         # 기기(에어컨) 정보 등록, 제어 상태 업데이트 및 범위 벨리데이션
├── controllers/                # [C - Controller] 백엔드 비즈니스 로직 API 라우트
│   ├── auth_controller.py      # CF IP 필터링, 브루트포스 차단 검증, warning 경고 로깅 및 암호 변경 API
│   ├── device_controller.py    # 기기 목록 조회, 추가, 제어(IR 트리거 연동) 및 기기 삭제 API
│   └── sensor_controller.py    # DHT22 센서 10초 주기 실시간 데이터 반환 API
├── hardware/                   # 하드웨어 제어 추상화 레이어
│   ├── ir_driver.py            # pigpio 기반 IR 펄스 송출기 (LG 28bit 연산 및 삼성 펄스 룩업 맵핑)
│   ├── dht22_driver.py         # pigpio 및 DHT.py 라이브러리 연동 DHT22 측정기 (캐싱 감쇄 및 Mock 폴백)
│   └── i2c_lcd_driver.py       # PCF8574 LCD 1602 제어 드라이버 (Line 2 실시간 갱신 및 시뮬레이터 내장)
├── templates/                  # [V - View] HTML5 템플릿 마크업
│   ├── base.html               # 듀얼 테마 전환 및 상단 우측 내 계정 드롭다운 버튼 마크업
│   ├── login.html              # Glassmorphism 테마 로그인 화면 및 자동 로그인 체크
│   ├── dashboard.html          # 실시간 온습도 게이지, 기기 카드 목록, 계정정보 변경 모달
│   └── device_detail.html      # 운전 모드, 온도(18~30 검증), 바람세기, 설정 적용 버튼
└── static/                     # 정적 웹 자원
    ├── css/
    │   └── style.css           # 듀얼 테마(화이트 기본), Glassmorphism, 헤더 드롭다운(z-index 보정), 간편 버튼 스타일
    └── js/
        ├── auth.js             # 로그인 처리, 눈동자 모양 비밀번호 토글
        ├── dashboard.js        # 10초 센서 갱신, 기기 리스트 및 간편 전원 조작(e.stopPropagation), 모달 제어
        └── device.js           # 기기 옵션 세팅, 온도 실시간 검증(잘못 입력 에러 매핑), 제어 전송
```

---

## 3. 네트워크 주소 자동 감지 및 스크롤 프로세스

1. `config.py` 내의 `SYSTEM_URL = None` 상태일 경우, Flask가 기동되거나 디스플레이를 표시할 때 `get_system_address()` 유틸 함수가 작동하여 공인 IP 또는 로컬 LAN IP를 자동 취득하고 포트 번호(`Config.PORT`)와 결합합니다.
2. 접속 주소가 16자를 초과하면 LCD 루프에서 **Marquee 스크롤**을 구동합니다.
3. 스크롤 시 `119.198.33.203:5000` 주소의 전체 길이가 첫 글자부터 마지막 글자까지 흐르도록 슬라이딩 윈도우를 계산하여 LCD 드라이버에 전송합니다.
4. 가독성 극대화를 위해 시작 부분(1.0초)과 끝 부분(1.5초)에 정지 딜레이를 주며, 스크롤 이동 단계(0.35초)마다 LCD가 부드럽게 갱신되도록 제어합니다.

---

## 4. 진행 현황 체크리스트 (v8 개편 반영 완료)

* [x] **도메인 기본값 해제 및 포트 추가**: `config.py` 내 `SYSTEM_URL = None` 및 `PORT = 5000` 설정 완료
* [x] **공인/로컬 IP 자동 탐색 및 포트 결합**: `app.py` 내 `get_system_address()` 및 IP 뒤 포트 자동 표출 구현 완료
* [x] **1602 LCD 긴 접속 주소 좌우 스크롤(Marquee) 구현**: 16자 초과 주소 스크롤 렌더링 및 가독성 최적화 타이밍 적용 완료
* [x] **Flask 디버그 모드 리로더 스레드 이중 기동 방지**: `app.debug = Config.DEBUG` 적용 및 디버그 스레드 안정성 확보 완료
* [x] **삼성 에어컨 IR 송출 pigpiod 크래시 방지**: 38kHz 변조 펄스를 50us 반올림 및 고유 웨이브폼 ID 캐싱 후 wave_chain 분할 송출로 우회 완료
* [x] **pigpiod 데몬 소켓 자동 재연결**: 연결 해제 시 송출 전 자동 통신 소켓 복구 및 GPIO 재초기화 구조 적용 완료
* [x] **가상 LCD 시뮬레이터 실시간 반영 개선**: Line 2 업데이트 시에도 콘솔 렌더링이 트리거되도록 수정 완료
* [x] **GitHub 배포 매뉴얼**: 하드웨어 배선 및 기동 매뉴얼 [README.md](README.md) 작성 완료
* [x] **개발 히스토리 보고서**: 초안에서부터 v8에 이르는 상세 아키텍처 변경 이력서 [HISTORY.md](HISTORY.md) 작성 완료
* [x] **인계 문서 갱신**: 본 문서 `DEV_STATUS.md` 최신화 완료
