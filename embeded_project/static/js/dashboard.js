// ==========================================================================
// 메인 대시보드 패널 클라이언트 스크립트 (dashboard.js)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // DOM 요소 캐싱
    const sensorTemp = document.getElementById('sensor-temp');
    const sensorHumi = document.getElementById('sensor-humi');
    const refreshBadge = document.getElementById('refresh-badge');
    const devicesContainer = document.getElementById('devices-container');
    const noDevicesState = document.getElementById('no-devices-state');
    
    // 모달 관련 버튼 및 폼
    const btnOpenRegister = document.getElementById('btn-open-register');
    const btnEmptyRegister = document.getElementById('btn-empty-register');
    const registerForm = document.getElementById('register-device-form');
    const regErrorMessage = document.getElementById('reg-error-message');
    
    const btnOpenChangePw = document.getElementById('btn-open-change-pw');
    const changePwForm = document.getElementById('change-pw-form');
    const pwErrorMessage = document.getElementById('pw-error-message');
    const pwSuccessMessage = document.getElementById('pw-success-message');

    // 한글 변환 매핑 딕셔너리
    const modeKorean = {
        'cool': '냉방',
        'dry': '제습',
        'fan': '송풍',
        'heat': '난방'
    };

    const fanSpeedKorean = {
        'high': '강',
        'medium': '중',
        'low': '약',
        'auto': '자동'
    };

    // ---------------------------------------------
    // 1. 실시간 온습도 센서 모니터링 (10초 주기 갱신)
    // ---------------------------------------------
    function fetchSensorData() {
        // 리프레시 애니메이션 활성화
        if (refreshBadge) {
            refreshBadge.classList.add('refreshing');
            const icon = refreshBadge.querySelector('i');
            icon.classList.add('fa-spin');
        }

        fetch('/api/sensor/dht22')
            .then(res => {
                if (res.status === 401) {
                    // 세션 만료 시 로그인 이동
                    window.location.href = '/login';
                }
                return res.json();
            })
            .then(data => {
                if (data.success) {
                    // 서서히 갱신되는 시각 효과 추가 (Fade Effect)
                    animateValueUpdate(sensorTemp, data.temperature.toFixed(1));
                    animateValueUpdate(sensorHumi, data.humidity.toFixed(1));
                }
            })
            .catch(err => console.error('센서 데이터 로드 중 통신 에러:', err))
            .finally(() => {
                // 1.5초 후 갱신 애니메이션 리셋
                setTimeout(() => {
                    if (refreshBadge) {
                        refreshBadge.classList.remove('refreshing');
                    }
                }, 1500);
            });
    }

    // 값 업데이트 시 부드럽게 깜빡이는 CSS 애니메이션 지원 함수
    function animateValueUpdate(element, newValue) {
        if (element.textContent !== newValue) {
            element.style.opacity = '0.3';
            setTimeout(() => {
                element.textContent = newValue;
                element.style.opacity = '1';
                element.style.transition = 'opacity 0.4s ease';
            }, 300);
        }
    }

    // 초기 로딩 후 10초마다 갱신 주기 작동
    fetchSensorData();
    setInterval(fetchSensorData, 10000);

    // ---------------------------------------------
    // 2. 가전 기기 목록 조회 및 카드 동적 렌더링
    // ---------------------------------------------
    function loadDevices() {
        fetch('/api/devices')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderDeviceCards(data.devices);
                }
            })
            .catch(err => {
                console.error('기기 목록 로드 실패:', err);
                devicesContainer.innerHTML = `
                    <div class="error-state">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <p>가전 목록을 불러오는 중 통신 에러가 발생했습니다.</p>
                    </div>
                `;
            });
    }

    function renderDeviceCards(devices) {
        devicesContainer.innerHTML = '';
        
        if (!devices || devices.length === 0) {
            noDevicesState.classList.remove('hidden');
            devicesContainer.classList.add('hidden');
            return;
        }

        noDevicesState.classList.add('hidden');
        devicesContainer.classList.remove('hidden');

        devices.forEach(dev => {
            const card = document.createElement('div');
            card.className = `device-card ${dev.is_active ? 'active' : ''}`;
            card.dataset.id = dev.id;
            
            // 삼성/LG 에어컨 아이콘
            const brandIcon = dev.brand === 'samsung' 
                ? '<i class="fa-solid fa-snowflake text-indigo"></i>' 
                : '<i class="fa-solid fa-certificate text-red"></i>';
                
            // 기기 동작 뱃지 및 간편 조작 단추 구성
            const quickPowerBtn = dev.is_active
                ? `<button class="btn-quick-power off" data-id="${dev.id}"><i class="fa-solid fa-power-off"></i> 끄기</button>`
                : `<button class="btn-quick-power on" data-id="${dev.id}"><i class="fa-solid fa-power-off"></i> 켜기</button>`;
                
            const powerBadge = dev.is_active 
                ? '<span class="state-badge on"><i class="fa-solid fa-circle-play"></i> 운전 중</span>' 
                : '<span class="state-badge off"><i class="fa-solid fa-circle-stop"></i> 꺼짐</span>';
            
            // 가전 상태 정보 구성 (송풍인 경우 온도 표기 제외)
            let statusItemsHtml = '';
            if (dev.is_active) {
                // 운전모드 한글 변환
                const modeName = modeKorean[dev.mode] || dev.mode;
                statusItemsHtml += `
                    <div class="summary-item">
                        <i class="fa-solid fa-circle-nodes"></i>
                        <span>모드: <strong>${modeName}</strong></span>
                    </div>
                `;

                // 설정 희망온도 (송풍 모드일 때는 표기 제외)
                if (dev.mode !== 'fan') {
                    statusItemsHtml += `
                        <div class="summary-item">
                            <i class="fa-solid fa-temperature-three-quarters"></i>
                            <span>희망: <strong>${dev.target_temp}°C</strong></span>
                        </div>
                    `;
                }

                // 바람세기 한글화
                const speedName = fanSpeedKorean[dev.fan_speed] || dev.fan_speed;
                statusItemsHtml += `
                    <div class="summary-item">
                        <i class="fa-solid fa-fan"></i>
                        <span>바람: <strong>${speedName}</strong></span>
                    </div>
                `;
            } else {
                statusItemsHtml = `
                    <div class="summary-item text-muted">
                        <i class="fa-solid fa-circle-info"></i>
                        <span>제어 대기 상태 (마지막 작동 기준)</span>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="card-top">
                    <div class="device-title">
                        <span class="device-brand ${dev.brand}">${dev.brand}</span>
                        <h4>${dev.name}</h4>
                    </div>
                    <div class="brand-badge-wrapper ${dev.brand}">
                        ${brandIcon}
                    </div>
                </div>
                <div class="card-middle">
                    <div class="status-summary-list">
                        ${statusItemsHtml}
                    </div>
                </div>
                <div class="card-bottom">
                    <div class="card-bottom-actions">
                        ${quickPowerBtn}
                        ${powerBadge}
                    </div>
                </div>
            `;

            // 클릭 시 기기 상세 패널 페이지 이동 바인딩
            card.addEventListener('click', () => {
                window.location.href = `/devices/${dev.id}`;
            });

            // 간편 전원 조작 단추 클릭 바인딩 및 전파 중단
            const quickBtn = card.querySelector('.btn-quick-power');
            if (quickBtn) {
                quickBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // 상세페이지 리다이렉트 카드 클릭 전파 차단
                    
                    const deviceId = quickBtn.dataset.id;
                    const willTurnOn = quickBtn.classList.contains('on');
                    
                    // 페이로드 구성 (켜기: 냉방/24도/강, 끄기: 전원 차단)
                    const payload = {
                        is_active: willTurnOn,
                        mode: 'cool',
                        target_temp: 24,
                        fan_speed: 'high'
                    };
                    
                    quickBtn.disabled = true;
                    quickBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

                    fetch(`/api/devices/${deviceId}/control`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            loadDevices(); // 화면 즉각 리렌더링
                        } else {
                            alert(data.message || '전원 제어 명령 송출 실패');
                            loadDevices();
                        }
                    })
                    .catch(err => {
                        console.error('간편 전원 제어 에러:', err);
                        alert('네트워크 통신에 실패했습니다.');
                        loadDevices();
                    });
                });
            }

            devicesContainer.appendChild(card);
        });
    }

    loadDevices();

    // ---------------------------------------------
    // 3. 기기 등록 모달 처리
    // ---------------------------------------------
    if (btnOpenRegister) btnOpenRegister.addEventListener('click', () => openModal('modal-register-device'));
    if (btnEmptyRegister) btnEmptyRegister.addEventListener('click', () => openModal('modal-register-device'));

    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            regErrorMessage.classList.add('hidden');

            const brand = document.getElementById('reg-brand').value;
            const name = document.getElementById('reg-name').value.trim();

            if (!brand || !name) {
                showRegError('모든 필드를 올바르게 입력해 주세요.');
                return;
            }

            fetch('/api/devices/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ brand, name })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    closeModal('modal-register-device');
                    registerForm.reset();
                    loadDevices(); // 리로드
                } else {
                    showRegError(data.message);
                }
            })
            .catch(err => {
                console.error('기기 등록 에러:', err);
                showRegError('서버와의 통신에 실패했습니다.');
            });
        });
    }

    function showRegError(msg) {
        if (regErrorMessage) {
            regErrorMessage.querySelector('.alert-text').textContent = msg;
            regErrorMessage.classList.remove('hidden');
        }
    }

    // ---------------------------------------------
    // 4. 계정 정보 및 비밀번호 변경 모달 처리 (v2 개편)
    // ---------------------------------------------
    const currentUsernameText = document.getElementById('current-username-text');
    const btnEnableUsernameEdit = document.getElementById('btn-enable-username-edit');
    const newUsernameInputGroup = document.getElementById('new-username-input-group');
    const newUsernameInput = document.getElementById('new-username');

    // 글로벌 모달 오픈 함수 바인딩 (base.html 헤더 내계정 드롭다운 버튼에서 호출)
    window.openChangePwModal = function() {
        openModal('modal-change-password');
        pwErrorMessage.classList.add('hidden');
        pwSuccessMessage.classList.add('hidden');
        changePwForm.reset();
        
        // 아이디 편집 영역 초기 상태로 잠금
        newUsernameInputGroup.classList.add('hidden');
        newUsernameInput.value = currentUsernameText.textContent;
        newUsernameInput.required = false;
        btnEnableUsernameEdit.textContent = '아이디 변경';
        btnEnableUsernameEdit.classList.remove('active');
    };

    // 타 페이지(예: 기기 제어페이지) 드롭다운에서 타고 들어온 리다이렉션 파라미터 감지 처리
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('openSettings') === 'true') {
        // 주소창 파라미터 흔적 제거
        window.history.replaceState({}, document.title, window.location.pathname);
        setTimeout(window.openChangePwModal, 300);
    }

    // 아이디 변경 토글 버튼 동작
    if (btnEnableUsernameEdit && newUsernameInputGroup) {
        btnEnableUsernameEdit.addEventListener('click', () => {
            const isEditing = !newUsernameInputGroup.classList.contains('hidden');
            
            if (isEditing) {
                // 편집 취소 상태
                newUsernameInputGroup.classList.add('hidden');
                newUsernameInput.value = currentUsernameText.textContent; // 값 롤백
                newUsernameInput.required = false;
                btnEnableUsernameEdit.textContent = '아이디 변경';
                btnEnableUsernameEdit.classList.remove('active');
            } else {
                // 편집 활성화 상태
                newUsernameInputGroup.classList.remove('hidden');
                newUsernameInput.required = true;
                newUsernameInput.focus();
                btnEnableUsernameEdit.textContent = '변경 취소';
                btnEnableUsernameEdit.classList.add('active');
            }
        });
    }

    if (changePwForm) {
        changePwForm.addEventListener('submit', (e) => {
            e.preventDefault();
            pwErrorMessage.classList.add('hidden');
            pwSuccessMessage.classList.add('hidden');

            const currentPassword = document.getElementById('current-password').value;
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            // 아이디 편집 활성화 상태에 맞춰 전송 사용자명 결정
            let newUsername = currentUsernameText.textContent;
            if (!newUsernameInputGroup.classList.contains('hidden')) {
                newUsername = newUsernameInput.value.trim();
            }

            if (!newUsername) {
                showPwError('변경할 아이디를 입력해 주세요.');
                return;
            }

            if (!currentPassword) {
                showPwError('본인 확인을 위해 현재 비밀번호를 입력해야 합니다.');
                return;
            }

            if (!newPassword || !confirmPassword) {
                showPwError('새로운 비밀번호를 입력해 주세요.');
                return;
            }

            // 새로운 비밀번호 간 대조 검사
            if (newPassword !== confirmPassword) {
                showPwError('새로운 비밀번호와 비밀번호 확인 값이 서로 일치하지 않습니다.');
                return;
            }

            // 계정 변경 API 요청 전송 (3단계 데이터 결합)
            fetch('/api/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_username: newUsername,
                    current_password: currentPassword,
                    new_password: newPassword
                })
            })
            .then(res => res.json().then(data => ({ status: res.status, body: data })))
            .then(({ status, body }) => {
                if (body.success) {
                    pwSuccessMessage.querySelector('.alert-text').textContent = body.message;
                    pwSuccessMessage.classList.remove('hidden');
                    
                    // 기기 저장 성공 시 1.5초 후 대시보드 강제 리프레시 반영
                    setTimeout(() => {
                        closeModal('modal-change-password');
                        changePwForm.reset();
                        window.location.reload();
                    }, 1500);
                } else {
                    showPwError(body.message || '정보 변경 중 오류가 발생했습니다.');
                }
            })
            .catch(err => {
                console.error('계정 정보 변경 API 통신 에러:', err);
                showPwError('서버와의 통신에 실패했습니다.');
            });
        });
    }

    function showPwError(msg) {
        if (pwErrorMessage) {
            pwErrorMessage.querySelector('.alert-text').textContent = msg;
            pwErrorMessage.classList.remove('hidden');
        }
    }
});

// 전역 모달 컨트롤 도우미 함수
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}
