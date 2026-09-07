"""Pydantic schemas for account management — DPDP deletion & data export."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeleteAccountRequest(BaseModel):
    """OTP-confirmed account deletion request (DPDP compliance)."""

    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class RequestDeletionOTPResponse(BaseModel):
    """Response after requesting a deletion-confirmation OTP."""

    success: bool = True
    message: str = "OTP sent to your registered email"


class DeleteAccountResponse(BaseModel):
    """Response after successful account deletion."""

    success: bool = True
    message: str = "Account deleted and personal data anonymised"


class ExportDataResponse(BaseModel):
    """Wrapper — actual export is returned as a JSON file download."""

    success: bool = True
    message: str = "Data export ready"
