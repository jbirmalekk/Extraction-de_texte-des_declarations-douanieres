"""
Auth Router - Endpoints pour l'authentification (signup, login, logout, me)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

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
from ..utils.email_service import (
    send_reset_email,
    send_email_verification,
    send_approval_notification,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme pour extraire le token depuis le header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
        is_active=True,
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
    token: str = Depends(oauth2_scheme),
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
        # Décoder le token
        payload = security.decode_access_token(token)
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        
        if username is None:
            raise credentials_exception
        
        # Vérifier si le token a été révoqué
        if jti and security.is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(username=username, jti=jti)
    except JWTError:
        raise credentials_exception
    
    # Récupérer l'utilisateur depuis la BD
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


# ========== Endpoints ==========

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Endpoint pour créer un nouveau compte utilisateur (inscription).
    
    - Vérifie que le username et l'email ne sont pas déjà utilisés
    - Hash le mot de passe avant stockage
    - Envoie un email de vérification
    - Le compte n'est pas approuvé jusqu'à l'approbation admin
    - Retourne les infos utilisateur (sans mot de passe)
    """
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
    # Récupérer l'utilisateur par email
    user = get_user_by_email(db, login_data.email)
    
    # Vérifier que l'utilisateur existe et que le mot de passe est correct
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier que l'utilisateur est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
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
            detail="Account not approved yet. Please wait for admin approval."
        )
    
    # Créer le token JWT
    access_token = security.create_access_token(subject=user.username)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(token: str = Depends(oauth2_scheme)):
    """
    Endpoint pour se déconnecter (révoque le token actuel).
    
    - Extrait le jti du token
    - Ajoute le jti à la blacklist
    - Le token ne pourra plus être utilisé
    
    Note: En production, implémenter un stockage persistant (Redis/DB)
    """
    try:
        payload = security.decode_access_token(token)
        jti = payload.get("jti")
        
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not contain jti"
            )
        
        # Révoquer le token
        security.revoke_token(jti)
        
        return {"message": "Successfully logged out"}
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


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
    Récupère les utilisateurs en attente d'approbation (email vérifié, pas approuvé).
    
    Accessible uniquement par les administrateurs.
    """
    ensure_admin(current_user)
    pending_users = db.query(User).filter(
        User.is_email_verified == True,
        User.is_approved == False
    ).all()
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
        return ApprovalResponse(
            user_id=user.id,
            is_approved=True,
            message="User already approved"
        )
    
    user.is_approved = True
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
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Génère un token de réinitialisation (retourné directement ici faute d'email).
    En production, envoyer le token par email et ne pas révéler son contenu.
    """
    user = get_user_by_email(db, payload.email)

    # Réponse générique pour ne pas divulguer l'existence d'un compte
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}

    reset_token = security.create_reset_token(user.username)
    try:
        send_reset_email(user.email, reset_token, settings.FRONTEND_URL)
    except Exception:
        # En cas d'échec d'envoi, on peut encore retourner le token pour debug
        return {
            "message": "Reset token generated (email failed)",
            "reset_token": reset_token,
            "expires_minutes": 15,
        }

    return {"message": "If the email exists, a reset link has been sent."}


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
