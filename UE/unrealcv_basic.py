import unrealcv
import cv2
import time
import PIL.Image
from io import BytesIO
import numpy as np
import json

class UnrealCV(object):
    def __init__(self, port, ip, resolution):
        self.ip = ip
        # build a client to connect to the env
        self.client = unrealcv.Client((ip, port))
        self.client.connect()

        self.resolution = resolution
        self.ini_unrealcv(resolution)

    def ini_unrealcv(self, resolution=(320, 240)):
        self.check_connection()
        [w, h] = resolution
        self.client.request(f'vrun setres {w}x{h}w', -1)  # set resolution of the display window
        self.client.request('DisableAllScreenMessages', -1)  # disable all screen messages
        self.client.request('vrun sg.ShadowQuality 0', -1)  # set shadow quality to low
        self.client.request('vrun sg.TextureQuality 0', -1)  # set texture quality to low
        self.client.request('vrun sg.EffectsQuality 0', -1)  # set effects quality to low
        time.sleep(0.1)
        self.client.message_handler = self.message_handler

    def message_handler(self, message):
        msg = message

    def check_connection(self):
        while self.client.isconnected() is False:
            print('UnrealCV server is not running. Please try again')
            time.sleep(1)
            self.client.connect()

    def spawn(self, prefab, name):
        cmd = f'vset /objects/spawn {prefab} {name}'
        self.client.request(cmd)

    def spawn_bp_asset(self, prefab_path, name):
        cmd = f'vset /objects/spawn_bp_asset {prefab_path} {name}'
        self.client.request(cmd)

    def clean_garbage(self):
        self.client.request("vset /action/clean_garbage")

    def set_location(self, loc, name):
        [x, y, z] = loc
        cmd = f'vset /object/{name}/location {x} {y} {z}'
        self.client.request(cmd)

    def set_orientation(self, orientation, name):
        [pitch, yaw, roll] = orientation
        cmd = f'vset /object/{name}/rotation {pitch} {yaw} {roll}'
        self.client.request(cmd)

    def set_scale(self, scale, name):
        [x, y, z] = scale
        cmd = f'vset /object/{name}/scale {x} {y} {z}'
        self.client.request(cmd)

    def enable_controller(self, name, enable_controller):
        cmd = f'vbp {name} EnableController {enable_controller}'
        self.client.request(cmd)

    def set_physics(self, actor_name, hasPhysics):
        cmd = f'vset /object/{actor_name}/physics {hasPhysics}'
        self.client.request(cmd)

    def set_collision(self, actor_name, hasCollision):
        cmd = f'vset /object/{actor_name}/collision {hasCollision}'
        self.client.request(cmd)

    def set_movable(self, actor_name, isMovable):
        cmd = f'vset /object/{actor_name}/object_mobility {isMovable}'
        self.client.request(cmd)

    def destroy(self, actor_name):
        cmd = f'vset /object/{actor_name}/destroy'
        self.client.request(cmd)

    def apply_action_transition(self, robot_name, action):
        [speed, duration, direction] = action
        if speed < 0:
            # switch the direction
            if direction == 0:
                direction = 1
            elif direction == 1:
                direction = 0
            elif direction == 2:
                direction = 3
            elif direction == 3:
                direction = 2
        cmd = f'vbp {robot_name} Move_Speed {speed} {duration} {direction}'
        self.client.request(cmd)
        # time.sleep(duration)

    def apply_action_rotation(self, robot_name, action):
        [duration, angle, direction] = action
        cmd = f'vbp {robot_name} Rotate_Angle {duration} {angle} {direction}'
        self.client.request(cmd)
        time.sleep(duration)

    def get_objects(self):
        res = self.client.request('vget /objects')
        objects = np.array(res.split())
        return objects

    def get_total_collision(self, name):
        res = self.client.request(f'vbp {name} GetCollisionNum')
        total_collision = eval(json.loads(res)["TotalCollision"])
        return total_collision

    def get_location(self, actor_name):
        try:
            cmd = f'vget /object/{actor_name}/location'
            res = self.client.request(cmd)
            location = [float(i) for i in res.split()]
            return np.array(location)
        except Exception as e:
            print(f"Error occurred in {__file__}:{e.__traceback__.tb_lineno}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Error traceback:")
            print('res:', res)

    def get_location_batch(self, actor_names):
        cmd = [f'vget /object/{actor_name}/location' for actor_name in actor_names]
        res = self.client.request_batch(cmd)
        # Parse each response and convert to numpy array
        locations = [np.array([float(i) for i in r.split()]) for r in res]
        return locations

    def get_orientation(self, actor_name):
        try:
            cmd = f'vget /object/{actor_name}/rotation'
            res = self.client.request(cmd)
            orientation = [float(i) for i in res.split()]
            return np.array(orientation)
        except Exception as e:
            print(f"Error occurred in {__file__}:{e.__traceback__.tb_lineno}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Error traceback:")
            print('res:', res)

    def get_orientation_batch(self, actor_names):
        cmd = [f'vget /object/{actor_name}/rotation' for actor_name in actor_names]
        res = self.client.request_batch(cmd)
        # Parse each response and convert to numpy array
        orientations = [np.array([float(i) for i in r.split()]) for r in res]
        return orientations

    def show_img(self, img, title="raw_img"):
        cv2.imshow(title, img)
        cv2.waitKey(3)

    def read_image(self, cam_id, viewmode, mode='direct'):
            # cam_id:0 1 2 ...
            # viewmode:lit,  =normal, depth, object_mask
            # mode: direct, file
            res = None
            if mode == 'direct': # get image from unrealcv in png format
                cmd = f'vget /camera/{cam_id}/{viewmode} png'
                image = self.decode_png(self.client.request(cmd))
            elif mode == 'file': # save image to file and read it
                cmd = f'vget /camera/{cam_id}/{viewmode} {viewmode}{self.ip}.png'
                img_dirs = self.client.request(cmd)
                print(f"img_dirs type: {type(img_dirs)}")
                print(f"img_dirs: {img_dirs}")
                image = cv2.imread(img_dirs)
                print(f"image type: {type(image)}")
                print(f"image: {image}")
            elif mode == 'fast': # get image from unrealcv in bmp format
                cmd = f'vget /camera/{cam_id}/{viewmode} bmp'
                print(f"bmp: {self.client.request(cmd)}")
                image = self.decode_bmp(self.client.request(cmd))
            return image

    def decode_png(self, res): # decode png image
        img = np.asarray(PIL.Image.open(BytesIO(res)))
        img = img[:, :, :-1]  # delete alpha channel
        img = img[:, :, ::-1]  # transpose channel order
        return img

    def decode_bmp(self, res, channel=4): # decode bmp image
        img = np.fromstring(res, dtype=np.uint8)
        img=img[-self.resolution[1]*self.resolution[0]*channel:]
        img=img.reshape(self.resolution[1], self.resolution[0], channel)
        return img[:, :, :-1] # delete alpha channel
