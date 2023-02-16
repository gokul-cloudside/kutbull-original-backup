from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.mixins import ProfileDataInAPIs
from .models import OTP
import logging
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)



#Api view to post prediction data from source and save
class V1_OTPDataViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    OTP_OPERATIONS = ('generate', 'validate')
    def create(self, request, **kwargs):
        """

        :param request: request parameter including post and data
        :param plant_slug: plan_slug from solarplant
        :param kwargs:
        :return:
        """
        #import pdb;pdb.set_trace()
        try:
            post_data = request.data
            if post_data['operation'] not in V1_OTPDataViewSet.OTP_OPERATIONS:
                return Response("Please provide valid operation", status=status.HTTP_400_BAD_REQUEST)

            try:
                if post_data['operation'] == 'generate':
                    if post_data['phone_no'].isdigit() and len(post_data['phone_no']) > 9 and len(
                            post_data['phone_no']) > 13:
                        return Response("Please provide valid phone no", status=status.HTTP_400_BAD_REQUEST)

                    result = OTP.send_otp(post_data['phone_no'])
                    return Response(str(result), status=status.HTTP_201_CREATED)

                if post_data['operation'] == 'validate':
                    result = OTP.validate_otp(post_data['otp_id'], post_data['otp'])
                    return Response(str(result), status=status.HTTP_200_OK)

            except Exception as exception:
                logger.debug(str(exception))
                return Response("", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
