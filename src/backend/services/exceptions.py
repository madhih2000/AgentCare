class ServiceError(Exception):
    """Base class for service-layer errors mapped to HTTP responses by routes."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class SlotUnavailableError(ServiceError):
    pass


class UnauthorizedError(ServiceError):
    pass


class ValidationError(ServiceError):
    pass
