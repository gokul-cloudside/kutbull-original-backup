import requests
import json
import time
from solarrms.models import SolarPlant, PVWatt

month_dict = {0:'JAN', 1: 'FRB', 2: 'MAR', 3: 'APR', 4: 'MAY', 5: 'JUN', 6: 'JUL', 7: 'AUG', 8: 'SEP', 9: 'OCT', 10: 'NOV', 11: 'DEC'}
DATASET_URL = "https://developer.nrel.gov/api/solar/data_query/v1.json?api_key=Krt7kGYeuGZjq5U0KS1v0PHFDierDs4OFVdT2MCg&lat=%s&lon=%s&radius=100"
PVWATT_DATA = "https://developer.nrel.gov/api/pvwatts/v5.json?api_key=Krt7kGYeuGZjq5U0KS1v0PHFDierDs4OFVdT2MCg&lat=%s&lon=%s&system_capacity=%s&azimuth=180&tilt=40&array_type=1&module_type=1&losses=10&dataset=%s"


def get_pvwatt_data():
    splants = SolarPlant.objects.all()
    pvwatt_instance = []
    for plant in splants:
        try:
            distance = 0
            dataset = None
            response = requests.get(DATASET_URL % (plant.latitude, plant.longitude))
            response_output = json.loads(response.content)
            if not "outputs" in response_output:
                continue
            response_output = response_output.get('outputs', None)
            for n_key in response_output:
                if response_output['%s' % n_key]:
                    if distance == 0 or distance >= response_output['%s' % n_key]['distance']:
                        distance = response_output['%s' % n_key]['distance'];
                        dataset = n_key
            print plant.slug, distance, dataset
            response_data = requests.get(PVWATT_DATA % (plant.latitude, plant.longitude, plant.capacity, dataset))
            response_data_output = json.loads(response_data.content)
            if not "outputs" in response_data_output:
                continue
            response_data_output = response_data_output.get('outputs', None)
            ac_annual = response_data_output.pop('ac_annual')
            solrad_annual = response_data_output.pop('solrad_annual')
            capacity_factor = response_data_output.pop('capacity_factor')
            pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='AC_ANNUAL',
                                        time_period_type='YEAR', time_period_year_number=2018,
                                        parameter_value=ac_annual))
            pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='SOLRAD_ANNUAL',
                                        time_period_type='YEAR', time_period_year_number=2018,
                                        parameter_value=solrad_annual))
            pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='CAPACITY_FACTOR',
                                        time_period_type='YEAR', time_period_year_number=2018,
                                        parameter_value=capacity_factor))
            dc_monthly = response_data_output.pop('dc_monthly', [])
            ac_monthly = response_data_output.pop('ac_monthly', [])
            solrad_monthly = response_data_output.pop('solrad_monthly', [])
            poa_monthly = response_data_output.pop('poa_monthly', [])
            for i in month_dict:
                pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='DC_MONTHLY',
                                            time_period_year_number=2018,
                                            time_period_type='MONTH', time_period_month_number=int(i)+1,
                                            parameter_value=dc_monthly[i]))
                pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='AC_MONTHLY',
                                            time_period_year_number=2018,
                                            time_period_type='MONTH', time_period_month_number=int(i)+1,
                                            parameter_value=ac_monthly[i]))
                pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='SOLRAD_MONTHLY',
                                            time_period_year_number=2018,
                                            time_period_type='MONTH', time_period_month_number=int(i)+1,
                                            parameter_value=solrad_monthly[i]))
                pvwatt_instance.append(PVWatt(plant_id=plant.id, parameter_name='POA_MONTHLY',
                                            time_period_year_number=2018,
                                            time_period_type='MONTH', time_period_month_number=int(i)+1,
                                            parameter_value=poa_monthly[i]))
        except Exception as e:
            print("Some exception for plant ",plant.slug,"--->",e)

    return pvwatt_instance

if __name__ == '__main__':
    #pvwatt_instance = get_pvwatt_data()
    #print pvwatt_instance
    #PVWatt.objects.bulk_create(pvwatt_instance)
    pass


