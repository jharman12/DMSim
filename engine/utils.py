import re

# ---------------------------------------------------------------------------
# Debug mode
# ---------------------------------------------------------------------------
# Set to True to enable verbose print output during a simulation run.
# Can be toggled at runtime via set_debug() or from main.py --debug flag.
DEBUG: bool = False


def set_debug(enabled: bool):
    """Enable or disable debug print output globally."""
    global DEBUG
    DEBUG = enabled


def dprint(*args, **kwargs):
    """Print only when DEBUG mode is enabled."""
    if DEBUG:
        print(*args, **kwargs)


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def safe_log(message, map_obj=None):
    """
    Log a message to the combat log if the map has one.
    Works for both interactive (GUI log) and simulated (no log) encounters.
    """
    if map_obj and hasattr(map_obj, 'combatLog') and callable(map_obj.combatLog):
        map_obj.combatLog(message)


def stringToTuple(string):
    return tuple([int(x) for x in re.split(r'\(|\)|,', string) if x != ''])


def text2int(textnum, numwords={}):
    if textnum.isdigit():
        return int(textnum)
    if not numwords:
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen",
        ]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        scales = ["hundred", "thousand", "million", "billion", "trillion"]
        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):
            numwords[word] = (1, idx)
        for idx, word in enumerate(tens):
            numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales):
            numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
            return 'Not a number'
        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current


def numberAfterString(text, target_string):
    """Finds the first digit that follows a given string in a text."""
    index = text.find(target_string)
    if index == -1:
        return None
    index += len(target_string)
    range_val = re.findall(r'\d+', text[index:])[0]
    return int(range_val)


def numberBeforeString(text, target_string):
    """Finds the first digit that precedes a given string in a text."""
    index = text.find(target_string)
    if index == -1:
        return None
    range_val = re.findall(r'\d+', text[:index])[-1]
    return int(range_val)
