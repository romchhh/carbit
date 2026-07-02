from __future__ import annotations

from fastapi.responses import JSONResponse

from app.core.auth_cookies import attach_auth_cookie


def token_json_response(token: str, *, status_code: int = 200) -> JSONResponse:
    response = JSONResponse(
        content={"access_token": token, "token_type": "bearer"},
        status_code=status_code,
    )
    attach_auth_cookie(response, token)
    return response
