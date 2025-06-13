import json # Added
import os   # Added
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
    Reads sprinkler configurations from a JSON file (sprinklers.json).
    
    Attempts to read sprinkler data from 'sprinklers.json' in the specified directory.
    If the file cannot be read, is malformed, or contains invalid data, 
    returns an empty list.
    
    Args:
        data_path (str): Directory path containing the sprinklers.json file
    
    Returns:
        List[SprinklerConfig]: List of valid sprinkler configurations.
            Returns empty list if file issues occur or validation fails.
    """
    sprinklers_file_path = os.path.join(data_path, "sprinklers.json")
    loaded_sprinklers: List[SprinklerConfig] = []

    try:
        with open(sprinklers_file_path, "r") as f:
            data_from_file = json.load(f)
        
        if not isinstance(data_from_file, list):
            logger.error(f"'{sprinklers_file_path}' does not contain a valid list. Found type: {type(data_from_file)}.")
            # loaded_sprinklers remains []
        else:
            # At this point, data_from_file is a list.
            # Further validation of its contents (structure of dicts, types of values)
            # is implicitly handled by validate_sprinklers.
            loaded_sprinklers = data_from_file
            
        # Validate the loaded sprinklers (even if it's an empty list from a valid empty JSON array)
        # validate_sprinklers will raise ValueError if the list is empty or rules are violated.
        validate_sprinklers(loaded_sprinklers)

    except FileNotFoundError:
        logger.warning(f"'{sprinklers_file_path}' not found. Returning empty list of sprinklers.")
        # loaded_sprinklers remains []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{sprinklers_file_path}': {e}. Returning empty list.")
        # loaded_sprinklers remains []
    except ValueError as e: # This catches validation errors from validate_sprinklers
        logger.error(f"Validation error for sprinklers in '{sprinklers_file_path}': {e}. Returning empty list.")
        loaded_sprinklers = [] # Ensure it's reset if validation fails after a partial load attempt
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error loading sprinklers data from '{sprinklers_file_path}': {e}. Returning empty list.")
        loaded_sprinklers = []

    logger.debug(f"Sprinklers loaded: {loaded_sprinklers}")
    return loaded_sprinklers

def write_sprinklers(data_path: str, sprinklers: List[SprinklerConfig]) -> bool:
    """
    Writes sprinkler configurations to a JSON file (sprinklers.json).
    
    Validates the sprinkler configurations before writing.
    Creates or overwrites 'sprinklers.json' in the specified directory.
    
    Args:
        data_path (str): Directory path where sprinklers.json will be written
        sprinklers (List[SprinklerConfig]): List of sprinkler configurations to write.
    
    Returns:
        bool: True if write operation succeeds
    
    Raises:
        ValueError: If sprinkler configurations fail validation.
        IOError: If file write operation fails.
    """
    try:
        # Validate sprinklers before attempting to write.
        # validate_sprinklers raises ValueError if validation fails (e.g. empty list).
        validate_sprinklers(sprinklers)
    except ValueError as e:
        logger.error(f"Invalid sprinklers data provided for writing: {e}. Aborting write to sprinklers.json.")
        raise # Re-raise the ValueError to be handled by the caller

    sprinklers_file_path = os.path.join(data_path, "sprinklers.json")
    try:
        with open(sprinklers_file_path, "w") as f:
            json.dump(sprinklers, f, indent=2)
        logger.debug(f"Sprinkler configurations written to '{sprinklers_file_path}'")
        return True
    except IOError as e:
        logger.error(f"Failed to write sprinklers data to '{sprinklers_file_path}': {e}")
        raise # Re-raise IOError
    except Exception as e: # Catch any other unexpected errors during write
        logger.error(f"Unexpected error writing sprinklers data to '{sprinklers_file_path}': {e}")
        # Convert to IOError or a custom exception if preferred, to signal write failure
        raise IOError(f"Unexpected error writing sprinklers.json: {e}")
