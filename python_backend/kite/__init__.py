import pyotp
import requests
from requests.utils import urlparse
from kiteconnect import KiteConnect

KITE_LOGIN_URL="https://kite.zerodha.com/api/login"
KITE_TWOFA_URL="https://kite.zerodha.com/api/twofa"
EXTERNAL_REQUEST_TIMEOUT = 10


def login(
    user_id: str,
    password: str,
    totp_secret: str,
    api_key: str,
    api_secret: str
):
    with requests.Session() as session:
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

        api_login_response = session.get(
            f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}",
            timeout=EXTERNAL_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if api_login_response.status_code != 302:
            raise Exception(
                f"Error while logging in to kite for user-{user_id}, Error: {api_login_response.text}"
            )

        finish_api_login_response = session.get(
            api_login_response.headers["Location"],
            timeout=EXTERNAL_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if finish_api_login_response.status_code != 302:
            raise Exception(
                f"Error while logging in to kite for user-{user_id}, Error: {finish_api_login_response.text}"
            )

        location_url = finish_api_login_response.headers["Location"]
        query_string = urlparse(location_url).query
        query_dict = dict(param.split("=") for param in query_string.split("&"))
        if "request_token" in query_dict:
            req_token = query_dict["request_token"]
            kite = KiteConnect(api_key=api_key)
            token_res = kite.generate_session(req_token, api_secret=api_secret)
            access_token = token_res["access_token"]
            return access_token

        raise Exception("Failed to get access token")