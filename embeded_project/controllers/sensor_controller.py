from flask import Blueprint, jsonify, session
from hardware.dht22_driver import DHT22SensorReader

sensor_bp = Blueprint('sensor', __name__)

# 온습도 센서 리더 객체 싱글톤 구조로 관리
dht_reader = DHT22SensorReader()

@sensor_bp.route('/api/sensor/dht22', methods=['GET'])
def get_sensor_data():
    """DHT22 센서 실시간 측정 데이터 조회 API (10초 주기 갱신용)"""
    # UI 화면 보안 검사 (비로그인 시에는 측정값 노출 차단)
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
    temp, humi = dht_reader.read_data()
    
    if temp is not None and humi is not None:
        return jsonify({
            'success': True,
            'temperature': temp,
            'humidity': humi
        })
    else:
        return jsonify({
            'success': False,
            'message': '센서 데이터 조회 실패 (센서 연결 상태를 확인해 주세요)'
        }), 500
