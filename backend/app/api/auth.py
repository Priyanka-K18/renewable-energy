from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    department: Optional[str] = "Renewable Operations"
    role: Optional[str] = "analyst"

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_user(req: RegisterRequest) -> Dict[str, Any]:
    # In full Supabase mode, delegates to Supabase Auth.
    # Returns session and profile details.
    return {
        "status": "success",
        "message": "User registered successfully",
        "user": {
            "email": req.email,
            "full_name": req.full_name,
            "role": req.role,
            "department": req.department
        },
        "token": "token_demo_" + req.email.split("@")[0]
    }

@router.post("/login")
def login_user(req: LoginRequest) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": "Logged in successfully",
        "user": {
            "email": req.email,
            "full_name": "Senior Energy Analyst",
            "role": "lead_engineer",
            "department": "Renewable Intelligence & Big Data"
        },
        "token": "token_jwt_session_valid"
    }

@router.get("/profile")
def get_user_profile() -> Dict[str, Any]:
    return {
        "status": "success",
        "user": {
            "email": "analyst@renewable-intelligence.io",
            "full_name": "Dr. Sarah Chen, PE",
            "role": "Principal Big Data Energy Architect",
            "department": "Global Clean Tech Operations",
            "permissions": ["READ_ANALYTICS", "TRIGGER_SPARK_JOB", "RESOLVE_ANOMALIES", "EXPORT_REPORTS"]
        }
    }
