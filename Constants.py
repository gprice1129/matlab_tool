import datetime as dt

DATA_POINTS_PER_FILE=1024
NT='nt'
DEFAULT_EXTENSION='.csv'
INPUT_DATE_FORMAT='%d/%m/%y %H:%M:%S'
STAMP_FORMAT='%m/%d/%y at %H:%M:%S'
MIN_DATE=dt.datetime(dt.MINYEAR,1,1,0,0,0)
MAX_DATE=dt.datetime(dt.MAXYEAR,12,31,23,59,59)
MIN_IN_DAY = 1440
