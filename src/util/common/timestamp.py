from datetime import datetime, timedelta, date


_last_timestamp_ms = 0

def get_timestamp():
    return int(datetime.now().timestamp())

def get_timestamp_ms():
    global _last_timestamp_ms

    timestamp = int(datetime.now().timestamp() * 1000)

    if timestamp <= _last_timestamp_ms:
        timestamp = _last_timestamp_ms + 1

    _last_timestamp_ms = timestamp

    return timestamp

def get_timestamp_next_day():
    today = datetime.combine(date.today(), datetime.min.time())
    tommorrow = today + timedelta(days = 1)

    return int(tommorrow.timestamp())
