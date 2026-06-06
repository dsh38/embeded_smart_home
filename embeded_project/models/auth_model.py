import os
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

class AuthModel:
    @staticmethod
    def initialize_config():
        """데이터 폴더 및 config.json 초기 파일 생성"""
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR, exist_ok=True)
            
        if not os.path.exists(Config.CONFIG_FILE):
            # 초기 관리자 정보 (admin / admin) 생성
            initial_data = {
                "user": {
                    "username": "admin",
                    "password_hash": generate_password_hash("admin", method='pbkdf2:sha256')
                },
                "devices": []
            }
            with open(Config.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=4, ensure_ascii=False)
            print("✅ 초기 config.json 파일이 성공적으로 생성되었습니다.")

    @staticmethod
    def _read_config():
        AuthModel.initialize_config()
        try:
            with open(Config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # 오류 발생 시 초기화 후 재시도
            AuthModel.initialize_config()
            with open(Config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

    @staticmethod
    def _write_config(data):
        with open(Config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def verify_login(username, password):
        """사용자 로그인 인증 검증"""
        config = AuthModel._read_config()
        user_info = config.get("user", {})
        
        if user_info.get("username") == username:
            hashed_pw = user_info.get("password_hash")
            if hashed_pw and check_password_hash(hashed_pw, password):
                return True
        return False

    @staticmethod
    def update_credentials(current_username, new_username, current_password, new_password):
        """로그인 아이디 및 비밀번호 변경 (현재 비밀번호 검증 추가)"""
        config = AuthModel._read_config()
        user_info = config.get("user", {})
        hashed_pw = user_info.get("password_hash")
        
        # 1. 현재 비밀번호 검증
        if not hashed_pw or not check_password_hash(hashed_pw, current_password):
            raise ValueError("현재 비밀번호가 올바르지 않습니다.")
        
        # 2. 새로운 사용자명과 새 비밀번호 해시 저장
        config["user"]["username"] = new_username
        config["user"]["password_hash"] = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        AuthModel._write_config(config)
        return True


class LoginAttemptTracker:
    """IP별 로그인 시도 횟수 및 24시간 차단 상태를 파일에 영구 관리하는 트래커"""
    ATTEMPTS_FILE = os.path.join(Config.DATA_DIR, 'login_attempts.json')

    @staticmethod
    def _read_attempts():
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR, exist_ok=True)
            
        if not os.path.exists(LoginAttemptTracker.ATTEMPTS_FILE):
            return {"attempts": {}}
            
        try:
            with open(LoginAttemptTracker.ATTEMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"attempts": {}}

    @staticmethod
    def _write_attempts(data):
        with open(LoginAttemptTracker.ATTEMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def check_block_status(ip):
        """해당 IP의 차단 유무 확인. 차단 시 (True, 남은 시간[초]) 반환, 미차단 시 (False, 0) 반환"""
        data = LoginAttemptTracker._read_attempts()
        attempts = data.get("attempts", {})
        
        if ip not in attempts:
            return False, 0
            
        ip_data = attempts[ip]
        blocked_until_str = ip_data.get("blocked_until")
        
        if not blocked_until_str:
            return False, 0
            
        try:
            blocked_until = datetime.fromisoformat(blocked_until_str)
            now = datetime.now()
            
            if now < blocked_until:
                remaining_seconds = int((blocked_until - now).total_seconds())
                return True, remaining_seconds
            else:
                # 차단 시간이 만료되었으므로 차단 해제 및 실패 횟수 초기화
                ip_data["fail_count"] = 0
                ip_data["blocked_until"] = None
                LoginAttemptTracker._write_attempts(data)
                return False, 0
        except Exception:
            return False, 0

    @staticmethod
    def register_fail(ip):
        """로그인 실패 시 호출. 누적 실패가 10회가 되면 24시간 차단 처리하고 (True, 차단만료시각) 반환"""
        data = LoginAttemptTracker._read_attempts()
        attempts = data.get("attempts", {})
        
        if ip not in attempts:
            attempts[ip] = {"fail_count": 0, "blocked_until": None}
            
        ip_data = attempts[ip]
        ip_data["fail_count"] = ip_data.get("fail_count", 0) + 1
        
        is_blocked = False
        blocked_until_str = None
        
        if ip_data["fail_count"] >= 10:
            # 24시간 차단 설정
            blocked_until = datetime.now() + timedelta(hours=24)
            blocked_until_str = blocked_until.isoformat()
            ip_data["blocked_until"] = blocked_until_str
            is_blocked = True
            
        data["attempts"] = attempts
        LoginAttemptTracker._write_attempts(data)
        return is_blocked, blocked_until_str

    @staticmethod
    def register_success(ip):
        """로그인 성공 시 실패 기록 완전 초기화"""
        data = LoginAttemptTracker._read_attempts()
        attempts = data.get("attempts", {})
        
        if ip in attempts:
            del attempts[ip]
            data["attempts"] = attempts
            LoginAttemptTracker._write_attempts(data)
