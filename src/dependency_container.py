# Dependency Injection Container

from dependency_injector import containers, providers

try:
    from src.services.storage_service import StorageService
    from src.services.submission_service import SubmissionService
    from src.infrastructure.repositories.submission_repository import SubmissionRepository
except ImportError:
    from services.storage_service import StorageService
    from services.submission_service import SubmissionService
    from infrastructure.repositories.submission_repository import SubmissionRepository


class Container(containers.DeclarativeContainer):
    # Placeholder để giữ compatibility với các phần khác
    # nếu project hiện tại đang tham chiếu container.database.
    database = providers.Object(None)

    storage_service = providers.Singleton(
        StorageService
    )

    submission_repository = providers.Factory(
        SubmissionRepository
    )

    submission_service = providers.Factory(
        SubmissionService,
        submission_repo=submission_repository,
        storage_service=storage_service,
    )