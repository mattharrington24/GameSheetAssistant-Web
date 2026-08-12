def convert_to_time_remaining(elapsed_time, period):
    if period == "OT":
        period_length_seconds = 8 * 60
    else:
        period_length_seconds = 17 * 60

    minutes, seconds = elapsed_time.split(":")
    elapsed_seconds = int(minutes) * 60 + int(seconds)

    remaining_seconds = period_length_seconds - elapsed_seconds

    remaining_minutes = remaining_seconds // 60
    remaining_seconds = remaining_seconds % 60

    return f"{remaining_minutes}:{remaining_seconds:02d}"
