from solarrms.models import SolarPlant, IndependentInverter, PlantMetaSource, GatewaySource
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from errors.models import ErrorStorageByStream
from monitoring.views import write_a_data_write_ttl

def copy_alpine_data():
    try:
        print("alpine data copy cronjob started")

        until_time = datetime.utcnow()
        from_time = until_time - timedelta(minutes=60)

        from_inverters = ['u7ZUCz0saytnzDr', '6vjOHZhuoMOfFW6', '8pxnq4nNlzTsZsv', 'zijXxKVrjO7CYFj', 'XQpLG7rHeIsyVNT',
                          'NhEfN9yH8pcr89B',
                          # ge demo data copy
                          '0fLSr6NSTegf0QI', 'u7ZUCz0saytnzDr', '6vjOHZhuoMOfFW6', '8pxnq4nNlzTsZsv',
                          'zijXxKVrjO7CYFj', 'XQpLG7rHeIsyVNT', 'NhEfN9yH8pcr89B', 'L09UnVEnfaedSAg', 'k6rD5GPYnVTaV5n',
                          'oHckmwlhyVxmli6', 'MS7NRavxkVZqLtN',

                          # # edp demo data copy
                          'mKHjVdWoJ0zuahn', '1q5DiHO7SzoNyid', 'n6kRF6pl40Dsrud', 'MKYu2EvtEVFo1Dv',
                          'N1hEMbtrLWwoP9u', 'fByHWh9CUJZuT1g', 'qB3dVvLASkKOKdY', 'gpbGcxUvE0PI2Hr', '8CNirAfE1fEZbV8',
                          'wWFJZCx1UgMbv9r', '87Wbhgbde4VxwWQ', '3HgVEUozeREx8LO', '545I3TEJyeF0y5U', 'Fnm1zDwa9FjSdWO',
                          'EkMqPIrqUcp0sP9', 'piPrAElSirgtFZN', 'ly1R0fD50QJhPLh', 'JFqZBNSwZVDye8V', '91QLKdEsqjUMD3J',
                          'XVBR5rErZ4QAuzK', 'xLlrH6CayMzy5hQ', 'p1vZGBk3h6eiV0j', 'XbXwqXlktDJOg5x', 'h87Agfu3DdPsIOB',
                          '05OaYFjjOoHQ2td', 'NaNCk7zKvCefzD4', 'raVHCGLAWKPW3HW', '1k0RBQnYuYaSVc7', 'DAm5VCpLqmeKOEo',
                          'SrnzMI8W793EDvs', 'm5tMbPWMM4RMecE', 'O9ptH92ScrFkPdN', 'Iz9BoN7WGbGVvNp', 'ouCcPh5IGLc88Xn',
                          'm8hap8ULb0s3Frf',

                          # ausnet data copy
                          'mKHjVdWoJ0zuahn', '1q5DiHO7SzoNyid', 'n6kRF6pl40Dsrud', 'MKYu2EvtEVFo1Dv', 'N1hEMbtrLWwoP9u',
                          'fByHWh9CUJZuT1g', 'qB3dVvLASkKOKdY', 'gpbGcxUvE0PI2Hr', '8CNirAfE1fEZbV8', 'wWFJZCx1UgMbv9r',
                          '87Wbhgbde4VxwWQ', '3HgVEUozeREx8LO', '545I3TEJyeF0y5U', 'Fnm1zDwa9FjSdWO', 'EkMqPIrqUcp0sP9',
                          'piPrAElSirgtFZN', 'ly1R0fD50QJhPLh', 'JFqZBNSwZVDye8V', '91QLKdEsqjUMD3J', 'XVBR5rErZ4QAuzK',
                          'xLlrH6CayMzy5hQ', 'p1vZGBk3h6eiV0j'
                          ]
        #from_inverters = ['u7ZUCz0saytnzDr','6vjOHZhuoMOfFW6','8pxnq4nNlzTsZsv','zijXxKVrjO7CYFj','XQpLG7rHeIsyVNT','NhEfN9yH8pcr89B']
        to_inverters = ['NegDweSBKY6sjrj', 'ZBhJ4bnmCN7Sp8k', 'TE0v1bFDaTJAVzd', 'dBpxR9RAAzSdyAB', 'LFqcLLMOvUdYoEz',
                        'i8cKitYQPWThroF',
                        # ge demo data copy
                        'mjuVj5H19OVT8U1', 'o5QfaEVhdk0ttBc', '9VtMoX7lwkJx7e9', 'MkGNlEAepCCM47d',
                        '1x7vOKerdtA1iZ5', 'I0LK3Wg0elwirop', 'GuFNLPj8RIPbdZj', 'vhBRJ9dTl3F9SQ0', 'XJzZ3Bnhcw76xxu',
                        'ifDNJ29Artc4RMr', 'UtIvEcC3gWjfQdF',

                        # # edp demo data copy
                        'bNwyi2TrZQ13QZU', 'YQehxQuLeOWsvrP', 'CaUudWtJZV1OsbZ', 'rvtbokJIX3mDaYq', '6As8F9pLYmh12Y5',
                        '4pac4qAXxERG7co', 'xKWRn6i6Rt5OasA', 'gNl4hO1xWaVpDOi', 'lLK99fY31iP861Q', 'nLOJ8AfKOguvKXb',
                        '8Izm2nb4wDm3tAw', 'lSlKkwdUDNyqCp8', 'CIhfqOBza2pGkEx', 'SabvRNR6EJhVMhj', 'XTd9ygBsgJQTb0a',
                        'a4yffWsFhlpb7Nc', 'MjDNI5rcrYJwFOu', 'WTh6h87ZkwJ2Z58', 'McNfIudimN3ph6W', 'n3aHVWFjWzWKe0P',
                        '7JexjFuQjprglh7', 'AivFyLHnD8OY9sr', 'ReaycmojFb55241', 'QiZhJBdRcK5Gfof', 'YNJahJUBwffyIG9',
                        'WJmgp9yXA3g38qS', 'kwlBNCeohFZSbso', 'FUnbZKY8fljRIQB', 'THoOe7l3vZmA9S6', '40xtMCWwTzsmItS',
                        'XhE1L60ClOqGpaq', 'Lb1WtwjejnHbbWP', 'Xyux6TNe3fPfLis', '3OlArRJu4I2lvZB', 'ygw8IrJsjvbPHKC',

                        # ausnet data copy
                        u'1htYwERmyZjKKe9', u'loGjV5yRLpKij7t', u'feP445BblU6Oyfm', u'JAZLamFimo6pB5c',
                        u'TdDljY4OAN97mkV', u'Y33vSjUG1D7WEIG', u'78ONlZ8R0HXcOYG', u'GUjP3n0DZeX80GN',
                        u'5znhPTQ9gxjX1Gb', u'KHdubcZ4S7rMuUi', u'3rawQVSlWKLV9if', u'mRROs8oX0vRgBQP',
                        u'YrsilxM4NgG4Rg5', u'4JhF8KldhfChHvg', u'a0Jy4CAAIZJ1s15', u'2y4Qq2I24m6FEqM',
                        u'joRJaLMelXiNK8N', u'U1QvqoI5fMDSD4p', u'VrTyVLdClUxSHB0', u'02OxLfGloXdphq2',
                        u'1l0MeaeoaxO8tDE', u'KusV2KfLaMUMnVh'
                        ]
        #to_inverters = ['NegDweSBKY6sjrj','ZBhJ4bnmCN7Sp8k','TE0v1bFDaTJAVzd','dBpxR9RAAzSdyAB','LFqcLLMOvUdYoEz','i8cKitYQPWThroF']
        from_gateway = ['yaDpCBMtbXZ59ku', 'yaDpCBMtbXZ59ku',
                        # edp demo data copy
                        '8tHE4Nad4IRWn41', 'qDv6ruB7MijiMTA', 'sKotQlITnZ2Fnud',
                        # ausnet data copy
                        'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA',
                        'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA',
                        'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA', 'qDv6ruB7MijiMTA']

        #from_gateway = 'yaDpCBMtbXZ59ku'
        to_gateway = ['0vzy9TKkaakM3Ah', 'vqRYzmPbBeQDY8N',
                      # edp demo data copy
                      '1PwK1Niyn8Tjzda', 'HP13hmLLvWmbsNr', '77AY9sH8Pq3nKID',
                      # ausnet data copy
                      u'HbuK0bpa6n5qd6f', u'PDOIJgye8ZzRZIi', u'FJCanno9KqbQDqN', u'mbZK9hZpxXR2mQo',
                      u'smmTUmQUWRdr3rw', u'RdbSN0aDDCFlFka', u'wpVLN4GP1SHF9NQ', u'e2EflHfBWldiyW4',
                      u'4g4THRcIg3ahmZo', u'xMdgr8Kx9Rah4Z3', u'5vVELUm4id1kAD2']

        #to_gateway = '0vzy9TKkaakM3Ah'
        from_meta = ['B9542ObaG5e8XbN', 'B9542ObaG5e8XbN', 'M1i3Zy3xZ3wkvd6',
                     'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6',
                     'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6', 'M1i3Zy3xZ3wkvd6',
                     'M1i3Zy3xZ3wkvd6']

        #from_meta = 'B9542ObaG5e8XbN'
        to_meta = ['qbrQONXFaMysv2P', '8FpVnEveXYYWr0C', 'Gg9gKQUMEJdRfUf',
                   u'bqMvhFbOqknxiHH', u'MkcTlQoVqe0wThm', u'6tZrFvHh0MzL7hM', u'3rt67uxrn1i1szq', u'5PqgIHeAuqAQ3P4',
                   u'zRTuVW3R2X2gNeB', u'Xwu3vMKYqGKXdiZ', u'CdZ9Q4a42CuU5cx', u'm9Ysm3dRT5AcPUI', u'0J5QKCXX5pvaUDa',
                   u'fMT6YMbkCcdKmmv']
        #to_meta = 'qbrQONXFaMysv2P'

        aus_net_keys = [u'1htYwERmyZjKKe9', u'loGjV5yRLpKij7t', u'feP445BblU6Oyfm', u'JAZLamFimo6pB5c',
                        u'TdDljY4OAN97mkV', u'Y33vSjUG1D7WEIG', u'78ONlZ8R0HXcOYG', u'GUjP3n0DZeX80GN',
                        u'5znhPTQ9gxjX1Gb', u'KHdubcZ4S7rMuUi', u'3rawQVSlWKLV9if', u'mRROs8oX0vRgBQP',
                        u'YrsilxM4NgG4Rg5', u'4JhF8KldhfChHvg', u'a0Jy4CAAIZJ1s15', u'2y4Qq2I24m6FEqM',
                        u'joRJaLMelXiNK8N', u'U1QvqoI5fMDSD4p', u'VrTyVLdClUxSHB0', u'02OxLfGloXdphq2',
                        u'1l0MeaeoaxO8tDE', u'KusV2KfLaMUMnVh', u'HbuK0bpa6n5qd6f', u'PDOIJgye8ZzRZIi',
                        u'FJCanno9KqbQDqN', u'mbZK9hZpxXR2mQo', u'smmTUmQUWRdr3rw', u'RdbSN0aDDCFlFka',
                        u'wpVLN4GP1SHF9NQ', u'e2EflHfBWldiyW4', u'4g4THRcIg3ahmZo', u'xMdgr8Kx9Rah4Z3',
                        u'5vVELUm4id1kAD2', u'bqMvhFbOqknxiHH', u'MkcTlQoVqe0wThm', u'6tZrFvHh0MzL7hM',
                        u'3rt67uxrn1i1szq', u'5PqgIHeAuqAQ3P4', u'zRTuVW3R2X2gNeB', u'Xwu3vMKYqGKXdiZ',
                        u'CdZ9Q4a42CuU5cx', u'm9Ysm3dRT5AcPUI', u'0J5QKCXX5pvaUDa', u'fMT6YMbkCcdKmmv'
                        ]
        # copy Gateway data
        for i in range(len(from_gateway)):
            from_gateway_source = GatewaySource.objects.get(sourceKey=from_gateway[i])
            to_gateway_source = GatewaySource.objects.get(sourceKey=to_gateway[i])

            print "Copying from %s to %s" % (from_gateway_source.name, to_gateway_source.name)
            if to_gateway_source.sourceKey in aus_net_keys:
                h_delta = 4
            else:
                h_delta = 0

            for field in from_gateway_source.fields.all():
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_gateway_source.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                # print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_gateway_source.user.id, to_gateway_source.sourceKey,
                                           to_gateway_source.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_gateway_source.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            raw_value=record.raw_value,
                                                            timestamp_in_data=record.timestamp_in_data - timedelta(hours=h_delta))

        # copy Inverters data
        for i in range(len(from_inverters)):
            from_inverter = IndependentInverter.objects.get(sourceKey=from_inverters[i])
            to_inverter = IndependentInverter.objects.get(sourceKey=to_inverters[i])

            print "Copying from %s to %s" % (from_inverter.name, to_inverter.name)

            if to_inverter.sourceKey in aus_net_keys:
                h_delta = 4
            else:
                h_delta = 0


            for field in from_inverter.fields.filter(name__in=['SOLAR_STATUS', 'ACTIVE_POWER', 'DC_POWER', 'MPPT1_DC_VOLTAGE', 'MPPT1_DC_CURRENT', 'MPPT1_DC_POWER', 'MPPT2_DC_VOLTAGE', 'MPPT2_DC_CURRENT', 'MPPT2_DC_POWER', 'DAILY_YIELD', 'TOTAL_OPERATIONAL_HOURS', 'TOTAL_YIELD', 'HEAT_SINK_TEMPERATURE']):
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_inverter.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                # print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_inverter.user.id, to_inverter.sourceKey,
                                       	   to_inverter.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_inverter.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            raw_value=record.raw_value,
                                                            timestamp_in_data=record.timestamp_in_data - timedelta(hours=h_delta))
            # copy alarm for edpdemo plant
            if to_inverter.plant.slug == 'edpdemo' or to_inverter.plant.slug == "ausnetdemosite":
                for field in from_inverter.errorfields.all():
                    data_records = ErrorStorageByStream.objects.filter(source_key=from_inverter.sourceKey,
                                                                           stream_name=field.name,
                                                                           timestamp_in_data__gte=from_time,
                                                                           timestamp_in_data__lte=until_time)
                    # print len(data_records)
                    for record in data_records:
                        ErrorStorageByStream.objects.create(source_key=to_inverter.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            timestamp_in_data=record.timestamp_in_data - timedelta(hours=h_delta))
        # copy plant meta source data
        for i in range(len(from_meta)):
            from_meta_source = PlantMetaSource.objects.get(sourceKey=from_meta[i])
            to_meta_source = PlantMetaSource.objects.get(sourceKey=to_meta[i])

            print "Copying from %s to %s" % (from_meta_source.name, to_meta_source.name)

            if to_meta_source.sourceKey in aus_net_keys:
                h_delta = 4
            else:
                h_delta = 0

            for field in from_meta_source.fields.all():
                data_records = ValidDataStorageByStream.objects.filter(source_key=from_meta_source.sourceKey,
                                                                       stream_name=field.name,
                                                                       timestamp_in_data__gte=from_time,
                                                                       timestamp_in_data__lte=until_time)
                # print len(data_records)
                for record in data_records:
                    write_a_data_write_ttl(to_meta_source.user.id, to_meta_source.sourceKey,
                                           to_meta_source.timeoutInterval,
                                           True, until_time)
                    ValidDataStorageByStream.objects.create(source_key=to_meta_source.sourceKey,
                                                            stream_name=field.name,
                                                            stream_value=record.stream_value,
                                                            raw_value=record.raw_value,
                                                            timestamp_in_data=record.timestamp_in_data - timedelta(hours=h_delta))
        print("alpine data copy cronjob completed!")
    except Exception as exception:
        print(str(exception))