from collections import deque


class MovingAverageFilter:

    def __init__(self, window_size=5):
        self.values = deque(maxlen=window_size)

    def update(self, new_value):
        self.values.append(new_value)

        return sum(self.values) / len(self.values)


def stabilize_weight(readings, window_size=5):
    """
    Calculate a stable weight from multiple raw readings.

    readings:
        List of raw weight measurements.

    Example:
        [12.5, 13.4, 12.8, 13.2, 13.0]
    """

    if not readings:
        raise ValueError("No weight readings provided.")

    weight_filter = MovingAverageFilter(window_size)

    stable_weight = None

    for reading in readings:
        stable_weight = weight_filter.update(reading)

    return round(stable_weight, 2)