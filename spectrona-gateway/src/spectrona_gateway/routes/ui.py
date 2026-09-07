import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..auth import gateway_auth_token


router = APIRouter()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    html_path = Path(__file__).resolve().parents[1] / "ui" / "index.html"
    html = html_path.read_text().replace(
        "__SPECTRONA_AUTH_TOKEN_JSON__",
        json.dumps(gateway_auth_token()),
    )
    return HTMLResponse(html)
