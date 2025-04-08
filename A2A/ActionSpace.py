from pydantic import BaseModel
from enum import Enum
import json
from typing import List, Tuple
from utils.Types import Vector

class Waypoint(BaseModel):
    x: float
    y: float

class Action(Enum):
    Navigate = 0

class ActionSpace(BaseModel):
    actions: List[Action] 
    waypoints: Waypoint

    def __str__(self):
        actions_str = ','.join(str(a) for a in self.actions)
        return f"ActionSpace(actions=[{actions_str}], waypoints={self.waypoints})"

    def __repr__(self):
        return self.__str__()

    @classmethod
    def from_json(cls, json_str):
        # Need to convert integer to enum manually
        # data = json.loads(json_str)
        # data["actions"] = [Action(a) for a in data["actions"]]
        return cls(**json.loads(json_str))