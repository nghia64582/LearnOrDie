"""Domain exceptions for workflow models and definitions."""


class ModelError(Exception):
    """Base exception for all model-related domain errors."""
    pass


class InvalidSchemaVersionError(ModelError):
    """Raised when schema_version is missing or unsupported."""
    pass


class InvalidNodeError(ModelError):
    """Raised when node data or node type is invalid."""
    pass


class InvalidEdgeError(ModelError):
    """Raised when edge data or port connection is invalid."""
    pass


class DuplicateIdError(ModelError):
    """Raised when an entity with an existing ID is added."""
    pass
