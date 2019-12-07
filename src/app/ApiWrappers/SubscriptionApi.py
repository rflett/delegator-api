import json
import typing
from os import getenv

import requests

from app.ApiWrappers import BaseWrapper
from app.Exceptions import WrapperCallFailedException


class SubscriptionApi(BaseWrapper):
    def __init__(self, jwt_secret: str, url: str):
        super().__init__(jwt_secret, url)

    def get_subscription(self, subscription_id: str) -> dict:
        """Get a subscription's plan quantity"""
        if getenv('MOCK_SERVICES'):
            return {}
        try:
            r = requests.get(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")
        if r.status_code == 200:
            return r.json()
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def create_customer(self, plan_id: str, user_dict: dict, org_name: str) -> typing.Tuple[str, str]:
        """Create a customer on chargebee with the signup details"""
        if getenv('MOCK_SERVICES'):
            return 'mock_cust_id', 'https://delegator.com.au'
        try:
            r = requests.post(
                url=f"{self.url}/customer/",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                data=json.dumps({
                    "plan_id": plan_id,
                    "user": user_dict,
                    "org_name": org_name
                }),
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code == 200:
            try:
                res = r.json()
                return res['customer_id'], res['url']
            except ValueError:
                raise WrapperCallFailedException(f"Subscription API - failed to decode JSON response.")
            except KeyError:
                raise WrapperCallFailedException(f"Missing customer_id from response body.")
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code} - {r.text}")

    def decrement_plan_quantity(self, subscription_id: str) -> None:
        """Decrement a subscription's plan quantity"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.delete(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def increment_plan_quantity(self, subscription_id: str) -> None:
        """Increment a subscription's plan quantity"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.put(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")
