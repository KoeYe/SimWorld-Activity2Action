from typing import List
import numpy as np
# from llm_reasoners.reasoners.base import LanguageModel
from PIL import Image
import openai
import io
import json
import random
# from .base import ActionQueue, Action
from A2A.ActionSpace import ActionSpace, Action
from llm.openai_model import UEOpenAIModel
from utils.Types import Vector, Road
from Config import Config
import math
import time
import os
from threading import Lock

import logging

from Prompt.prompt import SYSTEM_PROMPT, USER_PROMPT
from A2A.Map import Map, Node, Edge

FUNCTIONS = json.load(open("functions.json", "r"))

class A2Agent(object):
    """Agent using LLM Reasoner"""
    def __init__(self,
                model: UEOpenAIModel,
                name: str,
                # waypoint: Vector,
                unrealcv_client=None,
                temperature=1.0,
                max_history_step=5,
                camera_id=1,
                dt=1,
                observation_viewmode='lit',
                action_buffer=None,
                rule_based=True,
                ):
        self.lock = Lock()
        self.name = name
        self.model = model
        self.functions = FUNCTIONS
        self.unrealcv_client = unrealcv_client # unrealcv_delivery
        self.system_prompt = SYSTEM_PROMPT.replace("<NAME>", name)
        self.temperature = temperature
        self.max_history_step = max_history_step
        # self.action_history = ""
        self.camera_id = camera_id
        self.observation_viewmode = observation_viewmode
        self.map = Map()
        self.action_buffer = action_buffer
        self.next_waypoint = None # Vector
        self.position = None
        self.direction = None  # Assuming the initial direction is facing 'up' in the 2D plane
        self.rule_based = rule_based
        self.dt = dt
        self.update_position_and_direction()
        self.map_init()
        self.init_logger()

    def init_logger(self):
        # Create a logger object
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Create a file handler
        log_file_path = os.path.join("logs", f"{self.name}.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)

        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create a formatter and set it for both handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_possible_next_waypoints(self):
        """
        Get the possible next waypoints from the current position
        Returns: A list of possible next waypoints (List[Vector])
        """
        current_node = None
        min_distance = float('inf')
        for node in self.map.nodes:
            distance = self.position.distance(node.position)
            if distance < min_distance:
                min_distance = distance
                current_node = node
        return self.map.get_adjacent_points(current_node)

    def parse(self):
        test_point = self.get_possible_next_waypoints()[0]
        self.logger.info(f"possible next waypoint:{test_point}")
        user_prompt = USER_PROMPT.format(map=self.map, position=self.position, waypoint=test_point)
        
        response = self.model.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            # action_history=self.action_history,
            temperature=self.temperature
        )
        print(f"Response: {response}")
        response_obj = ActionSpace.from_json(response)

        actions = response_obj.actions
        self.next_waypoint = Vector(response_obj.waypoints.x, response_obj.waypoints.y)

        for action in actions:
            if action == Action.Navigate:
                self.navigate()
        
    def navigate(self):
        """Navigate to the waypoint"""
        # self.next_waypoint = Vector(int(waypoint[0]), int(waypoint[1]))
        print(f"Next waypoint: {self.next_waypoint}")
        if self.rule_based:
            self.navigate_rule_based()
        else:
            self.navigate_vision_based()
        self.update_position_and_direction()
        
    def navigate_rule_based(self):
        self.logger.info(f"Current position: {self.position}, Next waypoint: {self.next_waypoint}, Direction: {self.direction}")
        while not self.walk_arrive_at_waypoint():
            while not self.align_direction():
                angle, turn_direction = self.get_angle_and_direction()
                self.logger.info(f"Angle: {angle}, Turn direction: {turn_direction}")
                self.unrealcv_client.d_rotate(self.name, angle, turn_direction)
                self.update_position_and_direction()
            self.logger.info(f"Walking to waypoint: {self.next_waypoint}")
            self.unrealcv_client.d_step_forward(self.name)
            self.update_position_and_direction()
            
    def navigate_vision_based(self):
        # while not self.walk_arrive_at_waypoint():
        #     image = self.unrealcv_client.get_observation(self.camera_id, self.observation_viewmode)
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
        self.logger.info("Aligning direction")
        to_waypoint = self.next_waypoint - self.position
        angle = math.degrees(math.acos(np.clip(self.direction.dot(to_waypoint.normalize()), -1, 1)))
        self.logger.info(f"Angle to waypoint: {angle}")
        return angle < 5
        
    def update_position_and_direction(self):
        with self.lock:
            position = self.unrealcv_client.d_get_location(self.name)[:-1] # Ignore Z coordinate
            yaw = self.unrealcv_client.d_get_rotation(self.name)[1] # Yaw
            self.position = Vector(position[0], position[1])
            self.direction = Vector(math.cos(math.radians(yaw)), math.sin(math.radians(yaw))).normalize()
        # return position, direction
    
    def map_init(self):
        with open('roads.json', 'r') as f:
            roads_data = json.load(f)

        roads = roads_data['roads']

        road_objects = []
        for road in roads:
            start = Vector(road['start']['x']*100, road['start']['y']*100)
            end = Vector(road['end']['x']*100, road['end']['y']*100)
            road_objects.append(Road(start, end))

        # Initialize the map
        for road in road_objects:
            normal_vector = Vector(road.direction.y, -road.direction.x)
            point1 = road.start - normal_vector * (Config.SIDEWALK_OFFSET) + road.direction * Config.SIDEWALK_OFFSET
            point2 = road.end - normal_vector * (Config.SIDEWALK_OFFSET) - road.direction * Config.SIDEWALK_OFFSET

            point3 = road.end + normal_vector * (Config.SIDEWALK_OFFSET) - road.direction * Config.SIDEWALK_OFFSET
            point4 = road.start + normal_vector * (Config.SIDEWALK_OFFSET) + road.direction * Config.SIDEWALK_OFFSET

            node1 = Node(point1, "intersection")
            node2 = Node(point2, "intersection")
            node3 = Node(point3, "intersection")
            node4 = Node(point4, "intersection")

            self.map.add_node(node1)
            self.map.add_node(node2)
            self.map.add_node(node3)
            self.map.add_node(node4)

            self.map.add_edge(Edge(node1, node2))
            self.map.add_edge(Edge(node3, node4))
            self.map.add_edge(Edge(node1, node4))
            self.map.add_edge(Edge(node2, node3))


    def reset(self):
        self.unrealcv_client.enable_controller(self.name, True)