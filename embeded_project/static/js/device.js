// ==========================================================================
// 기기 상세 제어 패널 클라이언트 스크립트 (device.js)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // DOM 요소 캐싱
    const detailLoading = document.getElementById('detail-loading');
    const detailContentArea = document.getElementById('detail-content-area');
    
    // 메타 정보
    const deviceName = document.getElementById('device-name');
    const deviceBrandBadge = document.getElementById('device-brand-badge');
    const devicePowerBadge = document.getElementById('device-power-badge');
    
    // 실시간 온습도
    const roomTemp = document.getElementById('detail-room-temp');
    const roomHumi = document.getElementById('detail-room-humi');
    const settingSummary = document.getElementById('detail-setting-summary');
    
    // 제어 인풋 폼 요소
    const powerSwitch = document.getElementById('device-power-switch');
    const controlForm = document.getElementById('device-control-form');
    const modeSelect = document.getElementById('ctrl-mode');
    const tempInput = document.getElementById('ctrl-temp');
    const tempSelect = document.getElementById('ctrl-temp-select');
    const speedSelect = document.getElementById('ctrl-speed');
    
    // 에러 및 뱃지 영역
    const tempControlGroup = document.getElementById('temp-control-group');
    const fanNotice = document.getElementById('fan-notice');
    const tempError = document.getElementById('temp-error');
    const lgSpeedNotice = document.getElementById('lg-speed-notice');
    const controlAlert = document.getElementById('control-alert');
    
    // 버튼
    const btnCancel = document.getElementById('btn-cancel');
    const btnSubmit = document.getElementById('btn-submit');
    const btnDeleteDevice = document.getElementById('btn-delete-device');

    let currentDeviceData = null;

    // ---------------------------------------------
    // 1. 기기 상세 데이터 최초 로드
    // ---------------------------------------------
    function loadDeviceDetails() {
        fetch(`/api/devices/${DEVICE_ID}`)
            .then(res => {
                if (res.status === 404) {
                    alert('기기를 찾을 수 없습니다.');
                    window.location.href = '/dashboard';
                }
                return res.json();
            })
            .then(data => {
                if (data.success) {
                    currentDeviceData = data.device;
                    initializeControlPanel(data.device);
                }
            })
            .catch(err => {
                console.error('기기 상세 로드 오류:', err);
                alert('기기 정보를 읽어오는데 실패했습니다.');
            });
    }

    // 폼 초기 세팅
    function initializeControlPanel(device) {
        // 타이틀 정보 세팅
        deviceName.textContent = device.name;
        
        // 브랜드 로고 아이콘 및 스타일 셋업
        deviceBrandBadge.className = `brand-badge-wrapper ${device.brand}`;
        if (device.brand === 'samsung') {
            deviceBrandBadge.innerHTML = '<i class="fa-solid fa-snowflake"></i>';
            lgSpeedNotice.classList.add('hidden');
        } else {
            deviceBrandBadge.innerHTML = '<i class="fa-solid fa-certificate"></i>';
            lgSpeedNotice.classList.remove('hidden'); // LG 가이드 메시지 표기
        }

        // 전원 정보 세팅
        powerSwitch.checked = device.is_active;
        updatePowerBadgeState(device.is_active);

        // 운전 설정 세팅
        modeSelect.value = device.mode;
        tempInput.value = device.target_temp;
        tempSelect.value = device.target_temp;
        speedSelect.value = device.fan_speed;

        // 요약 정보 셋업
        updateStatusSummaryText(device);

        // 모드 변화에 따른 온도 UI 제어 체크
        handleModeUIChange(device.mode);

        // 로딩 화면 숨김 처리
        detailLoading.classList.add('hidden');
        detailContentArea.classList.remove('hidden');
    }

    // 전원 상태 뱃지 및 스타일 변경
    function updatePowerBadgeState(isActive) {
        if (isActive) {
            devicePowerBadge.textContent = '운전 중';
            devicePowerBadge.className = 'device-status-badge on';
        } else {
            devicePowerBadge.textContent = '전원 꺼짐';
            devicePowerBadge.className = 'device-status-badge off';
        }
    }

    // 설정 상태 요약 한글 텍스트 업데이트
    function updateStatusSummaryText(device) {
        const modeKorean = { 'cool': '냉방', 'dry': '제습', 'fan': '송풍', 'heat': '난방' };
        const speedKorean = { 'high': '강', 'medium': '중', 'low': '약', 'auto': '자동' };
        
        if (!device.is_active) {
            settingSummary.textContent = '정지';
            settingSummary.className = 'info-val summary-val text-muted';
        } else {
            const mode = modeKorean[device.mode] || device.mode;
            const speed = speedKorean[device.fan_speed] || device.fan_speed;
            
            if (device.mode === 'fan') {
                settingSummary.textContent = `${mode} / 바람:${speed}`;
            } else {
                settingSummary.textContent = `${mode} / ${device.target_temp}°C / 바람:${speed}`;
            }
            settingSummary.className = 'info-val summary-val';
        }
    }

    // ---------------------------------------------
    // 2. 실시간 온습도 갱신 (10초 주기)
    // ---------------------------------------------
    function fetchSensorData() {
        fetch('/api/sensor/dht22')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    roomTemp.textContent = `${data.temperature.toFixed(1)} °C`;
                    roomHumi.textContent = `${data.humidity.toFixed(1)} %`;
                }
            })
            .catch(err => console.error('센서 연동 에러:', err));
    }

    // 최초 갱신 주기 세팅
    fetchSensorData();
    const sensorInterval = setInterval(fetchSensorData, 10000);

    // ---------------------------------------------
    // 3. UI 변경 이벤트 리스너 연동 (동적 피드백)
    // ---------------------------------------------

    // 3-1. 전원 토글 스위치 변경 감지
    powerSwitch.addEventListener('change', () => {
        updatePowerBadgeState(powerSwitch.checked);
    });

    // 3-2. 운전 모드 선택 변경 감지
    modeSelect.addEventListener('change', () => {
        handleModeUIChange(modeSelect.value);
    });

    function handleModeUIChange(mode) {
        if (mode === 'fan') {
            // 송풍 모드 -> 온도 설정 숨김 및 안내 문구 활성화
            tempSelect.disabled = true;
            tempInput.disabled = true;
            fanNotice.classList.remove('hidden');
            tempError.classList.add('hidden'); // 에러 숨김
            btnSubmit.disabled = false; // 에러로 인해 비활성화되었을 수 있으므로 풀기
        } else {
            // 다른 모드 -> 온도 설정 활성화
            tempSelect.disabled = false;
            tempInput.disabled = false;
            fanNotice.classList.add('hidden');
            // 실시간 온도 검증 상태를 다시 한 번 체크
            validateTemperature();
        }
    }

    // 3-3. 온도 직접 입력창 입력 시 벨리데이션 체크 및 콤보박스 동기화
    tempInput.addEventListener('input', () => {
        const val = tempInput.value;
        if (val) {
            tempSelect.value = val; // 일치하는 콤보박스로 동기화
        }
        validateTemperature();
    });

    // 3-4. 온도 콤보박스 선택 시 직접 입력창 값 동기화
    tempSelect.addEventListener('change', () => {
        if (tempSelect.value) {
            tempInput.value = tempSelect.value;
        }
        validateTemperature();
    });

    // 온도 검증 메인 로직 (18~30 제한 범위)
    function validateTemperature() {
        // 송풍 모드이면 검증이 무의미하므로 즉각 통과 리턴
        if (modeSelect.value === 'fan') {
            tempError.classList.add('hidden');
            btnSubmit.disabled = false;
            return true;
        }

        const tempVal = parseInt(tempInput.value, 10);
        
        if (isNaN(tempVal) || tempVal < 18 || tempVal > 30) {
            // 입력 범위를 넘은 에러 상태 노출
            tempError.classList.remove('hidden');
            tempInput.classList.add('input-error');
            btnSubmit.disabled = true; // 확인 버튼 비활성화 (보안 및 에러 전송 방지)
            return false;
        } else {
            // 정상 상태 복귀
            tempError.classList.add('hidden');
            tempInput.classList.remove('input-error');
            btnSubmit.disabled = false;
            return true;
        }
    }

    // ---------------------------------------------
    // 4. 확인 및 취소 제어 폼 API 서브밋
    // ---------------------------------------------

    // 4-1. 취소 버튼 (대시보드로 복귀)
    if (btnCancel) {
        btnCancel.addEventListener('click', () => {
            clearInterval(sensorInterval);
            window.location.href = '/dashboard';
        });
    }

    // 4-2. 설정 적용 폼 제출 (확인 버튼 클릭)
    if (controlForm) {
        controlForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // 전송 전 안전성 최종 벨리데이션 수행
            if (!validateTemperature()) {
                showAlert('온도 입력 값이 잘못되었습니다. 범위를 확인하세요.', 'error');
                return;
            }

            const is_active = powerSwitch.checked;
            const mode = modeSelect.value;
            const target_temp = parseInt(tempInput.value, 10);
            const fan_speed = speedSelect.value;

            // 로딩 스피너 작동
            const originalBtnHtml = btnSubmit.innerHTML;
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> IR 신호 전송 중...';

            fetch(`/api/devices/${DEVICE_ID}/control`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active, mode, target_temp, fan_speed })
            })
            .then(res => res.json())
            .then(data => {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = originalBtnHtml;

                if (data.success) {
                    showAlert(data.message, 'success');
                    // 상태 요약 실시간 갱신
                    updateStatusSummaryText(data.device);
                    
                    // 1.5초 뒤 대시보드로 돌아가기
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1500);
                } else {
                    showAlert(data.message, 'error');
                }
            })
            .catch(err => {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = originalBtnHtml;
                console.error('제어 송출 오류:', err);
                showAlert('서버 통신 실패로 IR 송출을 실패했습니다.', 'error');
            });
        });
    }

    // API 알림바 표출 헬퍼 함수
    function showAlert(msg, type) {
        controlAlert.className = `alert-box ${type === 'success' ? 'success-alert' : 'error-alert'}`;
        const icon = controlAlert.querySelector('.alert-icon');
        const text = controlAlert.querySelector('.alert-text');
        
        if (type === 'success') {
            icon.className = 'alert-icon fa-solid fa-circle-check';
        } else {
            icon.className = 'alert-icon fa-solid fa-triangle-exclamation';
        }
        
        text.textContent = msg;
        controlAlert.classList.remove('hidden');
        
        // 4초 후 자동 숨김
        setTimeout(() => {
            controlAlert.classList.add('hidden');
        }, 4000);
    }

    // ---------------------------------------------
    // 5. 기기 삭제 처리
    // ---------------------------------------------
    if (btnDeleteDevice) {
        btnDeleteDevice.addEventListener('click', () => {
            if (confirm(`진짜로 "${deviceName.textContent}" 기기를 삭제하시겠습니까? 등록 정보가 모두 초기화됩니다.`)) {
                fetch(`/api/devices/${DEVICE_ID}/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        window.location.href = '/dashboard';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(err => {
                    console.error('기기 삭제 통신 오류:', err);
                    alert('서버와 통신할 수 없습니다.');
                });
            }
        });
    }

    // 초기 상태 실행
    loadDeviceDetails();
});
