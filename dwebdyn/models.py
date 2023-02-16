from __future__ import unicode_literals

from django.db import models
from .templates import *
import os, logging
from datetime import datetime, timedelta
import errno, gzip, pytz
from dwebdyn import settings
from data_uploader import upload_data, upload_error
from dateutil import parser
from django.db import OperationalError

UTC_TZ = pytz.timezone("UTC")

logger = logging.getLogger('dwebdyn.models')
logger.setLevel(logging.DEBUG)


def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)

from dwebdyn.settings import HEARTBEAT_MINUTES

# Create your models here.
class WebdynClient(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, unique=True, help_text="Name of the client")
    slug = models.SlugField(max_length=20, blank=False, null=False, unique=True)
    active = models.BooleanField(default=False, help_text="If this client is active and should be allowed to see data")
    api_key = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Client's API key")
    ftp_dir = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="FTP directory path")
    archived_dir = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Archived directory path")
    invalid_dir = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="Invalid directory path")

    def __unicode__(self):
        return self.name


class WebdynGateway(models.Model):
    client = models.ForeignKey(WebdynClient, related_name="gateways", related_query_name="client", to_field="name",
                               help_text="Client's name")
    device_id = models.CharField(max_length=20, blank=False, null=False)
    active = models.BooleanField(default=True)
    installed_location = models.CharField(max_length=100, blank=False, null=False)
    # heartbeats, power on/off, gprs signals and alarms
    heartbeat_source_key = models.CharField(max_length=50, blank=False, null=False, help_text="DGC source key for heartbeats")
    # power on/off, gprs signals
    metadata_source_key = models.CharField(max_length=50, blank=False, null=False, help_text="DGC source key for metadata")

    def __unicode__(self):
        return self.client.__unicode__() + "_" + self.device_id

    def read_new_files(self, device_type):
        if device_type == "INV" or device_type == "MODBUS" or device_type == "IO":
            device_type = "DATA/" + device_type

        files = []
        try:
            # get all DIR files
            dir_files = os.listdir(os.path.join(self.client.ftp_dir, device_type))
        except Exception as exc:
            return []

        for file in dir_files:
            # get files of this GATEWAY only and check for proper format also
            if (file.startswith(self.device_id) and file.endswith(".gz")) or (file.startswith(self.device_id) and file.endswith(".ok")):
                try:
                    # extract timestamp - ignore anything that has NTP errors
                    ts_file = datetime.strptime(file.split("_")[-2] + ":" + file.split("_")[-1].split(".")[0], "%y%m%d:%H%M%S")
                    assert(ts_file.year != 2000)
                except:
                    logger.error("Invalid time stamp in the file name, skipping: " + file)
                    self.move_invalid_file(os.path.join(self.client.ftp_dir, device_type, file), device_type)
                    continue
                # check there's enough latency and the file should be completely written by now
                ts_now = datetime.utcnow()
                if ts_now - ts_file > timedelta(minutes=WRITE_LATENCY_MINS):
                    files.append(os.path.join(self.client.ftp_dir, device_type, file))
        return sorted(files)

    def move_invalid_file(self, file_name, device_type):
        try:
            src = file_name
            # complete path
            dst_path_dir = os.path.join(self.client.invalid_dir, self.device_id, device_type)
            try:
                os.makedirs(dst_path_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    logger.debug("error creating a new director" + str(e))
                    return False
            # prepare for the destination
            dst = os.path.join(dst_path_dir, file_name.split("/")[-1])
            # move the file
            os.rename(src, dst)
            return True
        except Exception as exc:
            logger.error(",".join(["error moving file", self.client.invalid_dir, file_name, device_type, str(exc)]))
            return False

    def move_read_file(self, file_name, device_type):
        try:
            # this will be a complete path
            src = file_name
            # file timestamp
            ts_file = datetime.strptime(file_name.split("_")[-2] + ":" + file_name.split("_")[-1].split(".")[0], "%y%m%d:%H%M%S")
            # complete path
            dst_path_dir = os.path.join(self.client.archived_dir, self.device_id, str(ts_file.year),
                                        str(ts_file.month), str(ts_file.day), device_type)
            try:
                os.makedirs(dst_path_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    logger.debug("error creating a new director" + str(e))
                    return False
            # prepare for the destination
            dst = os.path.join(dst_path_dir, file_name.split("/")[-1])
            # move the file
            os.rename(src, dst)
            return True
        except Exception as exc:
            logger.error(",".join(["error moving file", self.client.ftp_dir, file_name, device_type, str(exc)]))
            return False

    def parse_inverter_file(self, gateway, filename):
        pass

    def parse_modbus_file(self, filename):
        data_upload_counts = 0
        data_upload_error_counts = 0
        error_upload_counts = 0
        error_upload_error_counts = 0
        operational_error = False
        try:
            df = gzip.open(filename, "rb")
            file_content = df.read()
            blocks = file_content.split("ADDRMODBUS")
            for block in blocks[1:]:
                lines = block.split("\n")
                lines = [line.lstrip().strip() for line in lines]
                try:
                    modbus_address = removeNonAscii(";".join([lines[0].split(";")[1].strip(),
                                                             lines[0].split(";")[2].strip()]))
                    try:
                        modbus_device = self.modbus_devices.get(modbus_address=modbus_address, active=True)
                    except OperationalError as exc:
                        logger.error(":".join(["MODBUS OPERATIONAL ERROR", str(exc)]))
                        operational_error = True
                        continue
                    except ModbusDevice.DoesNotExist:
                        operational_error = True
                        logger.error(",".join(["MODBUS DEVICE DOES NOT EXIST", self.device_id, filename, modbus_address, lines[0]]))
                        continue
                    except Exception as exc:
                        operational_error = True
                        logger.error(",".join(["MODBUS EXCEPTION", self.device_id, filename, str(exc)]))
                        continue

                    # there's device, read data now
                    # assert that the template matches
                    assert (modbus_device.fields_template in lines[1].strip().upper())

                    # indices lines - parameters numbers - exclude the first part as that contains total items
                    parameters_numbers = lines[2].strip().split(";")[1:]
                    # read data lines
                    for line in lines[3:]:
                        if len(line) == 0:
                            continue
                        # read data
                        data = line.strip().split(";")
                        # extract timezone
                        timestamp = datetime.strptime(data[0], "%d/%m/%y-%H:%M:%S")
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        if timestamp.year < 2016:
                            raise ValueError("Invalid timestamp: " + line)
                        # read values, exclude the first part as that's timestamp
                        parameters_values = line.strip().split(";")[1:]
                        # assert that parameters numbers and values are same
                        assert (len(parameters_numbers) == len(parameters_values))
                        # prepare a data dictionary

                        data_dict = {}
                        for i in range(len(parameters_numbers)):
                            try:
                                data_dict[int(parameters_numbers[i].replace("(moy)", ""))] = float(parameters_values[i])
                            except ValueError:
                                # error parsing max and min values TODO parse these also
                                continue

                        # read data as per the template
                        device_data = {}
                        for key in MODBUS_TEMPLATES[modbus_device.fields_template]["DATA"].keys():
                            device_data[MODBUS_TEMPLATES[modbus_device.fields_template]["DATA"][key]] = data_dict[key]
                        device_data['TIMESTAMP'] = str(timestamp)

                        if settings.UPLOAD_MODBUS:
                            # try three times maximum TODO
                            response = upload_data(":".join([self.device_id, modbus_device.modbus_address]),
                                                   self.client.api_key, modbus_device.source_key, device_data)
                            if response == settings.STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
                                data_upload_counts += 1
                            # count if it's a connection failure
                            elif response == settings.STATUS_CODES.CONNECTION_FAILURE:
                                data_upload_error_counts += 1

                        # read errors as per the template
                        try:
                            if device_data['SOLAR_STATUS'] in MODBUS_TEMPLATES[modbus_device.fields_template]["SOLAR_STATUS_ERRORS"]:
                                logger.debug("SOLAR STATUS ERROR")
                                # solar status has an error status, read the erorr field
                                error_code = data_dict[MODBUS_TEMPLATES[modbus_device.fields_template]["ERROR_FIELD"][0]]
                                # assumes that the error code is a float
                                error_data = {"ERROR_TIMESTAMP": str(timestamp),
                                              "ERROR_CODE": float(error_code)}
                                # upload this error
                                if settings.UPLOAD_ERRORS:
                                    response = upload_error(":".join([self.device_id, modbus_device.modbus_address]),
                                                            self.client.api_key, modbus_device.source_key, error_data)

                                if response == settings.STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
                                    data_upload_counts += 1
                                # count if it's a connection failure
                                elif response == settings.STATUS_CODES.CONNECTION_FAILURE:
                                    data_upload_error_counts += 1

                                # log other errors
                                device_errors = [self.device_id, "OTHER_ERRORS:",
                                                 str(device_data['SOLAR_STATUS']),
                                                 str(timestamp)]
                                logger.debug(device_errors)
                                logger.debug(MODBUS_TEMPLATES[modbus_device.fields_template]["OTHER_ERRORS"])
                                for entry in MODBUS_TEMPLATES[modbus_device.fields_template]["OTHER_ERRORS"]:
                                    device_errors.append(str(data_dict[entry]))
                                logger.debug(device_errors)
                            # Add TODO code to upload errors - send timestamp also
                        except KeyError as exc:
                            # as not all devices are sending errors yet
                            continue

                except Exception as exc:
                    logger.exception("MODBUS EXCEPTION")
                    logger.debug(",".join(["MODBUS ERROR", self.device_id, filename, str(exc)]))
                    continue

            # In case there was a connection failure, we will not move the file yet.
            # Will be tried again in the next run.
            if operational_error:
                return False
            elif data_upload_error_counts == 0 and error_upload_error_counts == 0:
                return True
            else:
                return False

        except Exception as exc:
            logger.exception("MODBUS EXCEPTION")
            logger.debug(",".join(["MODBUS ERROR", self.device_id, filename, str(exc)]))


    def parse_io_file(self, filename):
        data_upload_counts = 0
        data_upload_error_counts = 0
        operational_error = False
        try:
            df = gzip.open(filename, "rb")
            file_content = df.read()
            blocks = file_content.split("TypeIO")
            for block in blocks[1:]:
                lines = block.split("\n")
                lines = [line.lstrip().strip() for line in lines]
                try:
                    try:
                        io_devices = self.io_devices.filter(active=True)
                        logger.debug(io_devices)
                        if len(io_devices) == 0:
                            # no IO devices found, return True and move the file
                            return True
                    except OperationalError as exc:
                        logger.error(",".join(["IO DEVICES OPERATIONAL ERROR:", self.device_id, filename, str(exc)]))
                        operational_error = True
                        continue
                    except Exception as exc:
                        logger.exception(",".join(["IO DEVICES NOT FOUND:", self.device_id, filename, str(exc)]))
                        operational_error = True
                        continue

                    # there are IO devices, read data now
                    # indices lines - parameters numbers - exclude the first part as that contains total items
                    parameters_numbers = lines[1].split(";")[1:]
                    # read data lines
                    for line in lines[2:]:
                        if len(line) == 0:
                            continue
                        # read data
                        data = line.strip().split(";")
                        # extract timezone
                        timestamp = datetime.strptime(data[0], "%d/%m/%y-%H:%M:%S")
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        if timestamp.year < 2016:
                            raise ValueError("Invalid timestamp: " + line)
                        # read values, exclude the first part as that's timestamp
                        parameters_values = line.strip().split(";")[1:]
                        # assert that parameters numbers and values are same
                        assert (len(parameters_numbers) == len(parameters_values))
                        # prepare a data dictionary

                        data_dict = {}
                        for i in range(len(parameters_numbers)):
                            try:
                                data_dict[int(parameters_numbers[i].replace("(moy)", ""))] = float(parameters_values[i])
                            except ValueError:
                                # error parsing max and min values TODO parse these also
                                continue

                        # read data as per the template
                        for io_device in io_devices:
                            # upload for each stream as keys can differ
                            device_data = {}
                            if io_device.coefficient_A is None or io_device.coefficient_B is None:
                                logger.error(",".join([self.device_id,
                                                       "IO COEFFICIENTS NOT SET", str(io_device.stream_name)]))
                            device_data[io_device.stream_name] = float(io_device.multiplicationFactor) * ((float(data_dict[int(io_device.input_id)]) * float(io_device.coefficient_A)) + float(io_device.coefficient_B))
                            device_data['TIMESTAMP'] = str(timestamp)

                            # TODO remove this later, do it via Kafka if possible
                            if self.device_id == "WD008311":
                                device_data['IRRADIATION'] = (device_data["IRRADIATION1"] + device_data["IRRADIATION2"])/2.0

                            # check for irradiation - calibration issues
                            if io_device.stream_name == "IRRADIATION" and device_data["IRRADIATION"] < 0:
                                device_data["IRRADIATION"] = 0.0

                            if settings.UPLOAD_IO:
                                # try three times maximum
                                response = upload_data(":".join([self.device_id, str(io_device.input_id)]),
                                                       self.client.api_key, io_device.source_key, device_data)
                                if response == settings.STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
                                    data_upload_counts += 1
                                # count if it's a connection failure
                                elif response == settings.STATUS_CODES.CONNECTION_FAILURE:
                                    data_upload_error_counts += 1

                except Exception as exc:
                    logger.debug(",".join(["IO EXCEPTION", self.device_id, filename, str(exc)]))
                    continue

            # In case there was a connection failure, we will not move the file yet.
            # Will be tried again in the next run.
            if operational_error:
                return False
            elif data_upload_error_counts == 0 :
                return True
            else:
                return False

        except Exception as exc:
            logger.debug(",".join(["IO EXCEPTION", self.device_id, filename, str(exc)]))

    def parse_log_file(self, filename):
        try:
            messages_upload_count = 0
            messages_upload_error_count = 0
            df = gzip.open(filename, "rb")
            file_content = df.read()
            lines = file_content.split("\n")
            for line in lines:
                line = line.lstrip().strip()
                try:
                    log_data = {}
                    if "Restart Gateway" in line:
                        info = line.split("Application: ")
                        timestamp = parser.parse(info[0].split(">")[1].strip())
                        assert (timestamp.year > 2015)
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        log_data = {'REBOOT_TIMESTAMP': str(timestamp),
                                    'TIMESTAMP': str(timestamp)}

                    elif "Power ON" in line:
                        info = line.split("Application: ")
                        timestamp = parser.parse(info[0].split(">")[1].strip())
                        assert (timestamp.year > 2015)
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        log_data = {'POWER_ON': 1,
                                    'TIMESTAMP': str(timestamp)}

                    elif "Power OFF" in line:
                        info = line.split("Application: ")
                        timestamp = parser.parse(info[0].split(">")[1].strip())
                        assert (timestamp.year > 2015)
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        log_data = {'POWER_ON': 0,
                                    'TIMESTAMP': str(timestamp)}

                    elif "CONNECTION_PPP;GPRS signal" in line:
                        info = line.split("Application: ")
                        timestamp = parser.parse(info[0].split(">")[1].strip())
                        assert (timestamp.year > 2015)
                        timestamp = UTC_TZ.localize(timestamp)
                        timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                        log_data = {'GPRS_SIGNAL_STRENGTH': float(line.split(" ")[-1]),
                                    'TIMESTAMP': str(timestamp)}

                    if len(log_data.keys()) > 0:
                        if settings.UPLOAD_LOG:
                            response = upload_data(":".join([self.device_id, "_LOG"]),
                                                   self.client.api_key, self.metadata_source_key, log_data)
                            if response == settings.STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
                                messages_upload_count += 1
                            # count if it's a connection failure
                            elif response == settings.STATUS_CODES.CONNECTION_FAILURE:
                                messages_upload_error_count += 1

                except Exception as exc:
                    logger.exception("LOG EXCEPTION")
                    logger.debug(",".join(["LOG EXCEPTION", self.device_id, filename, str(exc)]))
                    continue

            if messages_upload_error_count == 0:
                return True
            else:
                return False

        except UnicodeDecodeError as exc:
            logger.debug(",".join(["LOG EXCEPTION", self.device_id, filename, str(exc)]))
            # move this file
            return True
        except Exception as exc:
            logger.exception("LOG EXCEPTION")
            logger.debug(",".join(["LOG EXCEPTION", self.device_id, filename, str(exc)]))
            # move this file
            return True

    def parse_alarm_file(self, gateway, filename):
        pass

    def write_heartbeat(self, timestamp):
        heartbeat_data = {"HEARTBEAT": 1, "TIMESTAMP": str(timestamp)}
        response = upload_data(":".join([self.device_id, "_HEARTBEAT"]),
                               self.client.api_key, self.heartbeat_source_key, heartbeat_data)
        if response == settings.STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
            return True
        else:
            logger.debug("HEARTBEAT ERROR : Could not reach DGC " + str(timestamp))
            return False

    # this function reads new files for a gtateway
    def gateway_read(self):
        # restart django's connection with mysql
        from django.db import connection
        if connection.connection:
            connection.connection.close()
        connection.connection = None
        # read inverter files
        #inv_files = self.read_new_files("INV")

        # read Modbus files
        modbus_files = self.read_new_files("MODBUS")
        for modbus_file in modbus_files:
            logger.debug(modbus_file)
            move = self.parse_modbus_file(modbus_file)
            if move:
                self.move_read_file(modbus_file, "MODBUS")

        # read IO files
        io_files = self.read_new_files("IO")
        for io_file in io_files:
            logger.debug(io_file)
            move = self.parse_io_file(io_file)
            if move:
                logger.debug(move)
                self.move_read_file(io_file, "IO")

        # read LOG files
        log_files = self.read_new_files("LOG")
        log_files_ts = []
        for log_file in log_files:
            try:
                ts_file = datetime.strptime(log_file.split("_")[-2] + ":" + log_file.split("_")[-1].split(".")[0],
                                            "%y%m%d:%H%M%S")
                log_files_ts.append(ts_file)
            except Exception as exc:
                continue

        # decide and write heartbeat
        # if there's a log file in the last 30 mins, heartbeat is assumed to be available
        if len(log_files_ts) > 0 :
            if datetime.utcnow() - sorted(log_files_ts)[-1] < timedelta(minutes=HEARTBEAT_MINUTES):
                timestamp = sorted(log_files_ts)[-1]
                timestamp = UTC_TZ.localize(timestamp)
                timestamp = timestamp.astimezone(pytz.timezone("Asia/Kolkata"))
                status = self.write_heartbeat(timestamp)
                if status is False:
                    # try one more time, that's it.
                    self.write_heartbeat(sorted(log_files_ts)[-1])
            else:
                pass
                #logger.info(self.device_id + " : NO HEARTBEAT WRITTEN. LAST LOG FILE SEEN AT : " + str(sorted(log_files_ts)[-1]))
        else:
            pass
            #logger.info(self.device_id + " : NO HEARTBEAT WRITTEN. NO LOG ENTRIES TO READ")

        # parse log files now
        for log_file in log_files:
            move = self.parse_log_file(log_file)
            if move:
                self.move_read_file(log_file, "LOG")
        # read ALARM files
        # wait for WAIT_TIME and start again


class InvertersDevice(models.Model):
    gateway_device = models.ForeignKey(WebdynGateway, related_name="inverter_devices",
                                       related_query_name="gateway", to_field="id",
                                       help_text="Inverter devices installed with the gateway")
    # this could be the name of the device or address
    identifier = models.CharField(max_length=20, blank=False, null=False, help_text="Inverter's identifier that "
                                                                                    "will be present in the data file")
    fields_template = models.CharField(max_length=20, choices=INVERTERS_MANUFACTURERS, blank=False, null=False,
                                       help_text="Template that will decide the parameters to be picked up")
    source_key = models.CharField(max_length=50, blank=False, null=False, help_text="DGC source key")
    active = models.BooleanField(default=True, help_text="If this device is active and data should be parsed")

    def __unicode__(self):
        return self.gateway_device.__unicode__() + self.identifier + "_" + self.fields_template


class ModbusDevice(models.Model):
    gateway_device = models.ForeignKey(WebdynGateway, related_name="modbus_devices", related_query_name="gateway",
                                       to_field="id", help_text="Modbus devices installed with the gateway")
    # this name could be the name of the device or address
    modbus_address = models.CharField(max_length=20, blank=False, null=False,
                                      help_text="Modbus address that will be present in the data file")
    fields_template = models.CharField(max_length=50, choices=MODBUS_MANUFACTURERS, blank=False, null=False,
                                       help_text="Template that will decide the parameters to be picked up")
    source_key = models.CharField(max_length=50, blank=False, null=False, help_text="DGC source key")
    active = models.BooleanField(default=True, help_text="If this device is active and data should be parsed")

    def __unicode__(self):
        return self.gateway_device.__unicode__() + self.modbus_address + "_" + self.fields_template

class IODevice(models.Model):
    gateway_device = models.ForeignKey(WebdynGateway, related_name="io_devices", related_query_name="gateway",
                                       to_field="id",
                                       help_text="IO devices installed with the gateway")
    # from 1 to 8 - there can be these many inputs
    input_id = models.IntegerField(choices=IO_CHOICES)
    stream_name = models.CharField(max_length=50, blank=False, null=False, help_text="DGC stream name")
    source_key = models.CharField(max_length=50, blank=False, null=False, help_text="DGC source key")
    manufacturer = models.CharField(max_length=50, blank=True, null=True)
    output_range = models.CharField(choices = [('4-20mA', '4-20mA'), ('0-10V', '0-10V')], max_length=20, blank=False, null=False, help_text="sensor range")
    lower_bound = models.FloatField(blank=False, null=False, help_text="lower bound")
    upper_bound = models.FloatField(blank=False, null=False, help_text="upper bound")
    coefficient_A = models.FloatField(blank=True, null=True)
    coefficient_B = models.FloatField(blank=True, null=True)
    multiplicationFactor = models.FloatField(default=1, blank=False, null=False, help_text="Multiplication Factor")
    active = models.BooleanField(default=True, help_text="If this device is active and data should be parsed")

    def save(self, *args, **kwargs):
        super(IODevice, self).save(*args, **kwargs)
        lower_pt = 0.0
        pt_delta = 0.0

        # if the instance has been saved
        if self.id and self.coefficient_A is None and self.coefficient_B is None:
            try:
                if self.output_range == '4-20mA':
                    lower_pt = 204.6
                    pt_delta = 818.4
                elif self.output_range == '0-10V':
                    lower_pt = 0.0
                    pt_delta = 1023.0
                values_delta = self.upper_bound - self.lower_bound
                self.coefficient_A = float(values_delta)/float(pt_delta)
                self.coefficient_B = float(self.lower_bound) - float(lower_pt * self.coefficient_A)
                self.save()
            except Exception as exc:
                logger.error("Error while calculating A and B coefficients: ", str(exc))
                pass

    def __unicode__(self):
        return self.gateway_device.__unicode__() + str(self.input_id) + "_" + self.stream_name
