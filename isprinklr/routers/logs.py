import logging
from fastapi import APIRouter, HTTPException

from ..paths import logs_path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"]
)

@router.get("/")
async def get_logs(
    module_name: str = None,
    debug_level: str = None,
    lines: int = 100
):
    """Retrieve and filter system logs.

Parameters:
* module_name (str, optional): Filter logs by module name (e.g., 'sprinkler_service')
* debug_level (str, optional): Filter logs by debug level (DEBUG, INFO, ERROR, etc.)
* lines (int, optional): Number of most recent log lines to return (1-200, default: 100)

Returns:
* List[str]: Filtered log entries, each entry formatted as:
  * "YYYY-MM-DD HH:MM:SS module_name LEVEL: message"

Raises:
* HTTPException:
  * 400: If lines parameter is outside valid range (1-200)
  * 404: If log file is not found
  * 500: If log file cannot be read
    """
    if lines < 0 or lines > 200:
        raise HTTPException(status_code=400, detail="Invalid number of lines")
    try:
        with open(logs_path + "/api.log", "r") as f:
            log_lines = f.readlines()
            filtered_lines = []
            for line in log_lines:
                parts = line.split()
                if len(parts) >= 4:
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
