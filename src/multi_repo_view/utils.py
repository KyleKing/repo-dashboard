from datetime import datetime


def truncate(text: str, max_length: int, suffix: str = "~") -> str:
    """Truncate text with suffix if longer than max_length"""
    if len(text) <= max_length:
        return text.ljust(max_length)
    return text[:max_length - len(suffix)] + suffix


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2h ago')"""
    delta = datetime.now() - dt

    if delta.days > 365:
        years = delta.days // 365
        return f"{years}y ago"
    if delta.days > 0:
        return f"{delta.days}d ago"

    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"

    minutes = delta.seconds // 60
    if minutes > 0:
        return f"{minutes}m ago"

    return "now"
