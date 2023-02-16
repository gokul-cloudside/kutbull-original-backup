from rest_framework_nested import routers
from dwebdyn.views import CreatePlantsView, CreatePlantDevicesView, CreateDelRemoPlantInvertersView
from dwebdyn.views_v2 import CreatePlantDevicesViewVersion2, FTPDetailsViewV2

router = routers.SimpleRouter()
router.register(r'entry', CreatePlantsView, base_name="entry")
router.register(r'ftpdata', FTPDetailsViewV2, base_name="ftpdata")
router.register(r'devices', CreatePlantDevicesView, base_name="devices")
router.register(r'webdyn', CreatePlantDevicesViewVersion2, base_name="webdyn")

router.register(r'delremo', CreateDelRemoPlantInvertersView, base_name="delremo")

dataentry_router = routers.NestedSimpleRouter(router, r'entry', lookup='entry')