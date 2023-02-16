from rest_framework_tracking.models import APIRequestLog
from django.utils import timezone
import datetime
from tabulate import tabulate
from django.core.mail import EmailMultiAlternatives

from_email = 'alerts@dataglen.com'
to_email = 'nishant@dataglen.com'
email_subject = 'API Error at DGC'

def send_api_fail_email(api_errors):
    try:
        html_content = '<body style="background-color:red;"> <h1><center> API Errors </center></h1></body></br>'
        html_content += 'Hi,<br> Following API errors have occurred at dataglen.com :<br><br>'
        api_error_table = []
        for error in api_errors:
            error_table = []
            error_table.append(error.user)
            error_table.append(error.requested_at)
            error_table.append(error.response_ms)
            error_table.append(error.path)
            error_table.append(error.remote_addr)
            error_table.append(error.method)
            error_table.append(error.data)
            error_table.append(error.response)
            error_table.append(error.status_code)
            api_error_table.append(error_table)
        api_html_table = tabulate(api_error_table, headers=['User', 'Error Time', 'Response Time', 'Error Path', 'IP Address', 'Request Method', 'Request Body', 'Response', 'Status Code'], tablefmt='html')
        html_content += api_html_table
        html_content += '<br><br> Thank You, <br> Team DataGlen <br>'
        html_content += '<br><body style="background-color:powderblue;" align="right"><h5>Connect with us </h5><a href="https://twitter.com/dataglen">Twitter</a> <a href="https://www.linkedin.com/company/dataglen">LinkedIn</a> <a href="https://www.facebook.com/dataglen/">Facebook</body>'
        text_content = ''
        html_content = html_content
        msg = EmailMultiAlternatives(email_subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as exception:
        print("Error in sending email : " + str(exception))


def monitor_api():
    try:
        final_time = timezone.now()
        initial_time = final_time - datetime.timedelta(minutes=5)
        api_errors = APIRequestLog.objects.filter(status_code=500,
                                                  requested_at__gte=initial_time,
                                                  requested_at__lt=final_time)
        if len(api_errors)>0:
            send_api_fail_email(api_errors)
    except Exception as exception:
        print("Error in getting the failed API's : " + str(exception))