// ==========================================================================
// 로그인 페이지 클라이언트 스크립트 (auth.js)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const rememberCheckbox = document.getElementById('remember');
    const togglePasswordBtn = document.getElementById('toggle-password');
    const errorMessage = document.getElementById('error-message');

    // 1. 비밀번호 보이기 / 숨기기 토글
    if (togglePasswordBtn) {
        togglePasswordBtn.addEventListener('click', () => {
            const icon = togglePasswordBtn.querySelector('i');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }
        });
    }

    // 2. 로그인 API 전송
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // 오류 알림 초기화
            errorMessage.classList.add('hidden');
            
            const username = usernameInput.value.trim();
            const password = passwordInput.value;
            const remember = rememberCheckbox.checked;

            if (!username || !password) {
                showError('아이디와 비밀번호를 입력해 주세요.');
                return;
            }

            // 로그인 요청 데이터
            const requestData = {
                username: username,
                password: password,
                remember: remember
            };

            // 버튼 로딩 상태 표시
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalBtnHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 로그인 처리 중...';

            fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            })
            .then(response => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
                return response.json().then(data => ({ status: response.status, body: data }));
            })
            .then(({ status, body }) => {
                if (status === 200 && body.success) {
                    // 로그인 성공 시 대시보드로 이동
                    window.location.href = '/dashboard';
                } else {
                    // 로그인 실패 알림
                    showError(body.message || '로그인에 실패했습니다. 다시 시도해 주세요.');
                }
            })
            .catch(err => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
                console.error('로그인 API 통신 에러:', err);
                showError('서버 통신 오류가 발생했습니다. 네트워크 상태를 확인하세요.');
            });
        });
    }

    // 오류 표시 도우미 함수
    function showError(message) {
        if (errorMessage) {
            const textSpan = errorMessage.querySelector('.alert-text');
            textSpan.textContent = message;
            errorMessage.classList.remove('hidden');
            
            // 살짝 흔들리는 진동 효과 가미
            errorMessage.classList.remove('shake-animate');
            void errorMessage.offsetWidth; // 리플로우 트리거
            errorMessage.classList.add('shake-animate');
        }
    }
});
