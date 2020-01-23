import json
from os import getenv

import requests

from app.ApiWrappers import BaseWrapper
from app.Exceptions import WrapperCallFailedException


class SubscriptionApi(BaseWrapper):
    def __init__(self, jwt_secret: str, url: str):
        super().__init__(jwt_secret, url)

    def get_subscription_meta(self, subscription_id: str) -> dict:
        """Get a subscription's metadata"""
        if getenv("MOCK_SERVICES"):
            return {"status": "in_trial", "meta_data": {}}
        try:
            r = requests.get(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={"Authorization": f"Bearer {self.create_sa_token()}"},
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")
        if r.status_code == 200:
            return r.json()
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def checkout_subscription(self, **kwargs) -> str:
        """Checkout a subscription for an existing customer"""
        if getenv("MOCK_SERVICES"):
            return "https://delegator.com.au"

        try:
            r = requests.post(
                url=f"{self.url}/subscription/checkout/",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.create_sa_token()}"},
                data=json.dumps({"customer_id": kwargs["customer_id"], "plan_id": kwargs["plan_id"]}),
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code == 200:
            try:
                response = r.json()
                return response["url"]
            except ValueError:
                raise WrapperCallFailedException(f"Subscription API - failed to decode JSON response.")
            except KeyError:
                raise WrapperCallFailedException(f"Missing url from response body.")
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code} - {r.text}")

    def get_subscription(self, subscription_id: str) -> dict:
        """Get a subscription"""
        if getenv("MOCK_SERVICES"):
            return {}
        try:
            r = requests.get(
                url=f"{self.url}/subscription/{subscription_id}",
                headers={"Authorization": f"Bearer {self.create_sa_token()}"},
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")
        if r.status_code == 200:
            return r.json()
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def create_customer(self, plan_id: str, user_dict: dict) -> dict:
        """Create a customer on chargebee with the signup details"""
        if getenv("MOCK_SERVICES"):
            return {"customer_id": "mock_cust_id", "subscription_id": "mock_sub_id", "url": "https://delegator.com.au"}
        try:
            r = requests.post(
                url=f"{self.url}/customer/",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.create_sa_token()}"},
                data=json.dumps(
                    {
                        "plan_id": plan_id,
                        "user": {
                            "email": user_dict["email"],
                            "first_name": user_dict["first_name"],
                            "last_name": user_dict["last_name"],
                        },
                    }
                ),
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                raise WrapperCallFailedException(f"Subscription API - failed to decode JSON response.")
            except KeyError:
                raise WrapperCallFailedException(f"Missing customer_id from response body.")
        else:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code} - {r.text}")

    def decrement_plan_quantity(self, subscription_id: str) -> None:
        """Decrement a subscription's plan quantity"""
        if getenv("MOCK_SERVICES"):
            return
        try:
            r = requests.delete(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.create_sa_token()}"},
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")

    def increment_plan_quantity(self, subscription_id: str) -> None:
        """Increment a subscription's plan quantity"""
        if getenv("MOCK_SERVICES"):
            return
        try:
            r = requests.put(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.create_sa_token()}"},
                timeout=10,
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Subscription API - {e}")

        if r.status_code != 204:
            raise WrapperCallFailedException(f"Subscription API - {r.status_code}")
