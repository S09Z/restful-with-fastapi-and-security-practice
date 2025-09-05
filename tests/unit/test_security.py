import pytest
from datetime import datetime, timedelta
from jose import JWTError
from unittest.mock import patch

from app.security import create_access_token, decode_access_token
from app.config import settings


class TestSecurity:
    
    def test_create_access_token_success(self):
        test_data = {"sub": "1", "username": "testuser"}
        
        token = create_access_token(data=test_data)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_decode_access_token_success(self):
        test_data = {"sub": "1", "username": "testuser", "email": "test@example.com"}
        token = create_access_token(data=test_data)
        
        payload = decode_access_token(token)
        
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
    
    def test_decode_access_token_invalid(self):
        invalid_token = "invalid.token.here"
        
        with pytest.raises(JWTError):
            decode_access_token(invalid_token)
    
    def test_decode_access_token_expired(self):
        test_data = {"sub": "1", "username": "testuser"}
        
        # Create token that expires immediately
        with patch('app.security.ACCESS_TOKEN_EXPIRE_MINUTES', -1):
            expired_token = create_access_token(data=test_data)
        
        # Wait a moment to ensure expiration
        import time
        time.sleep(0.1)
        
        with pytest.raises(JWTError):
            decode_access_token(expired_token)
    
    def test_token_expiration_included(self):
        test_data = {"sub": "1", "username": "testuser"}
        before_creation = datetime.utcnow()
        
        token = create_access_token(data=test_data)
        payload = decode_access_token(token)
        
        after_creation = datetime.utcnow()
        token_exp = datetime.utcfromtimestamp(payload["exp"])
        
        expected_exp = before_creation + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        max_expected_exp = after_creation + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        assert expected_exp <= token_exp <= max_expected_exp
    
    def test_token_contains_all_data(self):
        test_data = {
            "sub": "123",
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "custom_field": "custom_value"
        }
        
        token = create_access_token(data=test_data)
        payload = decode_access_token(token)
        
        for key, value in test_data.items():
            assert payload[key] == value
    
    def test_empty_data_token(self):
        empty_data = {}
        
        token = create_access_token(data=empty_data)
        payload = decode_access_token(token)
        
        # Should only contain the expiration claim
        assert "exp" in payload
        assert len(payload) == 1