"""
Password hashing and verification using bcrypt.

Provides secure password hashing with automatic salt generation
and configurable work factor for future-proofing against attacks.
"""

import bcrypt
from typing import Union


def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt with automatic salt generation.

    Parameters
    ----------
    password : str
        Plain text password to hash
    rounds : int, optional
        Number of rounds for bcrypt hashing (default: 12).
        Higher values increase security but also computation time.
        Recommended range: 10-14 for production systems.

    Returns
    -------
    str
        Bcrypt hashed password as a string (UTF-8 decoded)

    Examples
    --------
    >>> hashed = hash_password("SecurePassword123!")
    >>> len(hashed)
    60
    >>> hashed.startswith("$2b$")
    True

    Notes
    -----
    - Each call generates a unique salt automatically
    - The work factor (rounds) determines computation cost: 2^rounds iterations
    - Default of 12 rounds provides good security/performance balance
    - Hashed passwords are always 60 characters long
    - Format: $2b$<rounds>$<22-char-salt><31-char-hash>
    """
    # Encode password to bytes
    password_bytes = password.encode('utf-8')

    # Generate salt with specified rounds
    salt = bcrypt.gensalt(rounds=rounds)

    # Hash password with salt
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as UTF-8 string for database storage
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its bcrypt hash.

    Parameters
    ----------
    password : str
        Plain text password to verify
    password_hash : str
        Bcrypt hashed password to compare against

    Returns
    -------
    bool
        True if password matches the hash, False otherwise

    Examples
    --------
    >>> hashed = hash_password("MyPassword")
    >>> verify_password("MyPassword", hashed)
    True
    >>> verify_password("WrongPassword", hashed)
    False

    Notes
    -----
    - Timing-safe comparison to prevent timing attacks
    - Automatically extracts salt from the hash
    - Works with any bcrypt hash regardless of rounds used
    - Returns False for invalid hash formats instead of raising errors
    """
    try:
        # Encode inputs to bytes
        password_bytes = password.encode('utf-8')
        hash_bytes = password_hash.encode('utf-8')

        # Verify password (timing-safe comparison)
        return bcrypt.checkpw(password_bytes, hash_bytes)

    except (ValueError, AttributeError):
        # Invalid hash format or encoding issue
        return False


def get_password_strength(password: str) -> dict[str, Union[int, bool, str]]:
    """
    Evaluate password strength based on common criteria.

    Parameters
    ----------
    password : str
        Password to evaluate

    Returns
    -------
    dict[str, Union[int, bool, str]]
        Dictionary with strength metrics:
        - score: Overall strength score (0-5)
        - length: Password length
        - has_upper: Contains uppercase letters
        - has_lower: Contains lowercase letters
        - has_digit: Contains digits
        - has_special: Contains special characters
        - recommendation: Strength description

    Examples
    --------
    >>> result = get_password_strength("Pass123!")
    >>> result['score']
    4
    >>> result['recommendation']
    'Good'

    Notes
    -----
    Scoring:
    - 0: Very weak (< 8 characters)
    - 1: Weak (8+ chars, single type)
    - 2: Fair (8+ chars, two types)
    - 3: Moderate (8+ chars, three types)
    - 4: Good (12+ chars, four types)
    - 5: Strong (16+ chars, all types)
    """
    length = len(password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    # Count character type diversity
    diversity = sum([has_upper, has_lower, has_digit, has_special])

    # Calculate score
    if length < 8:
        score = 0
        recommendation = "Very weak - use at least 8 characters"
    elif length < 12:
        score = min(diversity, 3)
        recommendation = ["Weak", "Fair", "Moderate", "Good"][score - 1] if score > 0 else "Weak"
    elif length < 16:
        score = min(diversity + 1, 4)
        recommendation = ["Fair", "Moderate", "Good", "Good"][score - 1] if score > 0 else "Weak"
    else:
        score = 5 if diversity == 4 else 4
        recommendation = "Strong" if score == 5 else "Good"

    return {
        "score": score,
        "length": length,
        "has_upper": has_upper,
        "has_lower": has_lower,
        "has_digit": has_digit,
        "has_special": has_special,
        "recommendation": recommendation,
    }
