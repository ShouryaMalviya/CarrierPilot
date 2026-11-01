"""Authentication route handlers: registration, login, logout, and current user retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Profile, User
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponse

router = APIRouter()
settings = get_settings()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user account and attach an initial profile."""
    normalized_email = payload.email.strip().lower()

    # Check for existing email registration
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMAIL_ALREADY_REGISTERED",
                "message": "An account with this email address already exists.",
            },
        )

    # Securely hash password using bcrypt
    hashed = hash_password(payload.password)

    new_user = User(
        email=normalized_email,
        hashed_password=hashed,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    db.flush()  # Flush to generate new_user.id for profile foreign key

    # Initialize default profile for the user
    profile = Profile(
        user_id=new_user.id,
        target_role="Junior Python Developer",
        preferred_language="English",
        consent_analytics=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password",
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Validate credentials and issue a signed JWT access token."""
    normalized_email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    # Constant-time comparison or generic failure message to avoid account enumeration
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid email or password.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_DEACTIVATED",
                "message": "This account is inactive. Please contact support.",
            },
        )

    token_str = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(
        access_token=token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Invalidate client session",
)
def logout() -> dict:
    """Stateless logout confirmation instructing the client to delete tokens."""
    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile and account details of the authenticated caller."""
    return UserResponse.model_validate(current_user)

