# Changelog

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
  - `Sprinkler` for zone control operations
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
