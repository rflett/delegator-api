import json
import typing

import requests

from app.Exceptions import WrapperCallFailedException


class SubscriptionApi(object):
    def __init__(self, key: str, url: str):
        self.key = key
        self.url = url

    def get_limits(self, subscription_id: str) -> dict:
        """Get a subscription's plan quantity"""
        r = requests.get(
            url=f"{self.url}/subscription/{subscription_id}/quantity",
            headers={
                'Authorization': self.key
            },
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def create_customer(self, plan_id: str, user_dict: dict, org_name: str) -> typing.Tuple[str, str]:
        """Create a customer on chargebee with the signup details"""
        r = requests.post(
            url=f"{self.url}/customer/",
            headers={
                'Authorization': self.key,
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                "plan_id": plan_id,
                "user": user_dict,
                "org_name": org_name
            }),
            timeout=10
        )
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
        r = requests.delete(
            url=f"{self.url}/subscription/{subscription_id}/quantity",
            headers={
                'Authorization': self.key
            },
            timeout=10
        )
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def increment_plan_quantity(self, subscription_id: str) -> None:
        """Increment a subscription's plan quantity"""
        r = requests.put(
            url=f"{self.url}/subscription/{subscription_id}/quantity",
            headers={
                'Authorization': self.key
            },
            timeout=10
        )
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")
