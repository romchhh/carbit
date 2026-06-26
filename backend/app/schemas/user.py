from app.models.models import User
from app.schemas.schemas import UserOut
from app.services.user_avatar import user_avatar_api_path


def user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user, from_attributes=True)
    out.avatar_url = user_avatar_api_path(user)
    return out
