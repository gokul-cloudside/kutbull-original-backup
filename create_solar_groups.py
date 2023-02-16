import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from dataglen.models import Sensor, Field
from solarrms.models import PlantMetaSource,SolarPlant,SolarGroup,IndependentInverter,AJB
from django.contrib.auth.models import User


plant = SolarPlant.objects.get(slug='waaneep')
print(str(plant))
user = User.objects.get(username="pujandoshi@waaree.com")
print(str(user))
for i in range(1,21):
    groupname = "ITC"+str(i)
    group = SolarGroup.objects.create(plant=plant,user=user,slug="waaneep_itc"+str(i),name=groupname,displayName=groupname,isActive=True)
    for j in range(1,5):
        try:
            inverter = IndependentInverter.objects.get(plant=plant,name="Inverter_"+str(i)+"."+str(j))
        except Exception as ex:
            print(str(ex))
            continue
        if inverter is not None:
            group.groupIndependentInverters.add(inverter)
            group.save()
            for k in range(1,7):
                try:
                    smb = AJB.objects.get(plant=plant,name="SMB_"+str(i)+"."+str(j)+"."+str(k))
                except Exception as ex:
                    print(str(ex))
                    continue
                if smb is not None:
                    group.groupAJBs.add(smb)
                    group.save()

group = SolarGroup.objects.get(slug="waaneep_itc1")