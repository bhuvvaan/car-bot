from hyundai_kia_connect_api import VehicleManager
from dotenv import load_dotenv
import os

load_dotenv()

def create_vehicle_manager():
    
    # Region codes: 1=Europe, 2=Canada, 3=USA, 4=Korea
    # Brand codes: 2=Hyundai, 1=Kia, 3=Genesis
    vm = VehicleManager(
        region=int(os.getenv("BLUELINK_REGION", "3")),
        brand=int(os.getenv("BLUELINK_BRAND", "2")),
        username=os.getenv("BLUELINK_USERNAME"),
        password=os.getenv("BLUELINK_PASSWORD"),
        pin=os.getenv("BLUELINK_PIN")
    )

    print("Connecting to Bluelink...")
    vm.check_and_refresh_token()
    vm.update_all_vehicles_with_cached_state()
    
    return vm

def get_car_details():

    vm = create_vehicle_manager()

    print("\nVehicles found:")
    for vehicle_id, vehicle in vm.vehicles.items():
        print(f"\nVehicle: {vehicle.name}")
        print(f"  Model: {vehicle.model}")
        print(f"  Battery: {vehicle.ev_battery_percentage}%")
        print(f"  Range: {vehicle.ev_driving_range} miles")
        print(f"  Locked: {vehicle.is_locked}")
        print(f"  Location: {vehicle.location_latitude}, {vehicle.location_longitude}")

if __name__ == '__main__':
    get_car_details()