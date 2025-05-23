from Communicator.unrealcv_basic import UnrealCV
import threading

import numpy as np

class UnrealCvA2A(UnrealCV):
    def __init__(self, ip, port, resolution):
        super().__init__(ip, port, resolution)
        self.lock = threading.Lock()

    def d_move_forward(self, object_name):
        with self.lock:
            cmd = f'vbp {object_name} MoveForward'
            self.client.request(cmd)
    # def d_move_forward_sec(self, object_name, sec):
    #     with self.lock:
    #         self.apply_action_transition(object_name, 'MoveForward', sec)

    def d_rotate(self, object_name, angle, direction='left'):
        if direction == 'right':
            clockwise = 1
        elif direction == 'left':
            angle = -angle
            clockwise = -1
        with self.lock:
            cmd = f'vbp {object_name} Rotate_Angle {1} {angle} {clockwise}'
            self.client.request(cmd)

    def d_turn_around(self, object_name, angle, direction='left'):
        if direction == 'right':
            clockwise = 1
        elif direction == 'left':
            angle = -angle
            clockwise = -1
        with self.lock:
            cmd = f'vbp {object_name} TurnAround {angle} {clockwise}'
            self.client.request(cmd)
            
    def d_get_location(self,object_name):
        with self.lock:
            try:
                cmd = f'vget /object/{object_name}/location'
                res = self.client.request(cmd)
                location = [float(i) for i in res.split()]
                return np.array(location)
            except Exception as e:
                print(f"Error occurred in {__file__}:{e.__traceback__.tb_lineno}")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print(f"Error traceback:")
                print('res:', res)
                
    def d_get_rotation(self, object_name):
        with self.lock:
            try:
                cmd = f'vget /object/{object_name}/rotation'
                res = self.client.request(cmd)
                rotation = [float(i) for i in res.split()]
                return np.array(rotation)
            except Exception as e:
                print(f"Error occurred in {__file__}:{e.__traceback__.tb_lineno}")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print(f"Error traceback:")
                print('res:', res)

    def d_step_forward(self, object_name):
        with self.lock:
            cmd = f'vbp {object_name} StepForward'
            self.client.request(cmd)

    def d_stop(self, object_name):
        with self.lock:
            cmd = f'vbp {object_name} StopDeliveryMan'
            self.client.request(cmd)

    def get_camera_observation(self, camera_id, viewmode='lit'):
        with self.lock:
            return self.read_image(camera_id, viewmode, 'fast')