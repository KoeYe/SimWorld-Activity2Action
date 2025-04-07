from typing import List
import numpy as np
# from llm_reasoners.reasoners.base import LanguageModel
from PIL import Image
import openai
import io
import json
import random
from .base import ActionQueue, Action
from llm.openai_model import UEOpenAIModel
from utils.Types import Vector
from Config import Config
import math
import time

from Prompt.prompt import SYSTEM_PROMPT

FUNCTIONS = json.load(open("functions.json", "r"))

class A2Agent(object):
    """Agent using LLM Reasoner"""
    def __init__(self,
                model: UEOpenAIModel,
                name: str,
                waypoint: Vector,
                unrealcv_client=None,
                temperature=1.5,
                max_history_step=5,
                camera_id=1,
                dt=1,
                observation_viewmode='lit',
                action_buffer=None,
                rule_based=True,
                ):
        self.name = name
        self.model = model
        self.functions = FUNCTIONS
        self.client = unrealcv_client # unrealcv_delivery
        self.system_prompt = SYSTEM_PROMPT.replace("<NAME>", name)
        self.temperature = temperature
        self.max_history_step = max_history_step
        self.action_history = ""
        self.camera_id = camera_id
        self.observation_viewmode = observation_viewmode
        self.action_buffer = action_buffer
        self.next_waypoint = waypoint
        self.position = None
        self.direction = None  # Assuming the initial direction is facing 'up' in the 2D plane
        self.rule_based = rule_based
        self.dt = dt
        self.update_position_and_direction()

        
    def navigate(self, waypoint: List[int]):
        """Navigate to the waypoint"""
        self.next_waypoint = Vector(int(waypoint[0]), int(waypoint[1]))
        if self.rule_based:
            self.navigate_rule_based()
        else:
            self.navigate_vision_based()
        self.update_position_and_direction()
        
    def navigate_rule_based(self):
        while not self.walk_arrive_at_waypoint():
            while not self.align_direction():
                angle, turn_direction = self.get_angle_and_direction()
                self.unrealcv_client.d_rotate(self.name, angle, turn_direction)
            self.unrealcv_client.d_step_forward(self.name)
            # time.sleep(self.dt)
        # self.unrealcv_client.d_stop(self.name)
            
    def navigate_vision_based(self):
        # while not self.walk_arrive_at_waypoint():
        #     image = self.client.get_observation(self.camera_id, self.observation_viewmode)
        #     function_call = self.model.function_calling(self.system_prompt, self.user_prompt, images=image, functions=self.functions, action_history=self.action_history, temperature=self.temperature)
        pass

    def walk_arrive_at_waypoint(self):
        if self.position.distance(self.next_waypoint) < Config.WALK_ARRIVE_WAYPOINT_DISTANCE:
            return True
        return False
    
    def get_angle_and_direction(self):
        to_waypoint = self.next_waypoint - self.position

        angle = math.degrees(math.acos(np.clip(self.direction.dot(to_waypoint.normalize()), -1, 1)))

        cross_product = self.direction.cross(to_waypoint)
        turn_direction = 'left' if cross_product < 0 else 'right'

        if angle < 2:
            return 0, None
        else:
            return angle, turn_direction
        
    def align_direction(self):
        to_waypoint = self.next_waypoint - self.position
        angle = math.degrees(math.acos(np.clip(self.direction.dot(to_waypoint.normalize()), -1, 1)))
        return angle < 5

    def _process_function_call(self, tool_call):
        """Process the function call"""
        try:
            if hasattr(tool_call, 'function'):
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                if function_name == "navigate":
                    [x, y] = [arguments.get("x", 0), arguments.get("y", 0)]
                    self.navigate([x, y])
        except Exception as e:
            print(f"Error processing function call: {e}")
            return None
        
    def parse(self, user_prompt: str):
        self.action_history = self.action_buffer.get_action_history(self.name)
        result = self.model.function_calling(
            system_prompt= self.system_prompt,
            user_prompt=user_prompt, # plan given by the user is integrated into this prompt
            functions=self.functions, # 给大模型选择function
            action_history=self.action_history,
            temperature=self.temperature
        )[0][0]

        if result.type == "function":
            self._process_function_call(result)
            return 'success'
        else:
            print("No function call found in the result")
            return None
        
    def update_position_and_direction(self):
        position = self.client.d_get_location(self.name)[:-1] # Ignore Z coordinate
        direction = self.client.d_get_orientation(self.name)[1] # Yaw
        self.position = Vector(position[0], position[1])
        self.direction = direction
        return position, direction

    # def describe(self, observation: list[np.ndarray], system_prompt: str = None, user_prompt: str = None):
    #     default_system_prompt = """
    #         You are a robot named <NAME> in a city.
    #         You have the observation of the environment, which is a list of different types of images of the environment,
    #         including lit, normal, depth, and object_mask images.
    #         Your goal is describe the environment according to your observations in detail.
    #         Your description should include the following information:
    #         - Whether there are any obstacles or objects in the environment.
    #         - The color of the object, whether it is object or obstacle.
    #         - The relative direction of the objects to the robot.
    #         - The relative distance between the robot and the objects.
    #         - Does object right at the middle of the robot's view field.
    #         - The suggest direction for next step to achieve the goal.
    #     """
    #     default_user_prompt = """
    #         According to the current observations images, describe the environment in detail.
    #     """
    #     system_prompt = system_prompt if system_prompt else default_system_prompt
    #     user_prompt = user_prompt if user_prompt else default_user_prompt
    #     return self.model.generate(
    #         system_prompt=system_prompt,
    #         user_prompt=user_prompt,
    #         images=observation,
    #         functions=self.functions,
    #         action_history=self.action_history,
    #         temperature=self.temperature
    #     )


    def reset(self):
        self.client.enable_controller(self.name, True)