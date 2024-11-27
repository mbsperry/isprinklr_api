import pandas as pd
import logging
from typing import List

from isprinklr.schemas import SprinklerConfig

logger = logging.getLogger(__name__)


def validate_sprinklers(sprinklers: List[SprinklerConfig]) -> bool:
    """
    Validates a list of sprinkler configurations against defined rules.
    
    Rules:
    - Must have at least 1 sprinkler defined
    - Maximum of 12 sprinklers allowed
    - Each sprinkler must have 'zone' and 'name' fields
    - Zone must be an integer
    - Name must be a string
    - Zone numbers must be unique
    - Names must be unique
    - Names must not exceed 30 characters
    
    Args:
        sprinklers (List[SprinklerConfig]): List of sprinkler configurations to validate.
            Each sprinkler should be a dict with 'zone' (int) and 'name' (str) keys.
    
    Returns:
        bool: True if all validations pass
    
    Raises:
        ValueError: If any validation rule is violated, with a descriptive error message
    """
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
    """
    Reads sprinkler configurations from a CSV file.
    
    Attempts to read sprinkler data from 'sprinklers.csv' in the specified directory.
    If the file cannot be read or contains invalid data, returns an empty list.
    Only reads 'zone' and 'name' columns from the CSV.
    
    Args:
        data_path (str): Directory path containing the sprinklers.csv file
    
    Returns:
        List[SprinklerConfig]: List of valid sprinkler configurations.
            Returns empty list if file cannot be read or contains invalid data.
    
    Raises:
        Note: All exceptions are caught internally and result in an empty list being returned:
        - pandas.errors.EmptyDataError: If the CSV file is empty
        - FileNotFoundError: If sprinklers.csv doesn't exist in data_path
        - pandas.errors.ParserError: If CSV file is malformed
        - ValueError: If sprinkler configurations in CSV fail validation
    """
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
    """
    Writes sprinkler configurations to a CSV file.
    
    Validates the sprinkler configurations before writing to ensure data integrity.
    Creates or overwrites 'sprinklers.csv' in the specified directory.
    
    Args:
        data_path (str): Directory path where sprinklers.csv will be written
        sprinklers (List[SprinklerConfig]): List of sprinkler configurations to write.
            Each sprinkler should be a dict with 'zone' (int) and 'name' (str) keys.
    
    Returns:
        bool: True if write operation succeeds
    
    Raises:
        ValueError: If sprinkler configurations fail validation
        Exception: If file write operation fails
    """
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
