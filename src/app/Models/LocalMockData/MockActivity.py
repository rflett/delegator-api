import datetime


class MockActivity(object):
    def __init__(self):
        self.data = [
                {
                    "activity": "activity_1",
                    "activity_timestamp": datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ"),
                    "event_friendly": "Sample Event 1"
                },
                {
                    "activity": "activity_2",
                    "activity_timestamp": datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ"),
                    "event_friendly": "Sample Event 2"
                },
                {
                    "activity": "activity_3",
                    "activity_timestamp": datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ"),
                    "event_friendly": "Sample Event 3"
                }
            ]
