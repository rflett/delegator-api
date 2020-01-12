import datetime


class MockActivity(object):
    def __init__(self):
        _data = []
        for i in range(1, 50):
            _data.append(
                {
                    "activity": f"activity_{i}",
                    "activity_timestamp": datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ"),
                    "event_friendly": f"Sample Event {i}",
                }
            )
        self.data = _data
