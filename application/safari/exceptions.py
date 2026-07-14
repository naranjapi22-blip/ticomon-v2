class SafariApplicationError(ValueError):
    pass


class SafariUnlockUnavailable(SafariApplicationError):
    pass


class SafariUnlockAlreadyExists(SafariApplicationError):
    pass


class SafariActivityAlreadyExists(SafariApplicationError):
    pass


class SafariActivityNotFound(SafariApplicationError):
    pass


class SafariRegistrationNotFound(SafariApplicationError):
    pass


class SafariRegistrationStillOpen(SafariApplicationError):
    def __init__(self, remaining_seconds: int) -> None:
        self.remaining_seconds = remaining_seconds
        super().__init__("Safari registration is still open.")


class SafariSessionNotFound(SafariApplicationError):
    pass


class SafariSessionNotFinished(SafariApplicationError):
    pass


class SafariInsufficientParticipants(SafariApplicationError):
    pass


class SafariInvalidUnlockConfiguration(SafariApplicationError):
    pass


class SafariRouteVoteUnavailable(SafariApplicationError):
    pass


class SafariRouteVoteNotFound(SafariApplicationError):
    pass


class SafariCaptureSelectionUnavailable(SafariApplicationError):
    pass


class SafariCaptureSelectionNotFound(SafariApplicationError):
    pass


class SafariCaptureResolutionUnavailable(SafariApplicationError):
    pass
