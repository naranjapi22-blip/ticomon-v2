from __future__ import annotations

from application.safari import (
    SafariActivityAlreadyExists,
    SafariActivityNotFound,
    SafariCaptureResolutionUnavailable,
    SafariCaptureSelectionNotFound,
    SafariCaptureSelectionUnavailable,
    SafariInsufficientParticipants,
    SafariInvalidUnlockConfiguration,
    SafariRegistrationNotFound,
    SafariRegistrationStillOpen,
    SafariRouteVoteNotFound,
    SafariRouteVoteUnavailable,
    SafariSessionNotFinished,
    SafariSessionNotFound,
    SafariUnlockUnavailable,
)
from application.safari.exceptions import SafariApplicationError
from core.safari.registration import SafariRegistrationClosed
from interfaces.discord.safari_timing import format_registration_wait_message


def safari_error_message(error: Exception) -> str:
    if isinstance(error, SafariUnlockUnavailable):
        return "No Safari unlock is available for this guild."
    if isinstance(error, SafariActivityAlreadyExists):
        return "A Safari activity is already active for this guild."
    if isinstance(error, SafariActivityNotFound):
        return "No Safari activity is active for this guild."
    if isinstance(error, SafariRegistrationNotFound):
        return "Safari registration is no longer available."
    if isinstance(error, SafariRegistrationClosed):
        return "Safari registration is already closed."
    if isinstance(error, SafariRegistrationStillOpen):
        return format_registration_wait_message(error.remaining_seconds)
    if isinstance(error, SafariInsufficientParticipants):
        return "Safari requires at least two participants."
    if isinstance(error, SafariInvalidUnlockConfiguration):
        return "Safari unlock configuration is invalid."
    if isinstance(error, SafariSessionNotFound):
        return "Safari session was not found."
    if isinstance(error, SafariCaptureSelectionUnavailable):
        return "Safari capture selection is not available."
    if isinstance(error, SafariCaptureSelectionNotFound):
        return "Safari capture selection was not found."
    if isinstance(error, SafariCaptureResolutionUnavailable):
        return "Safari capture resolution is not available."
    if isinstance(error, SafariRouteVoteUnavailable):
        return "Safari route vote is not available."
    if isinstance(error, SafariRouteVoteNotFound):
        return "Safari route vote was not found."
    if isinstance(error, SafariSessionNotFinished):
        return "Safari session cannot be finished yet."
    if isinstance(error, SafariApplicationError):
        return "Safari could not be completed."
    return str(error)
