import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, Optional, Tuple
import os


def get_secret(secret_name: str, region_name: str = "eu-north-1", 
               access_key_id: Optional[str] = None, 
               secret_access_key: Optional[str] = None) -> Dict:
    """
    Retrieve a secret from AWS Secrets Manager.
    
    Args:
        secret_name: The name or ARN of the secret
        region_name: The AWS region where the secret is stored
        access_key_id: Optional AWS access key ID (if not provided, uses env vars or credentials file)
        secret_access_key: Optional AWS secret access key (if not provided, uses env vars or credentials file)
        
    Returns:
        Dictionary containing the secret values (parsed from JSON)
        
    Raises:
        ClientError: If there's an error retrieving the secret
        NoCredentialsError: If AWS credentials are not configured
    """
    # Create a Secrets Manager client
    # boto3 will automatically look for credentials in:
    # 1. Parameters passed to Session (if provided)
    # 2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    # 3. AWS credentials file (~/.aws/credentials)
    # 4. IAM role (if running on EC2/ECS/Lambda)
    session_kwargs = {}
    if access_key_id and secret_access_key:
        session_kwargs['aws_access_key_id'] = access_key_id
        session_kwargs['aws_secret_access_key'] = secret_access_key
    
    session = boto3.session.Session(**session_kwargs)
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e
    
    secret = get_secret_value_response['SecretString']
    
    # Parse the JSON secret
    try:
        return json.loads(secret)
    except json.JSONDecodeError:
        # If it's not JSON, return as string
        return {"secret": secret}


def get_database_url_from_secret(secret_name: Optional[str] = None, 
                                  region_name: str = "eu-north-1",
                                  access_key_id: Optional[str] = None,
                                  secret_access_key: Optional[str] = None,
                                  db_host: Optional[str] = None,
                                  db_name: Optional[str] = None,
                                  db_port: Optional[int] = None) -> Tuple[str, str]:
    """
    Get database connection URLs from AWS Secrets Manager.
    
    The secret should contain RDS connection details. If host/dbname are missing from the secret,
    they can be provided as parameters or environment variables (DB_HOST, DB_NAME, DB_PORT).
    
    Args:
        secret_name: The name or ARN of the secret (if None, uses env var)
        region_name: The AWS region where the secret is stored
        access_key_id: Optional AWS access key ID
        secret_access_key: Optional AWS secret access key
        db_host: Optional database host (falls back to DB_HOST env var, then secret)
        db_name: Optional database name (falls back to DB_NAME env var, then secret, then 'postgres')
        db_port: Optional database port (falls back to DB_PORT env var, then secret, then 5432)
        
    Returns:
        Tuple of (database_url, database_url_async)
    """
    if secret_name is None:
        secret_name = os.getenv("AWS_SECRET_NAME")
        if not secret_name:
            raise ValueError("AWS_SECRET_NAME environment variable is required")
    
    secret = get_secret(secret_name, region_name, access_key_id, secret_access_key)
    
    # Extract database connection details
    # AWS RDS secrets can have different formats, so we try multiple field names
    username = secret.get("username")
    password = secret.get("password")
    
    # Try different sources for host (parameter > env var > secret)
    host = (
        db_host or
        os.getenv("DB_HOST") or
        secret.get("host") or 
        secret.get("address") or 
        secret.get("endpoint") or
        secret.get("dbInstanceIdentifier")
    )
    
    # Try different sources for port (parameter > env var > secret > default)
    port = (
        db_port or
        (os.getenv("DB_PORT") and int(os.getenv("DB_PORT"))) or
        secret.get("port") or 
        secret.get("dbPort") or 
        5432
    )
    
    # Try different sources for database name (parameter > env var > secret > default)
    dbname = (
        db_name or
        os.getenv("DB_NAME") or
        secret.get("dbname") or 
        secret.get("database") or 
        secret.get("dbInstanceIdentifier") or
        "postgres"  # Default database name
    )
    
    # Validate required fields
    if not username or not password:
        raise ValueError(
            f"Secret must contain 'username' and 'password' fields. "
            f"Got: {list(secret.keys())}"
        )
    
    # If host is still missing, raise an error with helpful message
    if not host:
        raise ValueError(
            f"Database host not found. Secret contains: {list(secret.keys())}. "
            f"Please provide DB_HOST environment variable or ensure the secret contains 'host' field."
        )
    
    # Build connection URLs
    # Escape special characters in password
    from urllib.parse import quote_plus
    password_escaped = quote_plus(password)
    
    database_url = f"postgresql://{username}:{password_escaped}@{host}:{port}/{dbname}"
    database_url_async = f"postgresql+asyncpg://{username}:{password_escaped}@{host}:{port}/{dbname}"
    
    return database_url, database_url_async

