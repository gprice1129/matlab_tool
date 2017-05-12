import calendar

MONTHS = dict((v, k) for k, v in enumerate(calendar.month_abbr))
FFT_ID = "all_fft"
START_ID = "all_start_index"
END_ID = "all_end_index"
WBF_ID = "all_WBF"
STAMP_FORMAT = "%m/%d/%Y at %I:%M:%S %p"
HRS_IN_DAY = 24
MIN_IN_DAY = 1440
minWingBeat = 400
maxWingBeat = 1800
slidingWindow = 1024
stepSize = 128
complexityThreshold = 0.00007
interval = 5

