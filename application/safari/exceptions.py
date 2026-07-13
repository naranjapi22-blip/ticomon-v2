class SafariApplicationError(ValueError):
    pass


class SafariUnlockUnavailable(SafariApplicationError):
    pass


class SafariActivityAlreadyExists(SafariApplicationError):
    pass


class SafariRegistrationNotFound(SafariApplicationError):
    pass


class SafariInsufficientParticipants(SafariApplicationError):
    pass


class SafariInvalidUnlockConfiguration(SafariApplicationError):
    pass
