import logging
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from ..paths import logs_path

logger = logging.getLogger(__name__)

def filter_by_date_range(line: str, start_date: str = None, end_date: str = None) -> bool:
    """Filter a log line based on date range.
    
    Args:
        line (str): The log line to check
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns:
        bool: True if line is within date range or no range specified
    """
    if not start_date and not end_date:
        return True
    
    parts = line.split()
    if len(parts) < 2:
        return False
    
    try:
        log_date = datetime.strptime(parts[0], "%m-%d-%Y").date()
        
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            if log_date < start:
                return False
                
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            if log_date > end:
                return False
                
        return True
    except ValueError:
        return False  # Skip malformed log lines

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"]
)

@router.get("/")
async def get_logs(
    module_name: str = None,
    debug_level: str = None,
    lines: int = 100,
    start_date: str = None,
    end_date: str = None
):
    """Retrieve and filter system logs.

Parameters:
* module_name (str, optional): Filter logs by module name (e.g., 'sprinkler_service')
* debug_level (str, optional): Filter logs by debug level (DEBUG, INFO, ERROR, etc.)
* lines (int, optional): Number of most recent log lines to return (1-1000, default: 100)
* start_date (str, optional): Filter logs starting from this date (inclusive, YYYY-MM-DD format)
* end_date (str, optional): Filter logs up to this date (inclusive, YYYY-MM-DD format)
                          Must be provided with start_date

Returns:
* List[str]: Filtered log entries, each entry formatted as:
  * "YYYY-MM-DD HH:MM:SS module_name LEVEL: message"

Raises:
* HTTPException:
  * 400: If lines parameter is outside valid range (1-1000)
  * 400: If end_date is provided without start_date
  * 400: If date format is invalid (must be YYYY-MM-DD)
  * 400: If start_date is after end_date
  * 404: If log file is not found
  * 500: If log file cannot be read
    """
    if lines < 0 or lines > 1000:
        raise HTTPException(status_code=400, detail="Invalid number of lines")

    # Validate date parameters
    if end_date and not start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be used without start_date")
        
    if start_date or end_date:
        try:
            if start_date:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                if start > end:
                    raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    try:
        with open(logs_path + "/api.log", "r") as f:
            log_lines = f.readlines()
            filtered_lines = []
            for line in log_lines:
                parts = line.split()
                if len(parts) >= 4:
                    if not filter_by_date_range(line, start_date, end_date):
                        continue
                    if module_name and module_name not in parts[2]:
                        continue
                    if debug_level and debug_level not in parts[3]:
                        continue
                    filtered_lines.append(line)
            return filtered_lines[-lines:]
    except FileNotFoundError:
        logger.error("API Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/module_list")
async def get_available_modules() -> List[str]:
    """Retrieve all unique module names from the system logs.

    Returns:
        List[str]: Sorted list of unique module names found in the logs

    Raises:
        HTTPException:
            * 404: If log file is not found
            * 500: If log file cannot be read
    """
    try:
        with open(logs_path + "/api.log", "r") as f:
            log_lines = f.readlines()
            modules = set()
            for line in log_lines:
                parts = line.split()
                if len(parts) >= 4:
                    modules.add(parts[2])
            return sorted(modules)
    except FileNotFoundError:
        logger.error("API Log file not found")
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
