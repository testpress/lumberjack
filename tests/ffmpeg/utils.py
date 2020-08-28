import mock


class ProcessMock:
    def __init__(self):
        self.stdout_line = 0

    def poll(self, *args, **kwargs):
        return True

    def read_line(self):
        self.stdout_line += 1
        if self.stdout_line == 1:
            return "Duration :=00:10:00"
        elif self.stdout_line == 2:
            return "frame=    9 fps=0.0 q=0.0 size=N/A time=00:00:00.44 bitrate=N/A speed=0.669x"
        elif self.stdout_line == 3:
            return "frame=   25 fps= 14 q=33.0 size=N/A time=00:00:01.13 bitrate=N/A speed=0.63"
        elif self.stdout_line == 4:
            return "frame=   31 fps= 13 q=31.0 size=N/A time=00:00:01.32 bitrate=N/A speed=0.575x"
        else:
            return " "

    @property
    def stdout(self):
        a = {"readline.return_value": self.read_line()}
        return mock.Mock(**a)
