from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.ApiImpl import ClimateRequestOptions
from dotenv import load_dotenv
import os
import time
import requests

load_dotenv()

# Region codes: 1=Europe, 2=Canada, 3=USA, 4=Korea
# Brand codes: 2=Hyundai, 1=Kia, 3=Genesis
vm = VehicleManager(
    region=int(os.getenv("BLUELINK_REGION", "3")),
    brand=int(os.getenv("BLUELINK_BRAND", "2")),
    username=os.getenv("BLUELINK_USERNAME"),
    password=os.getenv("BLUELINK_PASSWORD"),
    pin=os.getenv("BLUELINK_PIN")
)


def get_address_from_coordinates(latitude, longitude):
    """Convert GPS coordinates to a street address using OpenStreetMap."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "zoom": 18
            },
            headers={
                "User-Agent": "PersonalCarBot/1.0"  # Required by Nominatim
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("display_name", "Address not found")
        else:
            return "Could not look up address"
    except Exception as e:
        print(f"Address lookup error: {e}")
        return "Address lookup failed"

#implement caching
_last_refresh_time = 0
_cache_duration = 60

def refresh_vehicle_manager():
    global _last_refresh_time
    
    now = time.time()
    
    if _last_refresh_time != 0 and (now - _last_refresh_time) < _cache_duration:
        print(f"Using cached data ({int(now - _last_refresh_time)}s old)")
        return
    
    # Cache expired or first call, do refresh
    print("Refreshing connection to Bluelink...")
    try:
        vm.check_and_refresh_token()
        vm.update_all_vehicles_with_cached_state()
        _last_refresh_time = now
        print("Refresh successful")
    except Exception as e:
        print(f"Refresh failed: {e}")
        _last_refresh_time = now  # Still update to avoid hammering
        raise

        
def tool_get_battery_status():
    """Will send to bluelink api and get battery percentage and available range"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    return f"Battery: {vehicle.ev_battery_percentage}% and Range: {vehicle.ev_driving_range} miles"

def tool_get_lock_status():
    """Will send to bluelink api and get lock/unlock status"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    return f"Locked: {vehicle.is_locked}"

def tool_get_location():
    """Will send to bluelink api and get location of car"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    address = get_address_from_coordinates(vehicle.location_latitude, vehicle.location_longitude)
    return f"Location: {address}"

def tool_lock_car():
    """Will lock the car"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    try:
        result = vm.lock(vehicle.id)
        return f"Car locked successfully. Result: {result}"
    except Exception as e:
        # Library bug: Hyundai USA API returns non-JSON, but the command succeeds
        print(f"Lock command sent (parse error: {e})")
        return "Lock command sent to the car. It should be locked now."

def tool_unlock_car():
    """Will unlock the car"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    try:
        result = vm.unlock(vehicle.id)
        return f"Car unlocked successfully. Result: {result}"
    except Exception as e:
        # Library bug: Hyundai USA API returns non-JSON, but the command succeeds
        print(f"Unlock command sent (parse error: {e})")
        return "Unlock command sent to the car. It should be unlocked now."

'''
def tool_start_climate(temperature: float = 72, duration: int = 5, defrost: bool = False, front_left_seat: int = 0):
    """Will start climate in the car"""
    refresh_vehicle_manager()
    vehicle = list(vm.vehicles.values())[0]
    options = ClimateRequestOptions(set_temp= temperature, duration=duration, defrost=defrost, front_left_seat=front_left_seat, climate=True)
    try:
        result = vm.start_climate(vehicle.id, options)
        return f"Climate started at {temperature}°F for {duration} min. Defrost: {defrost}."
    except Exception as e:
        print(f"Climate command sent (parse error: {e})")
        return f"Climate start command sent at {temperature}°F"
'''

def get_car_details():

    refresh_vehicle_manager()

    print("\nVehicles found:")
    for vehicle_id, vehicle in vm.vehicles.items():
        print(f"\nVehicle: {vehicle.name}")
        print(f"  Model: {vehicle.model}")
        print(f"  Battery: {vehicle.ev_battery_percentage}%")
        print(f"  Range: {vehicle.ev_driving_range} miles")
        print(f"  Locked: {vehicle.is_locked}")
        print(f"  Location: {vehicle.location_latitude}, {vehicle.location_longitude}")

if __name__ == '__main__':
    print(tool_get_battery_status())
    print(tool_get_lock_status())