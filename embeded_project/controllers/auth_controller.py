import logging
from flask import Blueprint, request, jsonify, session
from models.auth_model import AuthModel, LoginAttemptTracker

auth_bp = Blueprint('auth', __name__)

# 로깅 환경 셋업 (콘솔 표준 오류/출력 스트림에 경고 로그 활성화)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s: %(message)s')

def get_client_ip(req):
    """Cloudflare 프록시 대응 실제 접속 클라이언트 IP 필터링 함수"""
    # 1. Cloudflare 전용 실제 IP 헤더 확인
    cf_ip = req.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip.strip()
        
    # 2. 일반 리버스 프록시 헤더 확인 (X-Forwarded-For는 프록시를 거칠 때마다 IP가 누적되므로 첫 번째 IP가 실제 IP)
    xff = req.headers.get('X-Forwarded-For')
    if xff:
        # 쉼표로 구분된 첫 번째 IP 추출
        return xff.split(',')[0].strip()
        
    # 3. 로컬 직접 접속 시 Fallback 기본 소켓 원격 IP
    return req.remote_addr

def format_remaining_time(seconds):
    """초 단위를 시인성 좋은 한글 시간 스트링으로 변환"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}시간 {minutes}분"
    else:
        seconds_remain = seconds % 60
        return f"{minutes}분 {seconds_remain}초"

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """로그인 처리 API (브루트포스 IP 차단 기능 탑재)"""
    client_ip = get_client_ip(request)
    
    # 1. 해당 IP의 차단 상태 선행 확인
    is_blocked, remaining_seconds = LoginAttemptTracker.check_block_status(client_ip)
    if is_blocked:
        # [요구사항] 차단된 상태에서 로그인 시도 시 마찬가지로 로그를 서버 콘솔에 띄움
        logging.warning(f"[WARNING] Blocked IP {client_ip} attempted to login.")
        
        time_str = format_remaining_time(remaining_seconds)
        return jsonify({
            'success': False, 
            'message': f'보안 위험으로 인해 이 IP의 로그인 시도가 일시 차단되었습니다. 남은 시간: {time_str}'
        }), 403

    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False) # 자동 로그인 플래그
    
    if not username or not password:
        return jsonify({'success': False, 'message': '아이디와 비밀번호를 모두 입력해주세요.'}), 400
        
    # 2. 관리자 비밀번호 검증
    if AuthModel.verify_login(username, password):
        # 로그인 성공 -> 이 IP의 누적 실패 횟수 완전 리셋
        LoginAttemptTracker.register_success(client_ip)
        
        # 세션 저장
        session.clear()
        session['username'] = username
        session['logged_in'] = True
        
        if remember:
            session.permanent = True # 자동 로그인 활성화 (30일 유지)
            
        return jsonify({'success': True, 'message': '로그인에 성공했습니다.'})
    else:
        # 로그인 실패 -> 실패 카운트 증가
        is_now_blocked, blocked_until = LoginAttemptTracker.register_fail(client_ip)
        
        if is_now_blocked:
            # [요구사항] 10회 달성하여 차단 활성화 시점에 서버 콘솔에 경고 로그 표출
            logging.warning(f"[WARNING] IP {client_ip} has been blocked for 24 hours due to 10 consecutive login failures.")
            return jsonify({
                'success': False,
                'message': '비밀번호 입력 오류가 10회 누적되어 이 IP는 24시간 동안 로그인 접속이 차단되었습니다.'
            }), 403
        else:
            # 아직 10회 미만인 경우 누적 실패 경고 노출
            attempts_data = LoginAttemptTracker._read_attempts()
            current_fails = attempts_data.get("attempts", {}).get(client_ip, {}).get("fail_count", 0)
            
            return jsonify({
                'success': False, 
                'message': f'아이디 또는 비밀번호가 일치하지 않습니다. (누적 실패 횟수: {current_fails}/10)'
            }), 401

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """로그아웃 처리 API"""
    session.clear()
    return jsonify({'success': True, 'message': '로그아웃 되었습니다.'})

@auth_bp.route('/api/auth-check', methods=['GET'])
def auth_check():
    """로그인 상태 확인 API"""
    if session.get('logged_in'):
        return jsonify({'logged_in': True, 'username': session.get('username')})
    return jsonify({'logged_in': False}), 401

@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    """관리자 계정 정보 및 비밀번호 수정 API (현재 패스워드 대조 포함)"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '권한이 없습니다. 로그인이 필요합니다.'}), 401
        
    data = request.get_json() or {}
    new_username = data.get('new_username')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not new_username or not current_password or not new_password:
        return jsonify({'success': False, 'message': '현재 비밀번호와 새 아이디, 새 비밀번호를 모두 입력해주세요.'}), 400
        
    current_username = session.get('username')
    
    try:
        AuthModel.update_credentials(current_username, new_username, current_password, new_password)
        # 정보 변경 후 세션 상태 갱신
        session['username'] = new_username
        return jsonify({'success': True, 'message': '로그인 정보가 성공적으로 변경되었습니다.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'비밀번호 변경 실패: {str(e)}'}), 500
