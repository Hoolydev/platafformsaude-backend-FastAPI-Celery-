"""
Password Hashing and Verification
"""

from passlib.context import CryptContext

# Contexto de criptografia usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Gera hash de uma senha usando bcrypt
    
    Args:
        password: Senha em texto plano
    
    Returns:
        Hash da senha
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha corresponde ao hash
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha
    
    Returns:
        True se a senha corresponde, False caso contrário
    """
    return pwd_context.verify(plain_password, hashed_password)
