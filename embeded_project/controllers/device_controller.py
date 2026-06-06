from flask import Blueprint, request, jsonify, session
from models.device_model import DeviceModel
from hardware.ir_driver import UniversalACTransmitter

device_bp = Blueprint('device', __name__)

# IR 제어 드라이버 초기화 (전역 인스턴스 싱글톤 형태로 재사용)
ir_transmitter = UniversalACTransmitter()

def login_required(f):
    """로그인 상태 확인을 위한 데코레이터"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        return f(*args, **kwargs)
    return decorated_function

@device_bp.route('/api/devices', methods=['GET'])
@login_required
def get_devices():
    """모든 등록 가전 리스트 조회"""
    devices = DeviceModel.get_all_devices()
    return jsonify({'success': True, 'devices': devices})

@device_bp.route('/api/devices/register', methods=['POST'])
@login_required
def register_device():
    """새로운 에어컨 가전 기기 추가 등록"""
    data = request.get_json() or {}
    brand = data.get('brand')
    name = data.get('name')
    
    if not brand:
        return jsonify({'success': False, 'message': '가전 브랜드를 선택해주세요.'}), 400
        
    try:
        new_device = DeviceModel.add_device(brand, name)
        return jsonify({'success': True, 'device': new_device, 'message': '기기가 성공적으로 등록되었습니다.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@device_bp.route('/api/devices/<int:device_id>', methods=['GET'])
@login_required
def get_device_detail(device_id):
    """특정 가전 기기 상세 상태 조회"""
    device = DeviceModel.get_device_by_id(device_id)
    if not device:
        return jsonify({'success': False, 'message': '기기를 찾을 수 없습니다.'}), 404
    return jsonify({'success': True, 'device': device})

@device_bp.route('/api/devices/<int:device_id>/control', methods=['POST'])
@login_required
def control_device(device_id):
    """가전 기기 제어 명령 수신 및 물리 IR 송출 작동"""
    data = request.get_json() or {}
    is_active = data.get('is_active')          # True(켜기), False(끄기)
    mode = data.get('mode')                    # cool, dry, fan, heat
    target_temp = data.get('target_temp')      # 18 ~ 30
    fan_speed = data.get('fan_speed')          # low, medium, high, auto
    
    # 1. DB 모델 업데이트 및 입력값 검증 검사
    try:
        updated_dev = DeviceModel.update_device_state(
            device_id=device_id,
            is_active=is_active,
            mode=mode,
            target_temp=target_temp,
            fan_speed=fan_speed
        )
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except KeyError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
        
    # 2. 물리 IR 송출 모듈 연동 작동
    # DB에 정상 업데이트되었으므로 실제 하드웨어 신호를 발송합니다.
    success = ir_transmitter.control_ac(
        brand=updated_dev['brand'],
        is_active=updated_dev['is_active'],
        mode=updated_dev['mode'],
        target_temp=updated_dev['target_temp'],
        fan_speed=updated_dev['fan_speed']
    )
    
    if success:
        return jsonify({
            'success': True, 
            'device': updated_dev, 
            'message': '제어 명령이 IR 신호로 성공적으로 전송되었습니다.'
        })
    else:
        return jsonify({
            'success': True, 
            'device': updated_dev, 
            'message': '제어 값은 변경되었으나, 실제 IR 펄스 송출은 지연/실패했습니다 (시뮬레이터 모드 작동).'
        })

@device_bp.route('/api/devices/<int:device_id>/delete', methods=['POST'])
@login_required
def delete_device(device_id):
    """기기 삭제 API"""
    success = DeviceModel.delete_device(device_id)
    if success:
        return jsonify({'success': True, 'message': '기기가 삭제되었습니다.'})
    return jsonify({'success': False, 'message': '삭제할 기기를 찾을 수 없습니다.'}), 404
