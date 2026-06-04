"""
Auth Router - Endpoints pour l'authentification (signup, login, logout, me)
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
import logging

from ..database import get_db
from ..config import settings
from ..models.user import User
from ..schemas.user import (
    UserCreate,
    UserOut,
    Token,
    TokenData,
    UserLogin,
    AdminUserUpdate,
    PasswordResetRequest,
    PasswordResetConfirm,
    ProfileUpdate,
    PasswordChange,
    EmailVerification,
    ApprovalResponse,
    SignupResponse,
)
from ..utils import security
from ..utils.rate_limit import LimitRule, enforce_rate_limit, record_failed_login
from ..utils.email_service import (
    send_reset_email,
    send_email_verification,
    send_approval_notification,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# OAuth2 scheme pour extraire le token depuis le header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


LOGIN_LIMIT = LimitRule(max_requests=10, per_seconds=60)
SIGNUP_LIMIT = LimitRule(max_requests=5, per_seconds=300)
FORGOT_PASSWORD_LIMIT = LimitRule(max_requests=5, per_seconds=300)


def _same_site_value() -> str:
    value = (settings.COOKIE_SAMESITE or "lax").lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


def _cookie_domain() -> str | None:
    domain = settings.COOKIE_DOMAIN.strip()
    return domain or None


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    same_site = _same_site_value()
    secure = settings.COOKIE_SECURE
    if same_site == "none":
        secure = True

    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.COOKIE_PATH,
        domain=_cookie_domain(),
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=settings.COOKIE_PATH,
        domain=_cookie_domain(),
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=_cookie_domain(),
    )
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=_cookie_domain(),
    )


def get_access_token_from_request(request: Request, bearer_token: str | None) -> str:
    if bearer_token:
        return bearer_token
    cookie_token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ========== CRUD Helpers ==========

def get_user_by_username(db: Session, username: str) -> User | None:
    """Récupère un utilisateur par username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Récupère un utilisateur par email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Récupère un utilisateur par ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    """Récupère tous les utilisateurs avec pagination"""
    return db.query(User).order_by(User.id).offset(skip).limit(limit).all()


