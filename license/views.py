
from django.shortcuts import render
from django.http import HttpResponse
from .models import License
from django.views.decorators.csrf import csrf_exempt
import json, logging
from django.db import transaction

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

@csrf_exempt
@transaction.atomic
def add_signature(request):
    logger.debug("#".join([str("license"), str(request.method)]))
    # check if the request is post or not
    if request.method == 'POST':
        try:
            # HttpResponse("i am here")
            payload = json.loads(request.body)
            # 1. Check if the license key exists and has space
            license_key = payload['license_key']
            try:
                # check if the license key exists
                license = License.objects.get(license_key=license_key)

                # check if the license key has space
                if license.check_availability() is False:
                    return HttpResponse(status=403)

                logger.debug("#".join([str("license"), str(license.check_availability())]))

                # now parse other params and add this installation
                try:
                    installation_key = payload['installation_key']
                    customer_name = payload['customer_name']
                    installation_name = payload['installation_name']
                    ip_address = payload['ip_address']
                except:
                    return HttpResponse(status=400)

                # create a new installation
                new_installation = license.add_installation(installation_key, customer_name,
                                                            installation_name, ip_address)
                if new_installation:
                    return HttpResponse(status=200)
                else:
                    return HttpResponse(status=503)

            # send 401 if there is no key
            except License.DoesNotExist:
                logger.debug("#".join([str("license"), str("License not available")]))
                return HttpResponse(status=401)

            # send back 503 if the server is up but we are not able to process the request
            except Exception as exc:
                return HttpResponse(status=503)

        except Exception as e:
            logger.debug("#".join([str("license"), str(e)]))
            return HttpResponse(status=400)
    else:
        return HttpResponse(status=400)

@csrf_exempt
@transaction.atomic
def validate_signature(request):
    logger.debug("#".join([str("license"), str(request.method)]))
    # check if the request is post or not
    if request.method == 'POST':
        # return HttpResponse(status=503)
        try:
            # HttpResponse("i am here")
            payload = json.loads(request.body)
            # 1. Check if the license key exists and has space
            license_key = payload['license_key']
            logger.debug("#".join([str("license"), str(license_key)]))
            try:
                # check if the license key exists
                license = License.objects.get(license_key=license_key)

                # # check if the license key has space
                # if license.check_availability() is False:
                #     return HttpResponse(status=403)

                # now parse other params and add this installation
                try:
                    installation_key = payload['installation_key']
                    logger.debug("#".join([str("license"), str(installation_key)]))
                except:
                    return HttpResponse(status=400)

                # create a new installation
                existing_installation = license.validate_installation(installation_key)

                if existing_installation:
                    return HttpResponse(status=200)
                else:
                    return HttpResponse(status=401)

            # send 401 if there is no key
            except License.DoesNotExist:
                logger.debug("#".join([str("license"), str("License not available")]))
                return HttpResponse(status=401)

            # send back 503 if the server is up but we are not able to process the request
            except Exception as exc:
                return HttpResponse(status=503)

        except Exception as e:
            logger.debug("#".join([str("license"), str(e)]))
            return HttpResponse(status=400)
    else:
        return HttpResponse(status=400)


@csrf_exempt
@transaction.atomic
def delete_signature(request):
    logger.debug("#".join([str("license delete"), str(request.method)]))
    # check if the request is post or not
    if request.method == 'POST':
        # return HttpResponse(status=503)
        try:
            # HttpResponse("i am here")
            payload = json.loads(request.body)
            # 1. Check if the license key exists and has space
            license_key = payload['license_key']
            try:
                # check if the license key exists
                license = License.objects.get(license_key=license_key)

                # # check if the license key has space
                # if license.check_availability() is False:
                #     return HttpResponse(status=403)

                # now parse other params and add this installation
                try:
                    installation_key = payload['installation_key']
                except:
                    return HttpResponse(status=400)

                # create a new installation
                installation_deleted = license.delete_installation(installation_key)

                if installation_deleted:
                    return HttpResponse(status=200)
                else:
                    return HttpResponse(status=401)

            # send 401 if there is no key
            except License.DoesNotExist:
                logger.debug("#".join([str("license"), str("License not available")]))
                return HttpResponse(status=401)

            # send back 503 if the server is up but we are not able to process the request
            except Exception as exc:
                return HttpResponse(status=503)

        except Exception as e:
            logger.debug("#".join([str("license"), str(e)]))
            return HttpResponse(status=400)
    else:
        return HttpResponse(status=400)
