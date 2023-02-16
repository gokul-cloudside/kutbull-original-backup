from solarrms.models import SolarPlant, PVSystInfo
from django.db import IntegrityError

MONTH_MAPPING = {'January':1,
                 'February':2,
                 'March':3,
                 'April':4,
                 'May':5,
                 'June':6,
                 'July':7,
                 'August':8,
                 'September':9,
                 'October':10,
                 'November':11,
                 'December':12}

SHEET_HEADER_MAPPING = {'Months': 'MONTH',
                        'GHI (kWh/m2)':'GHI_IRRADIANCE',
                        'In-plane (kWh/m2)':'IN_PLANE_IRRADIANCE',
                        'Expected Specific Yield (kWh/kWp)':'SPECIFIC_PRODUCTION',
                        'Expected Generation (kWh)':'NORMALISED_ENERGY_PER_DAY'}

MONTH_DAY_MAPPING = {1:31,
                     2:28,
                     3:31,
                     4:30,
                     5:31,
                     6:30,
                     7:31,
                     8:31,
                     9:30,
                     10:31,
                     11:30,
                     12:31}


import xlrd
# Method to parse the excel sheet for pvsyst report
def parse_pvsyst_excel_report(plant, file_path):
    try:
        book = xlrd.open_workbook(file_path)
        # first sheet
        first_sheet = book.sheet_by_index(0)
        no_of_rows_in_first_sheet = first_sheet.nrows
        no_of_columns_in_first_sheet = first_sheet.ncols
        first_sheet_headers = first_sheet.row_slice(rowx=2,
                                                    start_colx=0,
                                                    end_colx=no_of_columns_in_first_sheet-1)

        # plant capacity
        plant_capacity_row = first_sheet.row_slice(rowx=0,
                                                start_colx=4,
                                                end_colx=5)

        try:
            plant_capacity = float(plant_capacity_row[0].value)
        except Exception as exception:
            print(str(exception))

        # second sheet
        second_sheet = book.sheet_by_index(1)
        no_of_rows_in_second_sheet = second_sheet.nrows
        no_of_columns_in_second_sheet = second_sheet.ncols
        second_sheet_headers = second_sheet.row_slice(rowx=2,
                                                      start_colx=0,
                                                      end_colx=2)

        headers_list = []
        for header in range(len(first_sheet_headers)):
            headers_list.append(SHEET_HEADER_MAPPING[str(first_sheet_headers[header].value)])
        if no_of_rows_in_first_sheet == 16:
            for j in range(3, no_of_rows_in_second_sheet):
                second_sheet_values = second_sheet.row_slice(rowx=j,
                                                             start_colx=0,
                                                             end_colx=2)
                print second_sheet_values
                second_sheet_actual_year = second_sheet_values[0].value
                second_sheet_degradation_percent = second_sheet_values[1].value
                for i in range(3,no_of_rows_in_first_sheet):
                    print i, j
                    if i == 15:
                        if j== 3:
                            year_row_index = no_of_rows_in_first_sheet
                            first_sheet_final_row_values = first_sheet.row_slice(rowx=year_row_index-1,
                                                                                 start_colx=0,
                                                                                 end_colx=no_of_columns_in_first_sheet-1)

                            for index in range(no_of_columns_in_first_sheet-2):
                                parameterName = headers_list[index+1]
                                timePeriodType = 'YEAR'
                                timePeriodValue = 0
                                if parameterName=='NORMALISED_ENERGY_PER_DAY':
                                    parameterValue = (first_sheet_final_row_values[index+1].value)/(365*plant_capacity)
                                else:
                                    parameterValue = (first_sheet_final_row_values[index+1].value)/365

                                print parameterName, timePeriodType, timePeriodValue, parameterValue
                                try:
                                    pv_syst_info = PVSystInfo.objects.create(plant=plant,
                                                                             parameterName=parameterName,
                                                                             timePeriodType=timePeriodType,
                                                                             timePeriodValue=timePeriodValue,
                                                                             timePeriodYear=0,
                                                                             parameterValue=parameterValue)
                                    pv_syst_info.save()
                                except IntegrityError:
                                    existing_info = PVSystInfo.objects.get(plant=plant,
                                                                           parameterName=parameterName,
                                                                           timePeriodType=timePeriodType,
                                                                           timePeriodYear=0,
                                                                           timePeriodValue=timePeriodValue)
                                    existing_info.parameterValue = parameterValue
                                    existing_info.save()
                                except Exception as exception:
                                    print(str(exception))
                        else:
                            for index in range(no_of_columns_in_first_sheet-2):
                                parameterName = headers_list[index+1]
                                timePeriodType = 'YEAR'
                                timePeriodValue = 0
                                if parameterName == 'SPECIFIC_PRODUCTION':
                                    parameterValue = ((first_sheet_final_row_values[index+1].value)/365)*(100-float(second_sheet_degradation_percent))/100
                                elif parameterName == 'NORMALISED_ENERGY_PER_DAY':
                                    parameterValue = (((first_sheet_final_row_values[index+1].value)/365)*(100-float(second_sheet_degradation_percent))/100)/plant_capacity
                                else:
                                    parameterValue = (first_sheet_final_row_values[index+1].value)/365
                                print parameterName, timePeriodType, timePeriodValue, parameterValue
                                try:
                                    pv_syst_info = PVSystInfo.objects.create(plant=plant,
                                                                             parameterName=parameterName,
                                                                             timePeriodType=timePeriodType,
                                                                             timePeriodValue=timePeriodValue,
                                                                             timePeriodYear=second_sheet_actual_year,
                                                                             parameterValue=parameterValue)
                                    pv_syst_info.save()
                                except IntegrityError:
                                    existing_info = PVSystInfo.objects.get(plant=plant,
                                                                           parameterName=parameterName,
                                                                           timePeriodType=timePeriodType,
                                                                           timePeriodYear=second_sheet_actual_year,
                                                                           timePeriodValue=timePeriodValue)
                                    existing_info.parameterValue = parameterValue
                                    existing_info.save()
                                except Exception as exception:
                                    print(str(exception))
                    else:
                        if j==3:
                            first_sheet_row_values = first_sheet.row_slice(rowx=i,
                                                                            start_colx=0,
                                                                            end_colx=no_of_columns_in_first_sheet-1)
                            for index in range(no_of_columns_in_first_sheet-2):
                                parameterName = headers_list[index+1]
                                timePeriodType = 'MONTH'
                                timePeriodValue = MONTH_MAPPING[first_sheet_row_values[0].value]
                                if parameterName=='NORMALISED_ENERGY_PER_DAY':
                                    parameterValue = ((first_sheet_row_values[index+1].value)/MONTH_DAY_MAPPING[timePeriodValue])/plant_capacity
                                else:
                                    parameterValue = (first_sheet_row_values[index+1].value)/MONTH_DAY_MAPPING[timePeriodValue]
                                print parameterName, timePeriodType, timePeriodValue, parameterValue
                                try:
                                    pv_syst_info = PVSystInfo.objects.create(plant=plant,
                                                                             parameterName=parameterName,
                                                                             timePeriodType=timePeriodType,
                                                                             timePeriodValue=timePeriodValue,
                                                                             timePeriodYear=0,
                                                                             parameterValue=parameterValue)
                                    pv_syst_info.save()
                                except IntegrityError:
                                    existing_info = PVSystInfo.objects.get(plant=plant,
                                                                           parameterName=parameterName,
                                                                           timePeriodType=timePeriodType,
                                                                           timePeriodYear=0,
                                                                           timePeriodValue=timePeriodValue)
                                    existing_info.parameterValue = parameterValue
                                    existing_info.save()
                                except Exception as exception:
                                    print(str(exception))
                        else:
                            first_sheet_row_values = first_sheet.row_slice(rowx=i,
                                                                            start_colx=0,
                                                                            end_colx=no_of_columns_in_first_sheet-1)
                            for index in range(no_of_columns_in_first_sheet-2):
                                parameterName = headers_list[index+1]
                                timePeriodType = 'MONTH'
                                timePeriodValue = MONTH_MAPPING[first_sheet_row_values[0].value]
                                if parameterName == 'SPECIFIC_PRODUCTION':
                                    parameterValue = ((first_sheet_row_values[index+1].value)/MONTH_DAY_MAPPING[timePeriodValue])*(100-float(second_sheet_degradation_percent))/100
                                elif  parameterName == 'NORMALISED_ENERGY_PER_DAY':
                                    parameterValue = (((first_sheet_row_values[index+1].value)/MONTH_DAY_MAPPING[timePeriodValue])*(100-float(second_sheet_degradation_percent))/100)/plant_capacity
                                else:
                                    parameterValue = (first_sheet_row_values[index+1].value)/MONTH_DAY_MAPPING[timePeriodValue]
                                print parameterName, timePeriodType, timePeriodValue, parameterValue
                                try:
                                    pv_syst_info = PVSystInfo.objects.create(plant=plant,
                                                                             parameterName=parameterName,
                                                                             timePeriodType=timePeriodType,
                                                                             timePeriodValue=timePeriodValue,
                                                                             timePeriodYear=second_sheet_actual_year,
                                                                             parameterValue=parameterValue)
                                    pv_syst_info.save()
                                except IntegrityError:
                                    existing_info = PVSystInfo.objects.get(plant=plant,
                                                                           parameterName=parameterName,
                                                                           timePeriodType=timePeriodType,
                                                                           timePeriodYear=second_sheet_actual_year,
                                                                           timePeriodValue=timePeriodValue)
                                    existing_info.parameterValue = parameterValue
                                    existing_info.save()
                                except Exception as exception:
                                    print(str(exception))
            return True
        else:
            return False
    except Exception as exception:
        print(str(exception))
