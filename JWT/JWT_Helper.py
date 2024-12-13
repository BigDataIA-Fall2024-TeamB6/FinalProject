import datetime
from datetime import timedelta, timezone
from typing import Any
import jwt
from fastapi import HTTPException, status
import logging

# Configure logger for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FASTAPI Services")

# Secret key for encoding and decoding JWT
SECRET_KEY = "your_secret_key"  # Replace with a secure key in production

def create_jwt_token(data: dict) -> dict[str, Any]:
    """
    Create a JWT token with a payload and expiration time.
    
    Args:
        data (dict): Data to include in the JWT payload.

    Returns:
        dict: A dictionary containing the JWT token and its type.
    """
    logger.info("FASTAPI Services - create_jwt_token() - Create a JWT token with an expiration time")
    
    # Set token expiration time to 60 minutes from the current time
    expiration = datetime.datetime.now(timezone.utc) + timedelta(minutes=60)
    
    # Create the token payload with expiration and provided data
    token_payload = {
        "expiration": str(expiration), 
        **data
    }
    
    # Encode the payload using the secret key and HS256 algorithm to create the token
    token = jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")
    
    # Prepare the response token dictionary
    token_dict = {
        'token': token,
        'token_type': "Bearer"
    }
    logger.info("FASTAPI Services - create_jwt_token() - JWT Token created with payload")
    return token_dict

def decode_jwt_token(token: str):
    """
    Decode and validate a JWT token.
    
    Args:
        token (str): The JWT token to decode.

    Returns:
        dict: The decoded JWT payload if valid.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    logger.info("FASTAPI Services - decode_jwt_token() - Decode JWT token & Validation")
    try:
        # Decode the JWT token
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        logger.info("FASTAPI Services - decode_jwt_token() - Decoded JWT token successfully")
        return decoded_token
    
    except Exception as e:
        logger.error(f"FASTAPI Services Error - decode_jwt_token() encountered an error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
