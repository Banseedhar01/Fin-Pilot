from kiteconnect import KiteConnect
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from python_backend.core.config import get_settings
from python_backend.core.logger import setup_logger
from .portfolio_data.manager import KitePortfolioDataManager
import pyotp
import requests
from requests.utils import urlparse
import re

settings = get_settings()
logger = setup_logger(__name__)

KITE_LOGIN_URL = "https://kite.zerodha.com/api/login"
KITE_TWOFA_URL = "https://kite.zerodha.com/api/twofa"
EXTERNAL_REQUEST_TIMEOUT = 10

@dataclass
class Position:
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int

@dataclass
class Holding:
    trading_symbol: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product: str
    exchange: str
    instrument_token: int
    t1_quantity: int = 0
    realised_quantity: int = 0
    authorised_quantity: int = 0
    opening_quantity: int = 0
    collateral_quantity: int = 0
    collateral_type: Optional[str] = None
    isin: Optional[str] = None

@dataclass
class Portfolio:
    holdings: List[Holding]
    positions: List[Position]
    last_updated: datetime
    net_value: float
    total_pnl: float

class KitePortfolioManager:
    def __init__(self):
        """
        Initialize the Kite Portfolio Manager
        """
        self.kite = KiteConnect(api_key=settings.KITE_API_KEY)
        self.logger = logger
        self._access_token = None
        self._portfolio_manager = None

    def set_access_token(self, access_token: str) -> None:
        """
        Set the access token for Kite API
        
        Args:
            access_token (str): The access token to set
        """
        self._access_token = access_token
        self.kite.set_access_token(access_token)
        # Initialize portfolio manager with the new access token
        self._portfolio_manager = KitePortfolioDataManager(access_token=access_token)

    def get_access_token(self) -> Optional[str]:
        """
        Get the current access token
        
        Returns:
            Optional[str]: The current access token if set, None otherwise
        """
        return self._access_token

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self._access_token is not None

    def _check_authentication(self) -> None:
        """
        Check if the user is authenticated before making API calls
        
        Raises:
            Exception: If user is not authenticated
        """
        if not self.is_authenticated():
            raise Exception("User not authenticated. Please login first.")

    def _validate_totp_secret(self, totp_secret: str) -> bool:
        """
        Validate if the TOTP secret is in correct base32 format
        
        Args:
            totp_secret: The TOTP secret to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Remove any spaces and convert to uppercase
        totp_secret = totp_secret.replace(" ", "").upper()
        
        # Check if the string only contains valid base32 characters
        if not re.match(r'^[A-Z2-7]+=*$', totp_secret):
            return False
            
        # Check if the length is valid (should be multiple of 8)
        if len(totp_secret) % 8 != 0:
            return False
            
        return True

    def handle_auto_login(self, user_id: str, password: str, totp_secret: str) -> Dict[str, Any]:
        """
        Handle the auto-login process for Kite using credentials and TOTP
        
        Args:
            user_id: The Kite user ID
            password: The Kite password
            totp_secret: The TOTP secret for 2FA
            
        Returns:
            Dict containing the response data
        """
        try:
            # Validate input data
            if not user_id or not password or not totp_secret:
                self.logger.error("Missing required credentials")
                return {
                    "status": "error",
                    "message": "Missing required credentials",
                    "data": {"detail": "User ID, password, and TOTP secret are required"}
                }
                
            # Validate TOTP secret format
            if not self._validate_totp_secret(totp_secret):
                self.logger.error("Invalid TOTP secret format")
                return {
                    "status": "error",
                    "message": "Invalid TOTP secret format",
                    "data": {
                        "detail": "TOTP secret must be in valid base32 format (A-Z, 2-7, and = for padding)"
                    }
                }
                
            # Attempt auto login
            try:
                access_token = self.auto_login(
                    user_id=user_id,
                    password=password,
                    totp_secret=totp_secret
                )
                
                if not access_token:
                    self.logger.error("Failed to get access token")
                    return {
                        "status": "error",
                        "message": "Failed to get access token",
                        "data": {"detail": "No access token received from Kite"}
                    }

                self.logger.info("Successfully completed auto login")
                return {
                    "status": "success",
                    "data": {
                        "access_token": access_token,
                        "public_token": None  # Public token not available in auto-login
                    }
                }
            except Exception as login_error:
                error_message = str(login_error)
                self.logger.error(f"Kite auto login error: {error_message}")
                
                # Handle specific error cases
                if "Non-base32 digit found" in error_message:
                    return {
                        "status": "error",
                        "message": "Invalid TOTP secret format",
                        "data": {
                            "detail": "TOTP secret must be in valid base32 format (A-Z, 2-7, and = for padding)"
                        }
                    }
                elif "Invalid credentials" in error_message:
                    return {
                        "status": "error",
                        "message": "Invalid credentials",
                        "data": {"detail": "User ID or password is incorrect"}
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Login failed",
                        "data": {"detail": error_message}
                    }
                
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"Unexpected error in kite_auto_login: {error_message}")
            return {
                "status": "error",
                "message": "An unexpected error occurred",
                "data": {"detail": error_message}
            }

    def auto_login(self, user_id: str, password: str, totp_secret: str) -> str:
        """
        Perform automatic login to Kite using user credentials and TOTP
        
        Args:
            user_id (str): Kite user ID
            password (str): Kite password
            totp_secret (str): TOTP secret for 2FA
            
        Returns:
            str: Access token
            
        Raises:
            Exception: If login fails
        """
        try:
            with requests.Session() as session:
                # Step 1: Initial login
                login_payload = {
                    "user_id": user_id,
                    "password": password,
                }
                login_response = session.post(
                    KITE_LOGIN_URL, data=login_payload, timeout=EXTERNAL_REQUEST_TIMEOUT
                )
                if login_response.status_code != 200:
                    raise Exception(
                        f"Error while logging in to kite for user-{user_id}, Error: {login_response.text}"
                    )
                req_id = login_response.json()["data"]["request_id"]

                # Step 2: 2FA
                twofa_payload = {
                    "request_id": req_id,
                    "user_id": user_id,
                    "twofa_value": pyotp.TOTP(totp_secret).now(),
                    "twofa_type": "totp",
                }
                twofa_response = session.post(
                    KITE_TWOFA_URL, data=twofa_payload, timeout=EXTERNAL_REQUEST_TIMEOUT
                )
                if twofa_response.status_code != 200:
                    raise Exception(
                        f"Error while logging in to kite for user-{user_id}, Error: {twofa_response.text}"
                    )

                # Step 3: API login
                api_login_response = session.get(
                    f"https://kite.zerodha.com/connect/login?v=3&api_key={settings.KITE_API_KEY}",
                    timeout=EXTERNAL_REQUEST_TIMEOUT,
                    allow_redirects=False,
                )
                if api_login_response.status_code != 302:
                    raise Exception(
                        f"Error while logging in to kite for user-{user_id}, Error: {api_login_response.text}"
                    )

                # Step 4: Finish API login
                finish_api_login_response = session.get(
                    api_login_response.headers["Location"],
                    timeout=EXTERNAL_REQUEST_TIMEOUT,
                    allow_redirects=False,
                )
                if finish_api_login_response.status_code != 302:
                    raise Exception(
                        f"Error while logging in to kite for user-{user_id}, Error: {finish_api_login_response.text}"
                    )

                # Step 5: Extract request token and generate session
                location_url = finish_api_login_response.headers["Location"]
                query_string = urlparse(location_url).query
                query_dict = dict(param.split("=") for param in query_string.split("&"))
                
                if "request_token" in query_dict:
                    req_token = query_dict["request_token"]
                    token_res = self.kite.generate_session(req_token, api_secret=settings.KITE_API_SECRET)
                    access_token = token_res["access_token"]
                    self.set_access_token(access_token)
                    return access_token

                raise Exception("Failed to get access token")
                
        except Exception as e:
            self.logger.error(f"Auto login error: {str(e)}")
            raise

    # Delegate portfolio operations to the portfolio manager
    def fetch_portfolio(self):
        """Fetch the complete portfolio data from Kite"""
        self._check_authentication()
        return self._portfolio_manager.fetch_portfolio()

    def get_holdings(self):
        """Fetch only holdings from Kite"""
        self._check_authentication()
        return self._portfolio_manager.get_holdings()

    def get_positions(self):
        """Fetch only positions from Kite"""
        self._check_authentication()
        return self._portfolio_manager.get_positions()

    def get_margins(self):
        """Fetch margin information from Kite"""
        self._check_authentication()
        return self._portfolio_manager.get_margins()

    def get_orders(self):
        """Fetch all orders from Kite"""
        self._check_authentication()
        return self._portfolio_manager.get_orders()

    def get_trades(self):
        """Fetch all trades from Kite"""
        self._check_authentication()
        return self._portfolio_manager.get_trades()
