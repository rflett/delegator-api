import chargebee

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

    @staticmethod
    def increment_plan_quantity(subscription_id: str) -> None:
        """Increment the plan for this subscription """
        try:
            # Get current quantity
            subscription = chargebee.Subscription.retrieve(subscription_id)
            current_quantity = subscription.subscription.plan_quantity

            # Increment
            new_quantity = current_quantity + 1

            chargebee.Subscription.update(subscription_id, {
                "plan_quantity": new_quantity
            })
        except chargebee.api_error.InvalidRequestError:
            raise ValidationError("Subscription ID doesn't exist")

    @staticmethod
    def decrement_plan_quantity(subscription_id: str) -> None:
        """Increment the plan for this subscription """
        try:
            # Get current quantity
            subscription = chargebee.Subscription.retrieve(subscription_id)
            current_quantity = subscription.subscription.plan_quantity

            # Decrement
            new_quantity = current_quantity - 1

            if new_quantity > 0:
                chargebee.Subscription.update(subscription_id, {
                    "plan_quantity": new_quantity
                })
            else:
                raise ValidationError("Plan quantity must be greater than 0.")
        except chargebee.api_error.InvalidRequestError:
            raise ValidationError("Subscription ID doesn't exist.")
