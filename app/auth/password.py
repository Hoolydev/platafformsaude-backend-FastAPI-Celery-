"""
Password Hashing and Verification
"""

import bcrypt

def hash_password(password: str) -> str:
    """
    Gera hash de uma senha usando bcrypt
    
    Args:
        password: Senha em texto plano
    
    Returns:
        Hash da senha
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha corresponde ao hash
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha
    
    Returns:
        True se a senha corresponde, False caso contrário
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
