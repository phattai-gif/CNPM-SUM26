# Dependency Injection Container

from dependency_injector import containers, providers

try:
    from services.storage_service import StorageService
    from services.submission_service import SubmissionService
    from infrastructure.repositories.submission_repository import SubmissionRepository
except ImportError:
    from services.storage_service import StorageService
    from services.submission_service import SubmissionService
    from infrastructure.repositories.submission_repository import SubmissionRepository


class Container(containers.DeclarativeContainer):
    # Placeholder Ä‘á»ƒ giá»¯ compatibility vá»›i cÃ¡c pháº§n khÃ¡c
    # náº¿u project hiá»‡n táº¡i Ä‘ang tham chiáº¿u container.database.
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