def ensure_admin(current_user: User) -> None:
    """Bloque l'acces si l'utilisateur n'est pas admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def create_user(db: Session, user_in: UserCreate, is_approved: bool = False, is_email_verified: bool = False) -> User:
    """Crée un nouvel utilisateur avec mot de passe hashé"""
    hashed_password = security.get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        role="user",
        is_active=is_approved,
        is_approved=is_approved,
        is_email_verified=is_email_verified
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, db_user: User, data: dict) -> User:
    """Met a jour un utilisateur avec les champs fournis."""
    for field, value in data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, db_user: User) -> None:
    """Supprime un utilisateur."""
    db.delete(db_user)
    db.commit()


# ========== Dependency pour obtenir l'utilisateur courant ==========

async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency pour récupérer l'utilisateur authentifié depuis le token JWT.
    
    Raises:
        HTTPException 401: Si le token est invalide, expiré ou révoqué
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_value = get_access_token_from_request(request, token)
        # Décoder le token
        payload = security.decode_access_token(token_value)
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_version: int = int(payload.get("tv", 0))
        
        if username is None:
            raise credentials_exception
        
        # Vérifier si le token a été révoqué
        if jti and security.is_token_revoked(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(username=username, jti=jti, token_version=token_version)
    except JWTError:
        raise credentials_exception
    
    # Récupérer l'utilisateur depuis la BD
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if token_data.token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token version mismatch. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


# ========== Endpoints ==========

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint pour créer un nouveau compte utilisateur (inscription).
    
    - Vérifie que le username et l'email ne sont pas déjà utilisés
    - Hash le mot de passe avant stockage
    - Envoie un email de vérification
    - Le compte n'est pas approuvé jusqu'à l'approbation admin
    - Retourne les infos utilisateur (sans mot de passe)
    """
    enforce_rate_limit(request, "auth_signup", SIGNUP_LIMIT)
    normalized_username = user_in.username.strip()
    if len(normalized_username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters"
        )

    normalized_email = user_in.email.strip().lower() if user_in.email else None

    # Vérifier si le username existe déjà
    existing_user = get_user_by_username(db, normalized_username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Vérifier si l'email existe déjà (si fourni)
    if normalized_email:
        existing_email = get_user_by_email(db, normalized_email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    sanitized_user = UserCreate(
        username=normalized_username,
        email=normalized_email,
        password=user_in.password,
        role=user_in.role,
    )
    
    # Créer le nouvel utilisateur (non approuvé, email non vérifié)
    user = create_user(db, sanitized_user, is_approved=False, is_email_verified=False)
    
    # Envoyer un email de vérification
    if user.email:
        try:
            verification_token = security.create_email_verification_token(user.email)
            send_email_verification(user.email, verification_token, settings.FRONTEND_URL)
        except Exception as e:
            # L'utilisateur est créé mais l'email n'a pas pu être envoyé
            print(f"Error sending verification email: {e}")
    
    return user


@router.post("/login", response_model=Token)
def login(
    response: Response,
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Endpoint pour se connecter et obtenir un token JWT.
    
    - Utilise JSON avec email et password
    - Vérifie le mot de passe
    - Vérifie que l'email est vérifié
    - Vérifie que le compte est approuvé par l'admin
    - Retourne un access_token JWT
    """
    enforce_rate_limit(request, "auth_login", LOGIN_LIMIT)
    # Récupérer l'utilisateur par email
    user = get_user_by_email(db, login_data.email)
    
    # Vérifier que l'utilisateur existe et que le mot de passe est correct
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        attempts = record_failed_login(login_data.email, request)
        logger.warning(
            "failed_login email=%s ip=%s attempts_15m=%s",
            login_data.email,
            request.client.host if request.client else "unknown",
            attempts,
        )
        if attempts >= 5:
            logger.error(
                "security_alert high_failed_login email=%s ip=%s attempts_15m=%s",
                login_data.email,
                request.client.host if request.client else "unknown",
                attempts,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier que l'email est vérifié
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email en cours de vérification. Vérifiez votre boîte email."
        )
    
    # Vérifier que le compte est approuvé par l'admin
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Votre compte n'est pas encore approuvé. Veuillez patienter jusqu'à l'approbation de l'administrateur."
        )

    # Vérifier que l'utilisateur est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Créer le token JWT
    access_token = security.create_access_token(subject=user.username, token_version=user.token_version)
    refresh_token = security.create_refresh_token(subject=user.username, token_version=user.token_version)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "message": "Login successful",
    }


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
def refresh_session(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = security.decode_refresh_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    username = payload.get("sub")
    jti = payload.get("jti")
    token_version = int(payload.get("tv", 0))
    exp = payload.get("exp")

    if not username or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")
    if security.is_token_revoked(jti, db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")
    if token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid")

    security.revoke_token(jti, exp, db, token_type="refresh", username=username)

    new_access_token = security.create_access_token(subject=user.username, token_version=user.token_version)
    new_refresh_token = security.create_refresh_token(subject=user.username, token_version=user.token_version)
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "message": "Session refreshed",
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Endpoint pour se déconnecter (révoque le token actuel).
    
    - Extrait le jti du token
    - Ajoute le jti à la blacklist
    - Le token ne pourra plus être utilisé
    
    Note: En production, implémenter un stockage persistant (Redis/DB)
    """
    try:
        token_value = get_access_token_from_request(request, token)
        payload = security.decode_access_token(token_value)
        jti = payload.get("jti")
        username = payload.get("sub")
        
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not contain jti"
            )
        
        # Révoquer le token
        security.revoke_token(jti, payload.get("exp"), db, token_type="access", username=username)
        refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                refresh_payload = security.decode_refresh_token(refresh_token)
                refresh_jti = refresh_payload.get("jti")
                if refresh_jti:
                    security.revoke_token(
                        refresh_jti,
                        refresh_payload.get("exp"),
                        db,
                        token_type="refresh",
                        username=username,
                    )
            except JWTError:
                pass
        clear_auth_cookies(response)
        
        return {"message": "Successfully logged out"}
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/logout-all", status_code=status.HTTP_200_OK)
def logout_all_sessions(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.token_version += 1
    db.add(current_user)
    db.commit()
    clear_auth_cookies(response)
    return {"message": "All sessions have been revoked"}


@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint protégé pour obtenir les infos de l'utilisateur connecté.
    
    - Nécessite un token JWT valide dans le header Authorization
    - Retourne les infos de l'utilisateur authentifié
    """
    return current_user


@router.get("/users", response_model=list[UserOut])
def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint protégé pour récupérer tous les utilisateurs.
    
    - Nécessite un token JWT valide
    - Pagination avec skip et limit
    - Retourne la liste des utilisateurs
    """
    ensure_admin(current_user)
    users = get_all_users(db, skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=UserOut)
def get_user_by_id_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint protégé pour récupérer un utilisateur par son ID.
    
    - Nécessite un token JWT valide
    - Retourne les infos de l'utilisateur demandé
    """
    ensure_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/users/username/{username}", response_model=UserOut)
def get_user_by_username_endpoint(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint protégé pour récupérer un utilisateur par son username.
    
    - Nécessite un token JWT valide
    - Retourne les infos de l'utilisateur demandé
    """
    ensure_admin(current_user)
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user_endpoint(
    user_id: int,
    user_in: AdminUserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met a jour un utilisateur (username/email/role) — necessite un token valide.
    """
    ensure_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    data = user_in.model_dump(exclude_unset=True)

    if "username" in data:
        target_username = data["username"].strip()
        if not target_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty"
            )

        existing_user = get_user_by_username(db, target_username)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        data["username"] = target_username

    if "email" in data and data["email"] is not None:
        target_email = data["email"].strip().lower()
        existing_email = get_user_by_email(db, target_email)
        if existing_email and existing_email.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        data["email"] = target_email

    updated_user = update_user(db, user, data)
    return updated_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime un utilisateur — nécessite un token valide."""
    ensure_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    delete_user(db, user)
    return None


@router.put("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Met a jour le profil de l'utilisateur courant (username/email)."""
    data = payload.model_dump(exclude_unset=True)

    if "username" in data:
        target_username = data["username"].strip()
        if not target_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty"
            )
        existing_user = get_user_by_username(db, target_username)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        current_user.username = target_username

    if "email" in data and data["email"] is not None:
        target_email = data["email"].strip().lower()
        existing_email = get_user_by_email(db, target_email)
        if existing_email and existing_email.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = target_email

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_200_OK)
def change_my_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change le mot de passe de l'utilisateur courant."""
    if not security.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    if security.verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    current_user.hashed_password = security.get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()

    return {"message": "Password updated successfully"}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(payload: EmailVerification, db: Session = Depends(get_db)):
    """
    Valide l'adresse email avec un token.
    
    Le token vient du lien d'email envoyé lors de l'inscription.
    """
    try:
        data = security.decode_email_verification_token(payload.token)
        email: str = data.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.is_email_verified:
        return {"message": "Email already verified"}
    
    user.is_email_verified = True
    db.add(user)
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.get("/pending-users", response_model=list[UserOut])
def get_pending_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les utilisateurs en attente d'approbation (pas approuvés).
    
    Accessible uniquement par les administrateurs.
    """
    ensure_admin(current_user)
    pending_users = db.query(User).filter(
        User.is_approved == False
    ).order_by(User.id).all()
    return pending_users


@router.post("/approve-user/{user_id}", response_model=ApprovalResponse)
def approve_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approuve un utilisateur en attente.
    
    Accessible uniquement par les administrateurs.
    Envoie un email de notification à l'utilisateur.
    """
    ensure_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_approved:
        if not user.is_active:
            user.is_active = True
            db.add(user)
            db.commit()

        return ApprovalResponse(
            user_id=user.id,
            is_approved=True,
            message="User already approved"
        )
    
    user.is_approved = True
    user.is_active = True
    db.add(user)
    db.commit()
    
    # Envoyer un email de notification
    if user.email:
        try:
            send_approval_notification(user.email, is_approved=True)
        except Exception as e:
            print(f"Error sending approval notification: {e}")
    
    return ApprovalResponse(
        user_id=user.id,
        is_approved=True,
        message="User approved successfully"
    )


@router.post("/reject-user/{user_id}", response_model=ApprovalResponse)
def reject_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rejette un utilisateur en attente et supprime son compte.
    
    Accessible uniquement par les administrateurs.
    Envoie un email de notification à l'utilisateur.
    """
    ensure_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Envoyer un email de notification avant suppression
    if user.email:
        try:
            send_approval_notification(user.email, is_approved=False)
        except Exception as e:
            print(f"Error sending rejection notification: {e}")
    
    # Supprimer l'utilisateur
    delete_user(db, user)
    
    return ApprovalResponse(
        user_id=user.id,
        is_approved=False,
        message="User rejected and deleted"
    )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    """
    Génère un token de réinitialisation (retourné directement ici faute d'email).
    En production, envoyer le token par email et ne pas révéler son contenu.
    """
    enforce_rate_limit(request, "auth_forgot_password", FORGOT_PASSWORD_LIMIT)
    user = get_user_by_email(db, payload.email)

    # Réponse générique pour ne pas divulguer l'existence d'un compte
    if not user:
        return {"message": "Si l'e-mail existe, un lien de réinitialisation a été envoyé."}

    # Bloquer la réinitialisation tant que le compte est en attente d'approbation admin.
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte n'est pas encore approuvé par l'administrateur. Vous ne pouvez pas réinitialiser votre mot de passe pour le moment."
        )

    reset_token = security.create_reset_token(user.username)
    try:
        send_reset_email(user.email, reset_token, settings.FRONTEND_URL)
    except Exception as exc:
        logger.exception("Failed to send reset email for user '%s': %s", user.username, exc)
        # Réponse générique: ne jamais divulguer de token sensible
        return {"message": "Si l'e-mail existe, un lien de réinitialisation a été envoyé."}

    return {"message": "Si l'e-mail existe, un lien de réinitialisation a été envoyé."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe à partir d'un token de reset."""
    try:
        data = security.decode_reset_token(payload.token)
        username = data.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_hashed = security.get_password_hash(payload.new_password)
    user.hashed_password = new_hashed
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Password has been reset successfully"}
