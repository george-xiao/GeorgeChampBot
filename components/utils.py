
# Converts seconds to MM:SS
def seconds_to_time(seconds):
    mins = str(int(seconds // 60))
    if len(mins) == 1:
        mins = "0" + mins
    secs = str(int(seconds % 60))
    if len(secs) == 1:
        secs = "0" + secs
    return mins + ":" + secs