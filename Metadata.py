import datetime as dt

class Metadata:
    def __init__(self, date, time, temperature, pressure):
        date_time = date + ' ' + time[:-4]
        self.time_info = dt.datetime.strptime(date_time, '%y/%m/%d %H:%M:%S')
        self.temperature = temperature
        self.pressure = pressure
