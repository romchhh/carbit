from app.models.models import User
from app.schemas.schemas import UserOut
from app.services.user_avatar import user_avatar_api_path
from app.services.telegram.links import is_placeholder_email


def user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user, from_attributes=True)
    out.avatar_url = user_avatar_api_path(user)
    if is_placeholder_email(user.email):
        out.email = ""
        out.email_verified = False
    else:
        out.email_verified = True
    return out
