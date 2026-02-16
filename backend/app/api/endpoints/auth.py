from fastapi import APIRouter, HTTPException, status, Depends
from app.models import UserCreate, UserLogin, UserResponse, SignupResponse, ApiKeyResponse, User
from app.core.auth import authenticate_user, create_user, get_current_user, refresh_api_key, create_access_token

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def signup(user_data: UserCreate):
    """
    Create a new user account
    """
    try:
        user = await create_user(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
        
        return SignupResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            is_active=user.is_active
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/login", response_model=UserResponse)
async def login(login_data: UserLogin):
    """
    Authenticate user and return user info with API key and JWT token
    """
    user = await authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        api_key=user.api_key,
        access_token=access_token,
        created_at=user.created_at,
        is_active=user.is_active
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    # Create a new access token for the response
    access_token = create_access_token(data={"sub": str(current_user.id)})
    
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        api_key=current_user.api_key,
        access_token=access_token,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )


@router.post("/refresh-api-key", response_model=ApiKeyResponse)
async def refresh_user_api_key(current_user: User = Depends(get_current_user)):
    """
    Generate a new API key for the current user
    """
    try:
        new_api_key = await refresh_api_key(current_user)
        
        return ApiKeyResponse(
            api_key=new_api_key,
            message="API key refreshed successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh API key: {str(e)}"
        )