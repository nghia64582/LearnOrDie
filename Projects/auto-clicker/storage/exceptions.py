"""Storage and repository domain exceptions."""


class StorageError(Exception):
    """Base exception for all storage errors."""
    pass


class WorkflowNotFoundError(StorageError):
    """Raised when a requested workflow file does not exist."""
    pass


class WorkflowCollisionError(StorageError):
    """Raised when an operation would overwrite an existing workflow file."""
    pass


class CorruptWorkflowError(StorageError):
    """Raised when a workflow file contains malformed JSON or invalid schema."""
    pass
