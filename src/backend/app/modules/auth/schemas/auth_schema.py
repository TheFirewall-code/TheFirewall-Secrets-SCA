from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    # refresh_token: str

# class RefreshTokenRequest(BaseModel):
#     refresh_token: str


class PasswordResetRequest(BaseModel):
    new_password: str
