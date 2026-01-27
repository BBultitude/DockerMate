"""
DockerMate Services Package

High-level service layer for business logic:
- ContainerService: Container operations (CRUD, start/stop, logs, stats)
- ImageService: Image management (coming in Sprint 3)
- NetworkService: Network management (coming in Sprint 4)
- VolumeService: Volume management (coming in Sprint 5)

Services abstract Docker SDK operations and provide:
- Business logic and validation
- Error handling and logging
- Data transformation for API consumption
- Caching and performance optimization
"""
