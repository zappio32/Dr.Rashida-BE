from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10)


class LoginResponse(BaseModel):
    role: str


class RegisterResponse(BaseModel):
    ok: bool = True


class SessionUser(BaseModel):
    userId: str
    role: str
    name: str
    email: str