"""
LOG ENTRY OF RUN

aurobindo 4422 IN
immigrationbuilding 1739 IN
shivamautotech 6773 IN
rafcoimbatore 2804 IN
2500kwniftem 3532 IN
2500kwniftemplant2 3532 IN
aaykarbhawan 3062 IN
acecrane 5315 IN
adminblockbbmb 3384 IN
airportmetrodepot 2251 IN
airportroad 4310 IN
ait 3242 IN
ait82kw 7405 IN
akshardham 3358 IN
alembicpharmaformation2 7551 IN
alembicpharmaformation3 7556 IN
aleordermaceuticalsltd 7556 IN
palladam 6204 IN
andheri 4310 IN
aparri 0 None
('Some exception for plant ', u'aparri', '--->', KeyError('ac_annual',))
thuraiyur 5309 IN
asalpha 4310 IN
aspengreen70 3622 IN
pavagada 6026 IN
avoncyclesltd 5348 IN
avonispat 5355 IN
avonispat2 5355 IN
azadnagar 4310 IN
badarpur 7388 IN
baguio 0 None
('Some exception for plant ', u'baguio', '--->', KeyError('ac_annual',))
bajajmotors 5019 IN
balajiirrigation 3866 IN
balancer 4456 IN
baler 0 None
('Some exception for plant ', u'baler', '--->', KeyError('ac_annual',))
ballupur 1450 IN
bangalore 5626 IN
bareillycitynerrailway 5577 IN
barmalt 981 IN
basco 0 None
('Some exception for plant ', u'basco', '--->', KeyError('ac_annual',))
batterydemo 5626 IN
bhu 4234 IN
bslcityoffice125kw 2836 IN
bsllimited 2747 IN
bslweaving180kw 6517 IN
btcpusa110kw 2419 IN
businessschoolatshivnadaruniversity 4528 IN
butuan 0 None
('Some exception for plant ', u'butuan', '--->', KeyError('ac_annual',))
castelo 53935 intl
catarman 0 None
('Some exception for plant ', u'catarman', '--->', KeyError('ac_annual',))
ccrtdwarka 4251 IN
cedarcrest189 3613 IN
centralcustom 6534 IN
centralexcise 3611 IN
cfti 4152 IN
gcgocomplex 5535 IN
cgocomplex 5306 IN
hacgocomplex 1840 IN
chakala 4310 IN
cidc 5535 IN
cisco2 5626 IN
computerblockbbmb 3366 IN
cotabato 0 None
('Some exception for plant ', u'cotabato', '--->', KeyError('ac_annual',))
councilhouse 2210 IN
csuppal 7536 IN
csspl 3972 IN
cuh 5535 IN
customhouse 6931 IN
cuyo 0 None
('Some exception for plant ', u'cuyo', '--->', KeyError('ac_annual',))
dact 0 None
('Some exception for plant ', u'dact', '--->', KeyError('ac_annual',))
dataglendemo 7490 IN
davao 0 None
('Some exception for plant ', u'davao', '--->', KeyError('ac_annual',))
deendayalupadhyaycollege 7405 IN
deifdemo 5626 IN
delhi 6884 IN
delhihaat 3318 IN
demo1 5626 IN
demo100 6534 IN
demo101 6534 IN
demo102 7146 IN
demo103 6534 IN
demo104 6534 IN
demo105 6534 IN
demochemtrols 5626 IN
demoh 4042 IN
demok 7454 IN
demo 4684 IN
derasachasauda 3620 IN
devyaniinternationallimited 6608 IN
dgcis 6227 IN
dhanalaxmiexports 4271 IN
dimplecreations 4329 IN
diplolog 0 None
('Some exception for plant ', u'diplolog', '--->', KeyError('ac_annual',))
dlfbksm 5135 IN
dlfsarojninagar 5268 IN
dmrcanandvihar115kwp 4420 IN
dmrcmetroenclave50kwp 7388 IN
mohanestate 7405 IN
dmrcpragatimaidan85kwp 7388 IN
dnnagar 4310 IN
dominicus 2027 IN
donbosco 6884 IN
dtu 3160 IN
dumaguete 0 None
('Some exception for plant ', u'dumaguete', '--->', KeyError('ac_annual',))
escape60 4529 IN
eastman 5492 IN
ecopark 7388 IN
electronicsniketan 5535 IN
elfitsolar 138508 intl
enovamdemo 8224 intl
evps 3033 IN
ezcc 4541 IN
faro 4154 intl
filtrationcapacity1510mgd2mwwaterworks 3366 IN
filtrationcapacity5151510mgd2mwwaterworks 3366 IN
foodcourt100kmyew 4201 IN
foodcourt107kmyew 562 IN
foodsandinnlimited 0 None
('Some exception for plant ', u'foodsandinnlimited', '--->', KeyError('ac_annual',))
fragnelschool 5260 IN
fsi100kwp 4437 IN
gadegaon 1133 IN
gdspsrajindernagar 3415 IN
ghatkopar 4310 IN
gisochurchlane 2259 IN
gjustuniversity 2949 IN
gmhs 1588 IN
gmhssec45c 1588 IN
gmhs1 1588 IN
gmhs2 1588 IN
gmr 4893 IN
goiformstoretemplestreet 1607 IN
goipresssantragachi 6113 IN
governmentofindiapress180kwp 6139 IN
governmentofindiapress30kwp 5982 IN
govindpuri 2211 IN
gpcl 6656 IN
growels 5082 IN
grps 4337 IN
gsi 1005 IN
gsi2 3490 IN
gsinagpur 4405 IN
gsss 1588 IN
guinan 0 None
('Some exception for plant ', u'guinan', '--->', KeyError('ac_annual',))
gupl 2654 IN
hartektower 5904 IN
helvoetrubberandplasticgse 6034 IN
herocylceltd 6812 IN
herodemo 7490 IN
heromotorcorp 4888 IN
hinatuan 0 None
('Some exception for plant ', u'hinatuan', '--->', KeyError('ac_annual',))
hindware100 1450 IN
hindware204 1450 IN
hirschvogelcomponents 4832 IN
hitechgearsltd 5611 IN
hmchalol 2759 IN
hmch 2613 IN
hyderabad 3005 IN
hyderabadhouse 5663 IN
ibmindirabhawan 5074 IN
ibmpilot 4876 IN
ieccollegegreaternoida 5408 IN
iffcoclub 3481 IN
igdtuw 2408 IN
igncajnapath 4910 IN
ihbas 5468 IN
iicpt 5739 IN
na 2892 IN
iisr 5855 IN
iiwbrkarnal 6675 IN
iloilo 0 None
('Some exception for plant ', u'iloilo', '--->', KeyError('ac_annual',))
incahammockmedavakkam 6021 IN
incahammockvandalur 3681 IN
infanta 0 None
('Some exception for plant ', u'infanta', '--->', KeyError('ac_annual',))
institutefortheblinds 1588 IN
ioclrndcentre 4389 IN
ioclrndfaridabad 5535 IN
ipbhawan 2639 IN
shivnadaruniversity 3854 IN
iticvraman 6884 IN
itijaffarpur 5312 IN
itijailroad 2419 IN
itimangolpuri 4432 IN
itipusa 6884 IN
ivorysoap 7612 IN
jagrutinagar 4310 IN
jaivinsacademy 7454 IN
jeevanjoty 5663 IN
jindalworldwideltd 3873 IN
jnarddc 5974 IN
jnpt 2863 IN
jppllalitpur 5615 IN
jppl1 4456 IN
jppl2 4456 IN
jsaibawalphasei 6684 IN
jsaibawalphaseii2 6684 IN
jsaibawalphaseiii 6684 IN
jsecsite1 2439 IN
jsecsite2 2439 IN
kvschoolspgdwaraka 5026 IN
kabirfoods1 4244 IN
kabirfoods2 4244 IN
kaleeswarar 2257 nsrdb
kalindicillege 1904 IN
mondipalayam 4684 IN
kbilphase2 5874 IN
khaitanpublicschool 3460 IN
kitpitampura 5538 IN
kmrlaluvametrostation 4103 IN
kmrlambattukavumetrostation2 7823 IN
kmrlchangampuzametrostation 7209 IN
kmrlcompanypadymetrostation 7821 IN
kmrlcusatmetrostation 4862 IN
kmrledapallymetrostation 7832 nsrdb
kmrlibldepo 3205 IN
kmrlkalamessarymetrostation 6970 IN
kmrlkaloormetrostation 6899 nsrdb
kmrlmgroadmetrostation 5692 nsrdb
kmrlmuttommetrostation 7823 IN
kmrlpalarivattommetrostation 6984 IN
kmrlpathadipalammetrostation 5174 IN
kmrlpulinchodumetrostation 4608 IN
kmrlworkshopdepo 2916 IN
kmrloccdcc 3283 IN
koyobearingindiapvtltd 5152 IN
krishibhavanrajpath200kwp 5087 IN
ksrcollege 2700 IN
kudal 4674 IN
laguindingan 0 None
('Some exception for plant ', u'laguindingan', '--->', KeyError('ac_annual',))
laxmidevidayalcharitablehospital 7443 IN
ldddh 1819 IN
lohia 5016 IN
loknayakbhawan90kwp 6263 IN
lovelyres 4454 IN
m2kcorporatepark 2419 IN
mactan 0 None
('Some exception for plant ', u'mactan', '--->', KeyError('ac_annual',))
magarpatta 4554 IN
magneti 3149 IN
maharashtrasadan150kwp 5311 IN
malaybalay 0 None
('Some exception for plant ', u'malaybalay', '--->', KeyError('ac_annual',))
mandakiniamin 4154 IN
maprofoodspvtltd 1554 IN
marolnaka 4310 IN
masbate 0 None
('Some exception for plant ', u'masbate', '--->', KeyError('ac_annual',))
matamansadevicampus 4546 IN
maulanaazadmedicalcollege 2955 IN
mdhouse 6884 IN
mdu 4477 IN
meerabaiinstituteoftechnology 1478 IN
meswaterworks2 3366 IN
mmum 5168 IN
molugan 0 None
('Some exception for plant ', u'molugan', '--->', KeyError('ac_annual',))
msjs 3149 IN
msl 4876 IN
msldrive3 6284 IN
msldriveline2 6242 IN
msldriveline4 6394 IN
mtnl80kwp 1982 IN
mumbaimetro 2985 IN
nacen200kwp 5535 IN
nappino100kw 5355 IN
nappino50kw 5355 IN
nariniketan 3366 IN
ncdccollege 3929 IN
neelamchowk 6447 IN
nehrumemorialmuseumlibrarynmml 7095 IN
neokraftglobalpvtltd 2729 IN
newchairmanofficebbmb 3366 IN
nirmanbhawan200kwp 5231 IN
nisarg 4888 IN
nitratechnicalcampus 2156 IN
nizampalace 1005 IN
nsbuilding 2706 IN
nsit 4753 IN
nursehostel 4075 IN
obchb 1588 IN
octg860kwmsl 3824 IN
olachargingstation 2454 IN
oldchairmanoffice 3366 IN
oldfaridabad 6781 IN
oldjnuclubbuilding 5663 IN
oldjnulibraryandclubbuilding 5663 IN
omya 4800 IN
opdsafdarjung 4437 nsrdb
ordinancefactory 4405 IN
orientfashiona14 4329 IN
orientfashionb4 4329 IN
orientfashionc17 4329 IN
ofuv 6884 IN
paramounte16 3556 IN
paramounte3 3557 IN
parishirwal 7654 IN
pinnacle 2526 IN
pioneerspinnermill 4969 nsrdb
piramalglassjambusar 4818 IN
piramalglasssolarkosamba 1205 IN
pitacademicblock100kw 5928 IN
pitprintingblock 6884 IN
platina 2857 IN
playsolar2 3848 IN
ponnitapes 4387 IN
pratyakshkarbhawan 3471 IN
powertransmissioncorporationofuttarakhandltd 6076 IN
ptcprincesa 0 None
('Some exception for plant ', u'ptcprincesa', '--->', KeyError('ac_annual',))
pumphouse122mwwaterworks 3366 IN
quezon 0 None
('Some exception for plant ', u'quezon', '--->', KeyError('ac_annual',))
rrkabel 5683 IN
radnik 6884 IN
raheja 4236 IN
rajahmundry 6443 IN
rajajibhawan 5297 IN
rajasthanvidyarthigriha 3992 IN
rajghat 1040 IN
ramnikuppal 5663 IN
rbl 1849 nsrdb
ranetrw 1849 nsrdb
ranergy 5607 nsrdb
raoresidency 5626 IN
rashtrapatibhawanauditorium 5663 IN
rashtrapatibhawangarage 5663 IN
reddysolar 5626 IN
reservationhall 3882 IN
rgniyd 3566 IN
rie 1588 IN
rmlhospital 4741 IN
rockman 6522 IN
rdil 4749 IN
rokas 0 None
('Some exception for plant ', u'rokas', '--->', KeyError('ac_annual',))
rsv 7755 IN
rsvp 7755 IN
rswm 4312 IN
rswmmandpam 4312 IN
sainagarapartments 1198 IN
sakinaka 4310 IN
sanjose 0 None
('Some exception for plant ', u'sanjose', '--->', KeyError('ac_annual',))
sandharbawal 5317 IN
sanjeevverma 3001 IN
santarem 72101 intl
sardarpatelbhawan 5663 IN
satyawaticollege 3853 IN
sawantwadi 4377 IN
seniorcitizenhome 1588 IN
sch 1588 IN
uran 3749 IN
seia 64702 intl
shastribhawan250kwp 2958 IN
shiningsunpower 7687 IN
shramsaktibhawan 5663 IN
sjmitchitradurga 4375 IN
skccpvtltd 3982 IN
skillprecision 7554 IN
slsdav 3974 IN
april4 7448 IN
solarappsdemo 5626 IN
solarpump 3902 IN
sonablw 2579 IN
srpvtltd 4405 IN
sripowerthinfilm 4311 IN
sripowercrystalline 4311 IN
sricity 3915 IN
sscbs 3239 IN
stbaptist 4270 nsrdb
substation122mwwaterworks 3366 IN
sueic 0 None
('Some exception for plant ', u'sueic', '--->', KeyError('ac_annual',))
thunganivillage 5465 IN
superfashion 5535 IN
supremecourt 5663 IN
surigao 0 None
('Some exception for plant ', u'surigao', '--->', KeyError('ac_annual',))
swamivivekananthaillam 3474 IN
swelecthhvsolar 2246 IN
asun 1617 IN
tampakan 0 None
('Some exception for plant ', u'tampakan', '--->', KeyError('ac_annual',))
tankno1cap1mgtankno1cap2mgmcphlab2mwwaterworks 3366 IN
tankno232mwwaterworks 3366 IN
tankno452mwwaterworks 3366 IN
tarapur 4350 IN
test1 7448 IN
test2 7448 IN
test604 3322 nsrdb
testplant1 2853 IN
testsunpure 5626 IN
thefoodstreetmathura 5440 IN
thegreenenvironmentservicescoopsocltd 1294 IN
thehitechgearsltd400kw 3881 IN
theatest 2853 IN
tata 2989 IN
tpsslengglab 1881 IN
tscsl 1588 IN
airportdepot2 7388 IN
tuguegarao 0 None
('Some exception for plant ', u'tuguegarao', '--->', KeyError('ac_annual',))
ultratechcementlimited 7654 IN
udyogbhavan208kwp 5663 IN
ultimatesunsystemspvtltd 445 IN
ultratechcementlimitedjhajjar 7654 IN
unani 2823 IN
unipatch 5626 IN
unisun 4925 IN
upsc100kwp 2255 IN
vedasrigreenenergyprivatelimited 6243 IN
versova 4310 IN
vidyutbhawan 5891 IN
vigyanbhawan 5372 IN
virac 0 None
('Some exception for plant ', u'virac', '--->', KeyError('ac_annual',))
vjti 5061 nsrdb
vtcashakiran 1588 IN
waaneep 4042 IN
waareedemo 5082 IN
walmartamravati 3163 IN
walmartaurangabad 2890 IN
weh 4310 IN
wrmandherinewstationbuilding 3358 IN
wrmbandraterminalmainbuilding 1802 IN
wrmdadarprsbuilding 3505 IN
wrmglobuilding 2882 IN
wrmgrantroad 3897 IN
wrmlowerparel 5320 IN
wrmmahimstation 1046 IN
wrmrammandir 132 IN
wrmsantacruzstation 3485 IN
wrrdrmoffice 1819 IN
wrrhospital 634 IN
wrrrailwayhighschoolbuilding 1012 IN
wrrujjainrailwaystation 4435 IN
yerangiligi 1258 IN
ykk1factory 7193 IN
ykk2factory 7193 IN
ysc400kwp 3678 IN
ytut 7432 IN
zamecanga 0 None
('Some exception for plant ', u'zamecanga', '--->', KeyError('ac_annual',))

"""