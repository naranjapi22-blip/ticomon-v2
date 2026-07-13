class SafariApplicationError(ValueError):
    pass


class SafariUnlockUnavailable(SafariApplicationError):
    pass


class SafariActivityAlreadyExists(SafariApplicationError):
    pass


class SafariRegistrationNotFound(SafariApplicationError):
    pass


class SafariSessionNotFound(SafariApplicationError):
    pass


class SafariInsufficientParticipants(SafariApplicationError):
    pass


class SafariInvalidUnlockConfiguration(SafariApplicationError):
    pass


class SafariRouteVoteUnavailable(SafariApplicationError):
    pass


class SafariRouteVoteNotFound(SafariApplicationError):
    pass
