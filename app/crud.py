from app.models import User, UserCreate

# Dummy users database
users_db = []

def create_user(user: UserCreate) -> User:
    new_user = User(id=len(users_db) + 1, **user.dict(), is_active=True)
    users_db.append(new_user)
    return new_user

def get_users(skip: int, limit: int) -> list:
    return users_db[skip : skip + limit]

# Add more CRUD functions as required
