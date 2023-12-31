from datetime import datetime, timedelta
import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidTokenError
from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        # Handle the expired token, e.g., by raising an HTTPException or returning None
        raise ExpiredSignatureError("Token expired.")
    except DecodeError:
        # Handle the error in decoding the token
        raise DecodeError("Error decoding the token.")
    except InvalidTokenError:
        # Handle invalid token
        raise InvalidTokenError("Invalid token.")
