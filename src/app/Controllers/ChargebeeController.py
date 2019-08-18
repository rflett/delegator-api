import chargebee

from app import logger
from app.Exceptions import ValidationError


class ChargebeeController(object):
    @staticmethod
    def get_subscription_details(subscription_id: str) -> dict:
        """Get some details for a chargebee subscription """
        # Get subscription from chargebee
        try:
            subscription = chargebee.Subscription.retrieve(subscription_id)
        except chargebee.api_error.InvalidRequestError:
            raise ValidationError("Subscription ID doesn't exist")

        return {
            "plan_id": subscription.subscription.plan_id,
            "customer_id": subscription.customer.id,
            "subscription_details": subscription.subscription.id
        }
