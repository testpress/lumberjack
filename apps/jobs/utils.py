import re

def convert_to_sec(time):
    h, m, s = time.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def get_time(key, string, default):
    time = re.search('(?<=' + key + ')\w+:\w+:\w+', string)
    return convert_to_sec(time.group(0)) if time else default
