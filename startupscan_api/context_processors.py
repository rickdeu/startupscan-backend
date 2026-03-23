from startupscan_api.roles import (
    ROLE_PUBLICO,
    get_user_role,
    role_access_matrix,
    role_home_url_name,
    role_label,
)


def user_role_context(request):
    user = getattr(request, "user", None)
    role = get_user_role(user)
    access = role_access_matrix(role)
    return {
        "user_role": role,
        "user_role_label": role_label(role),
        "user_role_home_url_name": role_home_url_name(role),
        "user_role_access": access,
        "role_publico": ROLE_PUBLICO,
    }

