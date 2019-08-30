import json

import requests

from app.Exceptions import WrapperCallFailedException


class SubscriptionApi(object):
    def __init__(self, key: str, url: str):
        self.key = key
        self.url = url

    def get_limits(self, subscription_id: str) -> dict:
        """Get a subscription's plan limits"""
        r = requests.get(
            url=f"{self.url}/subscription/{subscription_id}/limits",
            headers={
                'Authorization': self.key
            },
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def get_hosted_page(self, plan_id: str, user_dict: dict) -> str:
        """Get a hosted plan page for a new user"""
        r = requests.post(
            url=f"{self.url}/hosted-page",
            headers={
                'Content-Type': 'application/json',
                'Authorization': self.key
            },
            data=json.dumps({
                "plan_id": plan_id,
                "email": user_dict['email'],
                "first_name": user_dict['first_name'],
                "last_name": user_dict['last_name']
            }),
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get('url')
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

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
