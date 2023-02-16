from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError
from django.template import RequestContext, loader
from dataviz.forms import IndexForm, LiveForm
from datetime import datetime, timedelta
from django.http import JsonResponse
import json, math, sets
from dataviz.models import JPlug_Data_Table, JPlug_Energy_Data_Table, JPlug_Status_Table

import logging
logger = logging.getLogger(__name__)
# TODO - 1 - change it to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

def get_premise_loads():
    premise_loads = {}
    try:
        info = JPlug_Status_Table.objects.all()
        for entry in info:
            try:
                premise_loads[entry.premise].append(entry.load)
            except KeyError:
                premise_loads[entry.premise] = [entry.load]
        return premise_loads
    except :
        return None


def index(request):
    form = LiveForm()
    premise_loads = get_premise_loads()
    if premise_loads == None:
        return HttpResponseServerError("Server error: No premise found")
    return render(request, 'dataviz/visualization.html', {'result_set': {}, 'premise_loads' : premise_loads, 'premise_list':premise_loads.keys()})

def show_data(request):
    if request.method == 'POST':
        form = IndexForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            query_premise_name = cleaned_data['premise_name']
            query_load_name = cleaned_data['load_name']
            # times are hacked for now.
            query_start_date = datetime.strptime(str(cleaned_data['start_date']) + " 00:00:00", "%Y-%m-%d %H:%M:%S")
            query_end_date = datetime.strptime(str(cleaned_data['end_date']) + " 23:59:00", "%Y-%m-%d %H:%M:%S")

            # since the cassandra driver subtracts 5.5 hours before returning the value, we must subtract
            # the same duration from query values as well.
            time_offset = timedelta(minutes=330)
            query_start_date = query_start_date - time_offset
            query_end_date = query_end_date - time_offset

            db_rows = JPlug_Energy_Data_Table.objects.filter(premise=query_premise_name,
                                                             load=query_load_name,
                                                             label_time__gte=query_start_date,
                                                             label_time__lte=query_end_date).order_by('-label_time')

            result_set = []

            for row in db_rows:
                result_set.append({'premise_name': row['premise'],
                                  'load_name': row['load'],
                                  'label_time': str(row['label_time']),
                                  'energy': str(row['energy'])
                                   })

            return JsonResponse(result_set, safe=False)
            #return HttpResponse(json.dumps(result_set),content_type='application/json')

            #return render(request, 'dataviz/show_data.html', {'result_set': result_set})
            #return HttpResponse(template.render(context))
    else:
        form = IndexForm()
        return render(request, 'dataviz/index.html', {'form': form})

def show_live_data(request):
    premise_loads = get_premise_loads()
    logger.debug("Premise/load information obtained.")
    if premise_loads == None:
        return HttpResponseServerError("Server error. No premise found")

    if request.method == 'POST':
        form = LiveForm(request.POST)
        '''TODO : find out why form.is_valid() is failing '''
        if form.is_valid():
            cleaned_data = form.cleaned_data
            query_premise_name = cleaned_data['premise_name']
            query_load_name = cleaned_data['load_name']
            st = str(cleaned_data['start_time'])
            et = str(cleaned_data['end_time'])
        else:
            query_premise_name = form.data["premise_name"]
            query_load_name = form.data["load_name"]
            st = str(form.data['start_time'])
            et = str(form.data['end_time'])
            # times are hacked for now.
        query_start_time = datetime.strptime(st, "%Y/%m/%d %H:%M")
        query_end_time = datetime.strptime(et, "%Y/%m/%d %H:%M")
    
        # since the cassandra driver subtracts 5.5 hours before returning the value, we must subtract
        # the same duration from query values as well.
        time_offset = timedelta(minutes=330)
        query_start_time = query_start_time - time_offset
        query_end_time = query_end_time - time_offset

        if query_load_name == "All":
            premise_query_loads = premise_loads[query_premise_name]
        else:
            premise_query_loads = [query_load_name]

        logger.log(premise_query_loads)
        result_set = []
        for load in premise_query_loads:
            db_rows = JPlug_Energy_Data_Table.objects.filter(premise=query_premise_name,
                                                             load=load,
                                                             label_time__gte=query_start_time,
                                                             label_time__lte=query_end_time).order_by('-label_time')
            for row in db_rows:
                if math.isnan(row['energy']):
                    result_set.append({'premise': str(row['load']),
                                      'date': str(row['label_time']),
                                      'apc': float(0.0)
                                       })                    
                    continue
                result_set.append({'premise': str(row['load']),
                                  'date': str(row['label_time']),
                                  'apc': float(row['energy'])
                                   })

        return render(request, 'dataviz/visualization.html', {'result_set': result_set, 'premise_loads' : premise_loads, 'premise_list':premise_loads.keys()})
    else:
        return render(request, 'dataviz/visualization.html', {'result_set': {}, 'premise_loads' : premise_loads, 'premise_list':premise_loads.keys()})

def generate_data_status(request):
    premise_loads = get_premise_loads()
    logger.debug("Premise/load information obtained.")
    if premise_loads == None:
        return HttpResponseServerError("Server error. No premise found")

    status_data = []
    if request.method == "GET":
        try:
            for premise in premise_loads.keys():
                for load in premise_loads[premise]:
                    raw_data_records = JPlug_Data_Table.objects.filter(premise=premise, load=load)
                    energy_data_records = JPlug_Energy_Data_Table.objects.filter(premise=premise, load=load)
                    if len(raw_data_records)>=1 and len(energy_data_records) >= 1:
                        status_data.append((premise, load, len(raw_data_records), str(raw_data_records[-1].sample_time),
                                                            len(energy_data_records), str(energy_data_records[-1].label_time)))
            return HttpResponse((status_data), status=200)
        except Exception as E:
            return HttpResponseServerError("Error while generating the status : " + str(E))

