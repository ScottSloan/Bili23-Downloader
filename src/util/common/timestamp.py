from datetime import datetime, timedelta, date

def get_timestamp():
    return int(datetime.now().timestamp())

def get_timestamp_ms():
    return int(datetime.now().timestamp() * 1000)

def get_timestamp_next_day():
    today = datetime.combine(date.today(), datetime.min.time())
    tommorrow = today + timedelta(days = 1)

    return int(tommorrow.timestamp())
