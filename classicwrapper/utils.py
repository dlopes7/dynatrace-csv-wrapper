from datetime import datetime


def millis(dt: datetime):
    return int(dt.timestamp() * 1000)
