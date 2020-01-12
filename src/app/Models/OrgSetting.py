from dataclasses import dataclass
from decimal import Decimal


@dataclass
class OrgSetting:
    """ Org settings model"""

    org_id: Decimal

    def as_dict(self):
        return {"org_id": int(self.org_id)}
