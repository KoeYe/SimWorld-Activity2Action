import math
import json
import re
from Communicator.unrealcv_delivery import UnrealCvDelivery
from Base import DeliveryMan
from typing import List
from utils.Types import Vector
from Config import Config

class Communicator(UnrealCvDelivery):
    def __init__(self, port, ip, resolution):
        super().__init__(port, ip, resolution)

        self.delivery_manager_name = None

        self.delivery_man_id_to_name = {}

    def delivery_man_turn_around(self, delivery_man_id, angle, clockwise):
        self.d_turn_around(self.get_delivery_man_name(delivery_man_id), 90, 'left')

    def delivery_man_step_forward(self, delivery_man_id):
        self.d_step_forward(self.get_delivery_man_name(delivery_man_id))

    def delivery_man_move_forward(self, delivery_man_id):
        self.d_move_forward(self.get_delivery_man_name(delivery_man_id))

    def delivery_man_stop(self, delivery_man_id):
        self.d_stop(self.get_delivery_man_name(delivery_man_id))

    def delivery_man_rotate(self, delivery_man_id, angle, turn_direction):
        self.d_rotate(self.get_delivery_man_name(delivery_man_id), angle, turn_direction)

    def get_position_and_direction(self, delivery_man_ids):
        try:
            if self.delivery_manager_name is None:
                print("Warning: delivery_manager_name is not set")
                return {}

            info_str = self.get_informations(self.delivery_manager_name)
            if not info_str:
                print("Warning: No information received from Unreal Engine")
                return {}
            # print(f"Received info from UE: {info_str}")  # Debug print
            info = json.loads(info_str)
            result = {}
            d_locations = info["DLocations"]
            d_rotations = info["DRotations"]
            s_locations = info["SLocations"]
            s_rotations = info["SRotations"]
            for delivery_man_id in delivery_man_ids:
                name = self.get_delivery_man_name(delivery_man_id)
                # Parse location
                location_pattern = f"{name}X=(.*?) Y=(.*?) Z="
                match = re.search(location_pattern, d_locations)
                if match:
                    x, y = float(match.group(1)), float(match.group(2))
                    position = Vector(x, y)
                    # Parse rotation
                    rotation_pattern = f"{name}P=.*? Y=(.*?) R="
                    match = re.search(rotation_pattern, d_rotations)
                    if match:
                        direction = float(match.group(1))
                        result[delivery_man_id] = (position, direction)
                    else:
                        print(f"Warning: Could not parse rotation for {name}")
                    continue

                match = re.search(location_pattern, s_locations)
                if match:
                    x, y = float(match.group(1)), float(match.group(2))
                    position = Vector(x, y)
                    # Parse rotation
                    rotation_pattern = f"{name}P=.*? Y=(.*?) R="
                    match = re.search(rotation_pattern, s_rotations)
                    if match:
                        direction = float(match.group(1))
                        result[delivery_man_id] = (position, direction)    
                    else:
                        print(f"Warning: Could not parse rotation for {name}")
                else:
                    print(f"Warning: Could not parse location for {name}")


            return result
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Raw data: {info_str}")
            return {}
        except Exception as e:
            print(f"Error in get_position_and_direction: {e}")
            return {}

    def spawn_delivery_men(self, delivery_men: List[DeliveryMan]):
        for delivery_man in delivery_men:
            name = f'GEN_DELIVERY_MAN_{delivery_man.id}'
            self.delivery_man_id_to_name[delivery_man.id] = name
            model_name = Config.DELIVERY_MAN_MODEL_PATH
            self.spawn_bp_asset(model_name, name)
            # Convert 2D position to 3D (x,y -> x,y,z)
            location_3d = (
                delivery_man.position.x,
                delivery_man.position.y,
                110 # Z coordinate (ground level)
            )
            # Convert 2D direction to 3D orientation (assuming rotation around Z axis)
            orientation_3d = (
                0,  # Pitch
                math.degrees(math.atan2(delivery_man.direction.y, delivery_man.direction.x)),  # Yaw
                0  # Roll
            )
            self.set_location(location_3d, name)
            self.set_orientation(orientation_3d, name)
            self.set_scale((1, 1, 1), name)  # Default scale
            self.set_collision(name, True)
            self.set_movable(name, True)

    def spawn_delivery_manager(self):
        self.delivery_manager_name = 'GEN_DeliveryManager'
        self.spawn_bp_asset(Config.DELIVERY_MANAGER_MODEL_PATH, self.delivery_manager_name)

    def get_delivery_man_name(self, id):
        if id not in self.delivery_man_id_to_name:
            raise ValueError(f"Delivery man with id {id} not found")
        return self.delivery_man_id_to_name[id]


