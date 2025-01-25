admin_id_list = [468316922052608000]

def is_admin(user_id: int) -> bool:
    return user_id in admin_id_list