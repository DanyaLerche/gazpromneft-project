#
# Unit-тесты для auth.security (хэширование паролей, JWT, refresh token).
#
# Критичный модуль безопасности — чистая логика без БД и HTTP.
# При изменении алгоритмов или форматов эти тесты должны падать.
import allure
import pytest
from uuid import uuid4

from backend.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)


@allure.feature("Auth Security")
@allure.story("Password hashing")
class TestPasswordHashing:
    """Хэширование и верификация паролей (PBKDF2-HMAC-SHA256)."""

    @allure.title("hash_password + verify_password: roundtrip")
    @allure.description("Пароль после хэширования успешно верифицируется")
    def test_hash_verify_roundtrip(self):
        password = "SecureP@ssw0rd"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    @allure.title("verify_password: неверный пароль — False")
    def test_verify_wrong_password(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    @allure.title("hash_password: разные соли для одинаковых паролей")
    def test_different_salts(self):
        p1 = hash_password("same")
        p2 = hash_password("same")
        assert p1 != p2
        assert verify_password("same", p1)
        assert verify_password("same", p2)

    @allure.title("verify_password: невалидный формат хэша — False")
    def test_verify_invalid_format(self):
        assert not verify_password("any", "not-a-valid-hash")
        assert not verify_password("any", "pbkdf2_sha256$bad$salt$hash")
        assert not verify_password("any", "wrong_algo$100$x$y")


@allure.feature("Auth Security")
@allure.story("JWT Access Token")
class TestAccessToken:
    """Access JWT: создание и верификация."""

    @allure.title("create_access_token → verify_access_token: roundtrip")
    def test_create_verify_roundtrip(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "app_role" not in payload
        assert "project_role" not in payload
        assert "project_roles" not in payload

    @allure.title("verify_access_token: поддельная подпись — None")
    def test_verify_tampered_token(self):
        user_id = uuid4()
        token = create_access_token(user_id)
        tampered = token[:-5] + "xxxxx"
        assert verify_access_token(tampered) is None

    @allure.title("verify_access_token: refresh token вместо access — None")
    def test_verify_refresh_as_access(self):
        user_id = uuid4()
        refresh = create_refresh_token(user_id)
        assert verify_access_token(refresh) is None


@allure.feature("Auth Security")
@allure.story("JWT Refresh Token")
class TestRefreshToken:
    """Refresh JWT: создание и верификация."""

    @allure.title("create_refresh_token → verify_refresh_token: roundtrip")
    def test_create_verify_roundtrip(self):
        user_id = uuid4()
        token = create_refresh_token(user_id)
        payload = verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "nonce" in payload

    @allure.title("verify_refresh_token: access token вместо refresh — None")
    def test_verify_access_as_refresh(self):
        user_id = uuid4()
        access = create_access_token(user_id)
        assert verify_refresh_token(access) is None


@allure.feature("Auth Security")
@allure.story("Refresh Token Hash")
class TestHashRefreshToken:
    """Хэш refresh token для хранения в БД."""

    @allure.title("hash_refresh_token: детерминированность")
    def test_deterministic(self):
        token = "some-refresh-token-value"
        h1 = hash_refresh_token(token)
        h2 = hash_refresh_token(token)
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in h1)
