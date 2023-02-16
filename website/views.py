from django.shortcuts import render
from website.forms import BetaRequestForm
from django.utils import timezone
import logging

logger = logging.getLogger('dataglen.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

# Create your views here.
def index(request):
    request_arrival_time = timezone.now()
    if request.method == "GET":
        response = render(request, 'website/index.html')
        return response
    elif request.method == "POST":
        logger.debug("got a POST request")
        try:
            form = BetaRequestForm(request.POST)
            if form.is_valid():
                logger.debug("valid form..saving..")
                requester = form.save()
                logger.debug("saved")
                return render(request, 'website/index.html', {'requester': requester})
            else:
                logger.debug("form invalid..")
                return render(request, 'website/index.html', {'error': 'Error saving form, please write to us at contact@dataglen.com'})
        except Exception as e:
            logger.debug(str(e))
            response = render(request, 'website/index.html', {'error': 'Error saving form, please write to us at contact@dataglen.com'})
