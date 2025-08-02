"""
External API configurations and client management.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# Square Configuration
SQUARE_SANDBOX_SECRET = os.getenv("SQUARE_SANDBOX_SECRET")
SQUARE_SANDBOX_APP_ID = os.getenv("SQUARE_SANDBOX_APP_ID")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")
SQUARE_ENVIRONMENT = os.getenv("SQUARE_ENVIRONMENT", "sandbox")

# Knock Notifications
KNOCK_API_KEY = os.getenv("KNOCK_API_KEY")
KNOCK_PUBLIC_API_KEY = os.getenv("KNOCK_PUBLIC_API_KEY")

# LangSmith Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "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")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "adaptiv-agents")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"

def get_openai_client():
    """
    Get OpenAI client instance.
    
    Returns:
        OpenAI client if API key is available, None otherwise
    """
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            return OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            print("Warning: OpenAI package not installed")
            return None
    else:
        print("Warning: OPENAI_API_KEY not set in environment variables")
        return None

def get_square_client():
    """
    Get Square client instance.
    
    Returns:
        Square client if credentials are available, None otherwise
    """
    if SQUARE_SANDBOX_SECRET and SQUARE_SANDBOX_APP_ID:
        try:
            import squareup
            from squareup.models import Environment
            
            # Determine environment
            environment = Environment.SANDBOX if SQUARE_ENVIRONMENT == "sandbox" else Environment.PRODUCTION
            
            # Initialize Square client
            client = squareup.Client(
                access_token=SQUARE_SANDBOX_SECRET,
                environment=environment
            )
            return client
        except ImportError:
            print("Warning: Square SDK not installed")
            return None
    else:
        print("Warning: Square credentials not set in environment variables")
        return None

def get_stripe_client():
    """
    Get Stripe client configuration.
    
    Returns:
        Stripe API key if available, None otherwise
    """
    if STRIPE_SECRET_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            return stripe
        except ImportError:
            print("Warning: Stripe package not installed")
            return None
    else:
        print("Warning: STRIPE_SECRET_KEY not set in environment variables")
        return None

def get_knock_client():
    """
    Get Knock notification client.
    
    Returns:
        Knock client if API key is available, None otherwise
    """
    if KNOCK_API_KEY:
        try:
            from knockapi import Knock
            return Knock(api_key=KNOCK_API_KEY)
        except ImportError:
            print("Warning: Knock SDK not installed")
            return None
    else:
        print("Warning: KNOCK_API_KEY not set in environment variables")
        return None

def get_langsmith_client():
    """
    Get LangSmith client and configure tracing.
    
    Returns:
        LangSmith client if API key is available, None otherwise
    """
    if LANGSMITH_API_KEY and LANGSMITH_TRACING:
        try:
            from langsmith import Client
            import os
            
            # Set environment variables for LangSmith
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
            
            return Client(api_key=LANGSMITH_API_KEY)
        except ImportError:
            print("Warning: LangSmith package not installed")
            return None
    else:
        if not LANGSMITH_API_KEY:
            print("Warning: LANGSMITH_API_KEY not set in environment variables")
        return None

# Validation functions
def validate_api_keys():
    """
    Validate that required API keys are present.
    
    Returns:
        Dict with validation results
    """
    validation_results = {
        "openai": OPENAI_API_KEY is not None,
        "google": GOOGLE_CLIENT_ID != "",
        "stripe": STRIPE_SECRET_KEY != "",
        "square": SQUARE_SANDBOX_SECRET is not None and SQUARE_SANDBOX_APP_ID is not None,
        "knock": KNOCK_API_KEY is not None
    }
    
    return validation_results

def get_missing_api_keys():
    """
    Get list of missing API keys.
    
    Returns:
        List of missing API key names
    """
    validation = validate_api_keys()
    return [key for key, is_valid in validation.items() if not is_valid]
