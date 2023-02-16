from customwidgets.models import FilePath, WidgetInstance, UserConfiguration
from django.contrib.auth.models import User
delete_all = True

filepaths = [{'name': "weather", 'filepath': "/static/solarrms/widgets/weather/weather.html"},
             {'name': "gauge", 'filepath': "/static/solarrms/widgets/gauge/gauge.html"},
             {'name': "meta", 'filepath': "/static/solarrms/widgets/meta/meta.html"},
             {'name': "power", 'filepath': "/static/solarrms/widgets/power-todays/power-todays.html"},
             {'name': "inverters_status", 'filepath': "/static/solarrms/widgets/inverter-status/inverter-status.html"},
             {'name': "sterling_meta", 'filepath': "/static/solarrms/widgets/sterling-meta/sterling-meta.html"},
             {'name': "energy", 'filepath': "/static/solarrms/widgets/year-energy/year-energy.html"}]

default_config = [{"x": 0, "y": 0, "width": 4, "height": 3, 'name': "weather"},
                 {"x": 4, "y": 0, "width": 4, "height": 3, 'name': "gauge"},
                 {"x": 8, "y": 0, "width": 4, "height": 3, 'name': "meta"},
                 {"x": 0, "y": 4, "width": 12, "height": 4, 'name': "power"},
                 {"x": 0, "y": 8, "width": 12, "height": 4, 'name': "inverters_status"}]

sterling_config = [{"x": 0, "y": 0, "width": 4, "height": 3, 'name': "weather"},
                 {"x": 4, "y": 0, "width": 4, "height": 3, 'name': "power"},
                 {"x": 8, "y": 0, "width": 4, "height": 3, 'name': "meta"},
                 {"x": 0, "y": 4, "width": 12, "height": 4, 'name': "energy"},
                 {"x": 0, "y": 8, "width": 12, "height": 4, 'name': "inverters_status"}]

# setup the widgets
users = User.objects.all()
for user in users:
    if delete_all and hasattr(user, "configuration"):
        user.configuration.delete()
    configuration = UserConfiguration.objects.create(user=user)
    configuration.save()

    if user.id in [43, 46, 48]:
        config_dict = sterling_config
    else:
        config_dict = default_config

    for widget in config_dict:
        new_widget = WidgetInstance.objects.create(configuration=configuration,
                                                   x=widget["x"],
                                                   y=widget["y"],
                                                   width=widget["width"],
                                                   height=widget["height"],
                                                   name=widget["name"])
        new_widget.save()

if delete_all:
    filepaths_instances = FilePath.objects.all()
    for filepath in filepaths_instances:
        filepath.delete()

for filepath in filepaths:
    fp = FilePath.objects.create(name=filepath["name"],
                                 filepath=filepath["filepath"])