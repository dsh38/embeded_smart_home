import json
from models.auth_model import AuthModel

class DeviceModel:
    @staticmethod
    def get_all_devices():
        """등록된 모든 기기 목록 조회"""
        config = AuthModel._read_config()
        return config.get("devices", [])

    @staticmethod
    def get_device_by_id(device_id):
        """특정 ID의 기기 상세 조회"""
        devices = DeviceModel.get_all_devices()
        for dev in devices:
            if dev.get("id") == device_id:
                return dev
        return None

    @staticmethod
    def add_device(brand, name):
        """기기 등록 (현재는 삼성/LG 에어컨만 가능)"""
        brand = brand.strip().lower()
        if brand not in ["samsung", "lg"]:
            raise ValueError("허용되지 않는 브랜드입니다. 삼성 또는 LG만 등록할 수 있습니다.")
        
        config = AuthModel._read_config()
        devices = config.get("devices", [])
        
        # 새로운 기기 ID 생성
        new_id = 1 if not devices else max(d["id"] for d in devices) + 1
        
        # 신규 에어컨 기기 생성 (기본 기기 상태는 '끄기'로 초기화)
        new_device = {
            "id": new_id,
            "brand": brand,
            "name": name if name else f"{brand.upper()} 에어컨",
            "device_type": "air_conditioner",
            "is_active": False,          # 동작 여부 (기본 OFF)
            "mode": "cool",              # 기본 모드: 냉방 (송풍: fan, 제습: dry 등)
            "target_temp": 24,           # 기본 온도 24도
            "fan_speed": "medium"        # 기본 바람세기: 중
        }
        
        devices.append(new_device)
        config["devices"] = devices
        AuthModel._write_config(config)
        return new_device

    @staticmethod
    def update_device_state(device_id, is_active, mode, target_temp, fan_speed):
        """기기 제어 상태 업데이트 및 정밀 검증"""
        config = AuthModel._read_config()
        devices = config.get("devices", [])
        
        device_found = False
        updated_device = None
        
        for dev in devices:
            if dev.get("id") == device_id:
                # 입력 검증
                # 1. 온도 범위 검증 (송풍 모드일 때는 온도 제한 무시 또는 미표기지만 입력값 검증은 18~30 범위 내)
                if mode != "fan":
                    try:
                        temp_int = int(target_temp)
                        if not (18 <= temp_int <= 30):
                            raise ValueError("온도는 18°C에서 30°C 사이로 설정해야 합니다.")
                        dev["target_temp"] = temp_int
                    except ValueError as e:
                        raise ValueError(f"올바르지 않은 온도 입력입니다: {str(e)}")
                else:
                    # 송풍(fan) 모드인 경우 입력받은 온도가 있다면 일단 저장하되, UI 표시는 제외
                    if target_temp:
                        dev["target_temp"] = int(target_temp)
                
                # 2. 바람세기 검증
                fan_speed = fan_speed.strip().lower()
                if fan_speed not in ["low", "medium", "high", "auto"]:
                    raise ValueError("바람세기는 강(high), 중(medium), 약(low), 자동(auto) 중 하나여야 합니다.")
                
                # 3. 운전모드 검증
                mode = mode.strip().lower()
                if mode not in ["cool", "dry", "fan", "heat"]:
                    raise ValueError("올바르지 않은 운전모드입니다 (냉방, 제습, 송풍, 난방).")

                dev["is_active"] = bool(is_active)
                dev["mode"] = mode
                dev["fan_speed"] = fan_speed
                
                device_found = True
                updated_device = dev
                break
                
        if not device_found:
            raise KeyError("지정된 ID의 기기를 찾을 수 없습니다.")
            
        config["devices"] = devices
        AuthModel._write_config(config)
        return updated_device

    @staticmethod
    def delete_device(device_id):
        """기기 삭제 기능 (유지보수 및 기기 관리 편의성 제공)"""
        config = AuthModel._read_config()
        devices = config.get("devices", [])
        
        initial_count = len(devices)
        devices = [d for d in devices if d["id"] != device_id]
        
        if len(devices) == initial_count:
            return False
            
        config["devices"] = devices
        AuthModel._write_config(config)
        return True
