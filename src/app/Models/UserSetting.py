from dataclasses import dataclass
from decimal import Decimal


@dataclass
class UserSetting:
    """ User settings model"""
    user_id: Decimal
    tz_offset: str = "+0000"

    def as_dict(self):
        return {
            "user_id": int(self.user_id),
            "tz_offset": self.tz_offset
        }
