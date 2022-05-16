import pytz

from datetime import datetime, timedelta, date

# from dateutil.relativedelta import relativedelta
# from dateutil.parser import parse

from math import floor

from calendar import monthrange

from holidays import Brazil


def get_localized_datetime(datetime_object, timezone=pytz.timezone("America/Belem")):
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    return timezone.localize(datetime_object)


def get_localized_current_datetime(timezone=pytz.timezone("America/Belem")):
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    return get_localized_datetime(datetime_object=datetime.now(), timezone=timezone)


def get_timezone(timezone):
    return pytz.timezone(timezone)


def convert_from_string(datetime_str, template="%Y-%m-%d %H:%M:%S"):
    datetime_obj = datetime.strptime(datetime_str, template)
    return datetime_obj


def convert_timezone(datetime_obj, tz_from=pytz.utc, tz_to=pytz.timezone("America/Belem")):
    if isinstance(tz_from, str):
        tz_from = pytz.timezone(tz_from)
    if isinstance(tz_to, str):
        tz_to = pytz.timezone(tz_to)
    datetime_from = tz_from.localize(dt=datetime_obj)
    datetime_to = datetime_from.astimezone(tz=tz_to)
    return datetime_to


def convert_to_utc(datetime_obj):
    tz_from = datetime_obj.tzinfo
    datetime_obj = datetime_obj.replace(tzinfo=None)
    return convert_timezone(datetime_obj=datetime_obj, tz_from=tz_from, tz_to=pytz.utc)


def parse_from_string(datetime_str, dayfirst=True):
    datetime_obj = parse(datetime_str, dayfirst=dayfirst)
    return datetime_obj


def from_timestamp(timestamp, timezone=pytz.timezone("America/Belem")):
    return datetime.fromtimestamp(timestamp, tz=timezone)


def to_timestamp(datetime_obj):
    return datetime_obj.timestamp()


def get_month_interval(year, month, timezone=pytz.timezone("America/Belem")):
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    start_datetime = get_localized_datetime(
        datetime_object=datetime(
            year=year,
            month=month,
            day=1
        ),
        timezone=timezone
    )
    end_datetime = get_localized_datetime(
        datetime_object=datetime(
            year=year,
            month=month,
            day=monthrange(year=year, month=month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        ),
        timezone=timezone
    )
    interval_datetime = (start_datetime, end_datetime)
    return interval_datetime


def get_day_interval(year, month, day, timezone=pytz.timezone("America/Belem")):
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    start_datetime = get_localized_datetime(
        datetime_object=datetime(
            year=year,
            month=month,
            day=day
        ),
        timezone=timezone
    )
    end_datetime = get_localized_datetime(
        datetime_object=datetime(
            year=year,
            month=month,
            day=day,
            hour=23,
            minute=59,
            second=59,
            microsecond=999999
        ),
        timezone=timezone
    )
    interval_datetime = (start_datetime, end_datetime)
    return interval_datetime


def get_rounded_minutes_interval(datetime_object, interval=5):
    minute_floor = floor(datetime_object.minute / interval) * interval
    delta_minute = datetime_object.minute - minute_floor
    delta_second = datetime_object.second
    delta_millisecond = int(datetime_object.strftime("%f"))
    start = datetime_object - timedelta(minutes=delta_minute, seconds=delta_second, milliseconds=delta_millisecond)
    end = start + timedelta(minutes=interval)
    start += timedelta(microseconds=1)
    interval_datetime = (start, end)
    return interval_datetime


def get_datetime_weekday(datetime_object, use_iso_weekday=False, use_name=True):
    if use_iso_weekday:
        weekday = datetime_object.isoweekday()
        start_day = 1
    else:
        weekday = datetime_object.weekday()
        start_day = 0
    if use_name:
        days_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        weekday = days_names[weekday - start_day]
    return weekday


def get_months_in_interval(start_datetime, end_datetime):
    months = []
    current_datetime = start_datetime
    while current_datetime <= end_datetime:
        months.append((current_datetime.year, current_datetime.month))
        current_datetime += timedelta(days=monthrange(year=current_datetime.year, month=current_datetime.month)[1])
    return months


def get_days_in_interval(start_datetime, end_datetime):
    days = []
    current_datetime = start_datetime
    while current_datetime <= end_datetime:
        days.append((current_datetime.year, current_datetime.month, current_datetime.day))
        current_datetime += timedelta(days=1)
    return days


def is_weekend(datetime_object):
    weekday = get_datetime_weekday(datetime_object=datetime_object, use_name=True)
    if weekday == "saturday" or weekday == "sunday":
        return True
    else:
        return False


def is_holiday(datetime_object, country=Brazil):
    if datetime_object.date() in country(years=datetime_object.year).keys():
        return True
    else:
        return False


def interval_to_tuple(interval):
    (start, end) = interval.split("-")
    start_hour = int(start.split(":")[0])
    start_minute = int(start.split(":")[1])
    end_hour = int(end.split(":")[0])
    end_minute = int(end.split(":")[1])
    return start_hour, start_minute, end_hour, end_minute


def is_in_interval(datetime_object, interval_start, interval_end):
    if interval_start <= datetime_object <= interval_end:
        return True
    else:
        return False


def get_next_month(year, month):
    date_now = date(year=year, month=month, day=1)
    date_next = date_now + relativedelta(months=1)
    year = date_next.year
    month = date_next.month
    return year, month


def get_previous_month(year, month):
    date_now = date(year=year, month=month, day=1)
    date_prev = date_now + relativedelta(months=-1)
    year = date_prev.year
    month = date_prev.month
    return year, month


def get_tariff_rate(datetime_object, peak_times=("18:30-21:30",), intermediate_times=("17:30-18:30", "21:30-22:30")):
    if is_weekend(datetime_object=datetime_object):
        return "off_peak"
    elif is_holiday(datetime_object=datetime_object):
        return "off_peak"
    else:
        for time in peak_times:
            start_hour, start_minute, end_hour, end_minute = interval_to_tuple(interval=time)
            start_peak = datetime(
                year=datetime_object.year,
                month=datetime_object.month,
                day=datetime_object.day,
                hour=start_hour,
                minute=start_minute,
                tzinfo=datetime_object.tzinfo
            )
            end_peak = datetime(
                year=datetime_object.year,
                month=datetime_object.month,
                day=datetime_object.day,
                hour=end_hour,
                minute=end_minute,
                tzinfo=datetime_object.tzinfo
            )
            if is_in_interval(datetime_object=datetime_object, interval_start=start_peak, interval_end=end_peak):
                return "peak"

        for time in intermediate_times:
            start_hour, start_minute, end_hour, end_minute = interval_to_tuple(interval=time)
            start_intermediate = datetime(
                year=datetime_object.year,
                month=datetime_object.month,
                day=datetime_object.day,
                hour=start_hour,
                minute=start_minute,
                tzinfo=datetime_object.tzinfo
            )
            end_intermediate = datetime(
                year=datetime_object.year,
                month=datetime_object.month,
                day=datetime_object.day,
                hour=end_hour,
                minute=end_minute,
                tzinfo=datetime_object.tzinfo
            )
            if is_in_interval(datetime_object=datetime_object, interval_start=start_intermediate, interval_end=end_intermediate):
                return "intermediate"

        return "off_peak"
