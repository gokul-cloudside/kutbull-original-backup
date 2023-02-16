import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from solarrms.models import SolarPlant,IndependentInverter,GatewaySource

print("script started")
try:
	plants = SolarPlant.objects.all()
except Exception as exception:
	print("No solar plant found")

for plant in plants:
	try:
		inverters = IndependentInverter.objects.filter(plant=plant)
		for inverter in inverters:
			inverter.timeoutInterval = 1200
			inverter.save()
	except Exception as exception:
		print("Error in updating time out interval for inverters")

	try:
		gateways = GatewaySource.objects.filter(plant=plant)
		for gateway in gateways:
			gateway.timeoutInterval = 1200
			gateway.save()
	except Exception as exception:
		print("Error in updating time out interval for gateways")
print("script completed")