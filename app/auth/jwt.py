"""
JWT Token Management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import os

# Configurações JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret-key-use-random-string")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um access token JWT
    
    Args:
        data: Dados a serem codificados no token (user_id, tenant_id, role, etc)
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Cria um refresh token JWT
    
    Args:
        data: Dados a serem codificados no token
    
    Returns:
        Refresh token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifica e decodifica um token JWT
    
    Args:
        token: Token JWT a ser verificado
    
    Returns:
        Payload do token se válido, None caso contrário
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica um token JWT (sem verificar assinatura)
    Útil para debugging
    
    Args:
        token: Token JWT
    
    Returns:
        Payload do token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": False})
        return payload
    except JWTError as e:
        raise ValueError(f"Token inválido: {str(e)}")
