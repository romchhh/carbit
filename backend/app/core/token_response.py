from __future__ import annotations

from fastapi.responses import JSONResponse

from app.core.auth_cookies import AUTH_COOKIE_MAX_AGE, attach_auth_cookie


def token_json_response(
    token: str,
    *,
    status_code: int = 200,
    max_age: int | None = AUTH_COOKIE_MAX_AGE,
    is_new_user: bool | None = None,
) -> JSONResponse:
    content: dict = {"access_token": token, "token_type": "bearer"}
    if is_new_user is not None:
        content["is_new_user"] = is_new_user
    response = JSONResponse(content=content, status_code=status_code)
    attach_auth_cookie(response, token, max_age=max_age)
    return response
