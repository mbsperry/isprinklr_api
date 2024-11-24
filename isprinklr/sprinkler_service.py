import pandas as pd
import logging
from typing import List

from isprinklr.schemas import ScheduleItem, SprinklerConfig

logger = logging.getLogger(__name__)


def validate_sprinklers(sprinklers: List[SprinklerConfig]) -> bool:
    # check to make sure no more than 12 sprinklers are defined
    # This is arbitrary but we don't want files that are too large
    if len(sprinklers) == 0:
        logger.error(f"No sprinklers defined")
        raise ValueError("Validation Error: No sprinklers defined")
    if len(sprinklers) > 12:
        logger.error(f"Too many sprinklers defined: {sprinklers}")
        raise ValueError("Validation Error: Too many sprinklers defined")
    
    # check that required fields exist
    for sprinkler in sprinklers:
        if "zone" not in sprinkler or "name" not in sprinkler:
            logger.error(f"Missing required fields in sprinkler: {sprinkler}")
            raise ValueError("Validation Error: Missing required fields")
        if not isinstance(sprinkler["zone"], int):
            logger.error(f"Zone must be an integer: {sprinkler}")
            raise ValueError("Validation Error: Zone must be an integer")
        if not isinstance(sprinkler["name"], str):
            logger.error(f"Name must be a string: {sprinkler}")
            raise ValueError("Validation Error: Name must be a string")
    
    # check that each zone is only used once
    if len(sprinklers) != len(set([x["zone"] for x in sprinklers])):
        logger.error(f"Duplicate zones in sprinklers: {sprinklers}")
        raise ValueError("Validation Error: Duplicate zones in sprinklers")
    
    # check that each name is unique
    if len(sprinklers) != len(set([x["name"] for x in sprinklers])):
        logger.error(f"Duplicate names in sprinklers: {sprinklers}")
        raise ValueError("Validation Error: Duplicate names in sprinklers")
    
    # check that no name is greater than 30 characters
    if any(len(x["name"]) > 30 for x in sprinklers):
        logger.error(f"Name is too long: {sprinklers}")
        raise ValueError("Validation Error: Name is too long")
    
    return True

def read_sprinklers(data_path: str) -> List[SprinklerConfig]:
    try:
        df = pd.read_csv(data_path + "/sprinklers.csv", usecols=["zone", "name"])
        sprinklers = df.to_dict("records")
        try:
            validate_sprinklers(sprinklers)
        except ValueError as e:
            logger.error(f"Sprinklers.csv contained invalid sprinkler definitions")
            sprinklers = []
    except Exception as e:
        logger.error(f"Failed to load sprinklers data: {e}")
        sprinklers = []
    logger.debug(f"Sprinklers: {sprinklers}")
    return sprinklers

def write_sprinklers(data_path: str, sprinklers: List[SprinklerConfig]) -> bool:
    try:
        validate_sprinklers(sprinklers)
    except ValueError as e:
        logger.error(f"Invalid sprinklers: {sprinklers}, aborting write")
        raise
    try:
        df = pd.DataFrame(sprinklers)
        df.to_csv(data_path + "/sprinklers.csv", index=False)
        logger.debug(f"Sprinklers written to {data_path}/sprinklers.csv")
    except Exception as e:
        logger.error(f"Failed to write sprinklers data: {e}")
        raise
    return True
