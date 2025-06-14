# Changelog

## [2.1.1] - 2025-06-14

### Bug Fixes
- **Fixed test failures in fresh install**: Resolved `FileNotFoundError` exceptions that occurred when the `logs` directory didn't exist by checking for and creating logs directory as needed
- **Enhanced test dependencies**: Added missing `pytest-asyncio` and `pytest-mock` dependencies to requirements.txt
- **Fixed test mocking issues**: Corrected sprinklers route test to properly mock data instead of accessing non-existent files

## [2.1.0] - 2025-06-13

### Major Changes
- Migrated to ESP32-based controller with REST API over ethernet (from serial connection)
- Implemented APScheduler for automated schedule execution without cron dependency
- Improved system configuration with new interactive CLI tool (configure.py)

### Architecture Improvements
- Eliminated dependency on PANDAS for data storage
- Enhanced ESP controller communication with better error handling
- Fixed race conditions in zone sequence running
- Added ability to update ESP controller configuration without API restart
- Improved async implementation using AsyncIOScheduler

### Logging & Diagnostics
- Enhanced logging system with configurable log levels
- Added ability to retrieve up to 1000 lines from logs
- Added module list endpoint for filtering logs
- Improved error tracking and debugging capabilities

### System Tracking & Control
- Added tracking of last zone run and last schedule run
- Improved schedule management with better error handling
- Enhanced system stopping mechanism while running zone sequences
- Added endpoints to run active and specific schedules
- Improved handling of cancelled operations

### API Refinements
- Added CORS handling for better frontend integration
- Improved API endpoint documentation
- Enhanced error reporting
- Better boolean handling in settings
- Completely removed deprecated V1 API routes (no longer backward compatible)

## [2.0.0] - 2024

### Major Changes
- Complete API restructuring for better organization and maintainability
- New modular router system with dedicated endpoints 
- Improved system architecture with centralized state management

### API Changes
- Moved from monolithic `/api` to feature-specific routes
- New router structure:
  - `/api/sprinklers` for sprinkler control and configuration
  - `/api/scheduler` for schedule management
  - `/api/system` for system status
  - `/api/logs` provides access to logs
- Improved endpoint naming and organization
- Better RESTful practices with appropriate HTTP methods (GET, POST, PUT)

### Architecture Improvements
- Introduced centralized system state management through SystemStatus class
  - Unified state handling for sprinkler system
  - Thread-safe operations for concurrent requests
  - Robust error recovery mechanisms
- Separated business logic into dedicated service modules
  - SprinklerService for zone management
  - ScheduleService for scheduling logic
  - Improved hardware communication layer
- Business logic and API endpoints separated
- Improved error handling and validation
- Enhanced type safety with proper schema definitions

### Schema Improvements
- Introduced strongly typed schemas using TypedDict and Pydantic
  - `SprinklerCommand` for zone control operations (renamed from `Sprinkler` for clarity)
  - `SprinklerConfig` for zone configuration
  - `ScheduleItem` for scheduling definitions
  - `ScheduleOnOff` for schedule control
- Consistent data structures across API endpoints
- Runtime type validation for request/response data
- Better IDE support with type hints

### Code Quality
- Implemented consistent error handling patterns
  - Granular error types for different failure scenarios
  - Proper error propagation through layers
  - Improved error logging and reporting
- Added comprehensive type hints
- Improved async/await implementation
  - Better handling of long-running operations
  - Proper cancellation of background tasks
- Better logging system
- More robust validation for sprinkler and schedule configurations

### Better Logging
- Global logging file
- New logging API allows filtering by module name or logging alert status
- Improved error tracking and debugging capabilities
- Structured logging for better analysis

### Hardware Integration
- Improved communication with Arduino controller
- Better error handling for hardware failures
- Automatic recovery from connection issues
- More reliable zone control

### Breaking Changes
- Old (V1) API moved to `/api/v1/`
- New URL structure requires client updates
- Changed request/response formats for better consistency
- Modified state management requires updated client integration
- New schema definitions require updated client data structures
