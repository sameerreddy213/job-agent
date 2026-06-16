"""Google service-account auth + spreadsheet handle. Lazy imports so the rest of
the app runs without gspread installed / configured."""
import json

from ..config import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def is_configured() -> bool:
    return bool(
        settings.GOOGLE_SHEET_ID
        and (settings.GOOGLE_SERVICE_ACCOUNT_JSON.strip() or settings.GOOGLE_SERVICE_ACCOUNT_FILE.strip())
    )


def get_spreadsheet():
    """Authorize and open the configured spreadsheet. Raises if misconfigured."""
    import gspread
    from google.oauth2.service_account import Credentials

    if settings.GOOGLE_SERVICE_ACCOUNT_JSON.strip():
        info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    client = gspread.authorize(creds)
    return client.open_by_key(settings.GOOGLE_SHEET_ID)
