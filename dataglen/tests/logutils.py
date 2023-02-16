import dataglen.misc as utils
from datetime import timedelta
from datetime import datetime

print utils.count_discarded_logs(datetime.now()-timedelta(seconds=8000000), datetime.now(), 'w4pFH3kDAwli8wr')
print utils.count_all_discarded_records(datetime.now(), 'w4pFH3kDAwli8wr')

print utils.count_success_logs(datetime.now()-timedelta(seconds=8000000), datetime.now(), 'w4pFH3kDAwli8wr')
print utils.count_all_success_logs(datetime.now(), 'w4pFH3kDAwli8wr')

print utils.count_data_records(datetime.now()-timedelta(seconds=8000000), datetime.now(), 'w4pFH3kDAwli8wr')
print utils.count_all_data_records('w4pFH3kDAwli8wr', datetime.now())

