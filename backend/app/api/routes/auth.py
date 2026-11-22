from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserOut, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new citizen account."""
    existing = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    # Restrict admin creation via public endpoint unless designated
    role = "citizen"
    if user_in.role == "admin" and user_in.email.endswith("@civicpulse.gov.in"):
        role = "admin"

    user = User(
        email=user_in.email.lower().strip(),
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name.strip(),
        phone=user_in.phone,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.post("/login", response_model=Token)
@limiter.limit("20/minute")
def login(request: Request, login_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password to receive JWT session token."""
    user = db.query(User).filter(User.email == login_data.email.lower().strip()).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve currently authenticated user profile."""
    return current_user
