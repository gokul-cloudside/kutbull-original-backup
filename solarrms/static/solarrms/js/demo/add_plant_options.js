$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Add Plants Details</a></li>')

    $(function () {
      $('[data-toggle="tooltip"]').tooltip()
    })

});

var webdyn_id_data;
var device_io_number = 0;

// FORM WIZARD WITH VALIDATION
// =================================================================
$('#all_details').bootstrapWizard({
    tabClass            : 'wz-steps',
    nextSelector        : '.next',
    previousSelector    : '.previous',
    onTabClick          : function(tab, navigation, index) {
        return false;
    },
    onInit : function(){
        $('#all_details').find('.finish').hide().prop('disabled', true);
    },
    onTabShow: function(tab, navigation, index) {
        var $total = navigation.find('li').length;
        var $current = index+1;
        var $percent = ($current/$total) * 100;
        var wdt = 100/$total;
        var lft = wdt*index;

        $('#all_details').find('.progress-bar').css({width:wdt+'%',left:lft+"%", 'position':'relative', 'transition':'all .5s'});

        // If it's the last tab then hide the last button and show the finish instead
        if($current >= $total) {
            $('#all_details').find('.next').hide();
            $('#all_details').find('.finish').show();
            $('#all_details').find('.finish').prop('disabled', false);
        } else {
            $('#all_details').find('.next').show();
            $('#all_details').find('.finish').hide().prop('disabled', true);
        }
    },
    onNext: function(tab, navigation, index){

        $('#create_plant').bootstrapValidator('validate');

        if (index == 4){
            // validate the step first
            isValid = null;
            $('#create_plant').bootstrapValidator('validate');
            if(isValid === false)return false;
            var template = $('#roof_1').clone();
            // prepare content for the second step
            var number_of_groups = $("#roof_or_inverter_groups").val();
            // iterate through new rows
            if(!isNaN(parseInt(number_of_groups))) {
                $('#new_roofs').empty();
                for(var group = 2; group <= number_of_groups; group++) {
                    var validator = $('#create_plant').data('bootstrapValidator');
                    var klon = template.clone();
                    klon.find('h3').each(function() {
                        $(this)[0].innerHTML = $(this)[0].innerHTML
                                                   .replace("Roof or Group 1", "Roof or Group " + group.toString())});
                    klon.attr('id', 'roof_' + group)
                        .appendTo($('#new_roofs'))
                        .find('input')
                        .each(function () {
                            $(this).removeData();
                            $(this).attr('id', $(this).attr('id').replace(/_(\d*)$/, "_"+group));
                            validator.addField($(this));
                        })
                }
            }
            return true;

        } else if (index == 1) {

            $("#previous_button").hide();

            isValid = null;
            $('#create_plant').bootstrapValidator('validate');
            if(isValid === false)return false;

            console.log("index 1");

            var webdyn_id = $("#webdyn_id_code").val();

            devices_details(webdyn_id);

        } else if(index == 2) {

            isValid = null;
            $('#create_plant').bootstrapValidator('validate');
            if(isValid === false)return false;

            console.log("index");

            $("#previous_button").show();

        } else if (index == 3) {
            isValid = null;
            $('#create_plant').bootstrapValidator('validate');
            if(isValid === false)return false;

            var templateInverter = $('#inverter_0').clone();
            var number_of_inverters = $('#total_number_of_inverters').val();
            var plant_name = $("#plant_name").val();
            var inverter_manufacturer = $("#inverter_make").val();

            if(!isNaN(parseInt(number_of_inverters))) {
                $("#idmodbusAddress_0").val(inverters_data.inverters[0].address);
                $("#idinverterManufacturer_0").val(inverters_data.inverters[0].manufacturer);

                $("#new_inverters").empty();
                for (var inverter = 1; inverter < inverters_data.inverters.length; inverter++) {
                    var validatorInverter = $('#create_plant').data('bootstrapValidator');
                    var klonInverter = templateInverter.clone();
                    klonInverter.find('h3').each(function() {
                        $(this)[0].innerHTML = $(this)[0].innerHTML.replace("Inverter 1", "Inverter " + (inverter+1).toString());
                    });

                    klonInverter.attr('id', 'inverter_' + inverter)
                        .appendTo($('#new_inverters'))
                        .find('input')
                        .each(function () {
                            $(this).removeData();
                            $(this).attr('id', $(this).attr('id').replace(/_(\d*)$/, "_" + inverter));
                            validatorInverter.addField($(this));
                    })

                    $("#idmodbusAddress_"+inverter).val(inverters_data.inverters[inverter].address);
                    $("#idinverterManufacturer_"+inverter).val(inverters_data.inverters[inverter].manufacturer);
                }
            }
            return true;

        } else {
            isValid = null;
            $('#create_plant').bootstrapValidator('validate');

            if(isValid === false)return false;
        }
    }
});

var isValid;
var option = {
    container: 'popover',
    message: 'This value is not valid',
    feedbackIcons: {
        valid: 'fa fa-check-circle fa-lg text-success',
        invalid: 'fa fa-times-circle fa-lg',
        validating: 'fa fa-refresh'
    },
    fields: {
        webdyn_id: {
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                },
                regexp: {
                    regexp: /^(WD00)[a-zA-Z0-9]{4}$/i,
                    message: 'The ID can only consist of alphabetical characters and spaces. It should be of 8 characters in a specific format.'
                }
            }
        },
        group_name: {
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                },
                regexp: {
                    regexp: /^[a-zA-Z0-9_ ]+$/,
                    message: 'The first name can only consist of alphabetical characters and spaces'
                }
            }
        },
        device_id: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            },
        },
        panel_number: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        length_panel_area: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        breadth_panel_area: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        tilt_angle: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        group_type: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        azimuth: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        }/*,
        inverterName : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        modelNumber : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        serialNumber : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        inverterGroup : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        inverterCapacity : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        number_of_MPPT : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        stringsMPPT : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        modulesString : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        dcCapacity : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        serialNumber : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        modbusAddress : {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        }*/
    }
};

$("#create_plant").bootstrapValidator(option)
    .on('success.field.bv', function(e, data) {
        // $(e.target)  --> The field element
        // data.bv      --> The BootstrapValidator instance
        // data.field   --> The field name
        // data.element --> The field element

        var $parent = data.element.parents('.form-group');

        // Remove the has-success class
        $parent.removeClass('has-success');


        // Hide the success icon
        //$parent.find('.form-control-feedback[data-bv-icon-for="' + data.field + '"]').hide();
    }).on('error.form.bv', function(e) {
        console.log("error");
        console.log(e);

        isValid = false;
    });

$('#dcCapacity').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#dcCapacity').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#weather_station_tilt_angle').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#weather_station_tilt_angle').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#total_number_of_inverters').keypress(function(eve) {
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
});

$('#inverter_rating').keypress(function(eve) {
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#inverter_rating').keyup(function(eve) {
        var number_of_inverters = $("#total_number_of_inverters").val();
        
        var inverter_rating = $(this).val();

        if(!isNaN(parseInt(number_of_inverters))) {
            for(var inverter = 1; inverter <= number_of_inverters; inverter++) {
                $("#rated_capacity"+inverter).empty();
                $("#rated_capacity"+inverter).val(inverter_rating);
            }
        }
    });
});

$('#inverter_make').on('change', function() {
    var number_of_inverters = $("#total_number_of_inverters").val();
    
    var inverter_manufacturer = $(this).val();

    if(!isNaN(parseInt(number_of_inverters))) {
        for(var inverter = 1; inverter <= number_of_inverters; inverter++) {
            $("#inverter_manufacturer"+inverter).empty();
            $("#inverter_manufacturer"+inverter).append(inverter_manufacturer);
        }
    }
});

$('#modules_per_string').keypress(function(eve) {
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#modules_per_string').keyup(function(eve) {
        var number_of_inverters = $("#total_number_of_inverters").val();
        
        var modules_per_string = $(this).val();

        if(!isNaN(parseInt(number_of_inverters))) {
            for(var inverter = 1; inverter <= number_of_inverters; inverter++) {
                $("#modules_per_string"+inverter).empty();
                $("#modules_per_string"+inverter).val(modules_per_string);
            }
        }
    });
});

$('#weather_station_tilt_angle').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#weather_station_tilt_angle').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

function devices_details(webdyn_id) {

    $("#device_id").val(webdyn_id);

    console.log("devices");

    /*var modbus_data = {
        "modbus": [
            {
                "manufacturer": "SECURE_ELITE_440_446",
                "default_def": true,
                "name": "Secure_Elite_440_446_1",
                "address": "12;001"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "1;002"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "3;004"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "5;006"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "11;012"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "10;011"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "7;008"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "2;003"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "4;005"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "8;009"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "9;010"
            },
            {
                "manufacturer": "DELTA",
                "default_def": true,
                "name": "Delta",
                "address": "6;007"
            }
        ],
        "inverters": []
    }*/

    $.ajax({
        type: "GET",
        url: "/api/v1/plant/ftpdata/?deviceid=".concat(webdyn_id),
        success: function(modbus_data) {

            if(typeof modbus_data == "string") {

                noty_message(modbus_data + "!", 'error', 8000)
                return;

            } else {

                webdyn_id_data = modbus_data;

                var single_inverter_present = 0;
                var inverter_present = 0;
                
                var templateModbus = $('#modbus_device_original').clone();

                $("#inverter_details").empty();

                if(modbus_data.inverters.length > 0) {

                    $("#inverter_details").empty();
                    $("#inverter_details").append('<h3 class="text-center">Inverter Details</h3>' +
                                                '<div class="row" id="inverter_devices_div"></div>');

                    $("#inverter_devices_div").empty();

                    for (var inverter = 0; inverter < modbus_data.inverters.length; inverter++) {
                        var validatorModbus = $('#create_plant').data('bootstrapValidator');
                        $("#inverter_devices_div").append('<div class="row"><div id="inverter_'+inverter+'"></div></div>');

                        $("#inverter_"+inverter).empty();
                        $("#inverter_"+inverter).append('<div class="mar-all col-lg-2 col-md-2 col-sm-2" id="inverter_modbus_address_div_' + inverter + '" style="margin-right: 2px;">' +
                                                            '<div class="form-group">' +
                                                                '<input type="text" class="form-control" id="inverter_modbus_address_' + inverter + '" name="inverter_modbus_address" placeholder="Inverter Modbus Address" required="required" readonly>' + 
                                                                '<i>(Pre-filled Modbus Address)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2 col-sm-2" id="inverter_manufacturer_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" class="form-control" id="inverter_manufacturer_' + inverter + '" name="inverter_manufacturer" placeholder="Field Template" required="required" readonly>' + 
                                                                '<i>(Pre-filled Inverter Manufacturer)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="single_inverter_name_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Inverter Name" type="text" class="form-control" id="single_inverter_' + inverter + '" name="single_inverter_name">' + 
                                                                '<i>(Type a inverter name)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_model_number_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Inverter Model Number" type="text" class="form-control" id="inverter_model_number_' + inverter + '" name="inverter_model_number">' + 
                                                                '<i>(Type inverter model number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_serial_number_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Inverter Serial Number" type="text" class="form-control" id="inverter_serial_number_' + inverter + '" name="inverter_serial_number">' + 
                                                                '<i>(Type inverter serial number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_dc_capacity_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="DC Capacity in kW" type="text" class="form-control" id="inverter_dc_capacity_' + inverter + '" name="inverter_dc_capacity" min="1">' + 
                                                                '<i>(Type dc capacity in kW)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="single_inverter_capacity_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Inverter Capacity in kW" type="text" class="form-control" id="single_inverter_capacity_' + inverter + '" name="single_inverter_capacity" min="1">' + 
                                                                '<i>(Type inverters capacity in kW)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_number_of_mppts_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Number Of MPPTs" type="text" class="form-control" id="inverter_number_of_MPPT_' + inverter + '" name="inverter_number_of_MPPT" min="1">' + 
                                                                '<i>(Type a number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_strings_per_mppt_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Strings per MPPT" type="text" class="form-control" id="inverter_string_per_mppt_' + inverter + '" name="inverter_string_per_mppt" min="1">' + 
                                                                '<i>(Type string mppt)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_modules_per_string_div_' + inverter + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Modules per String" type="text" class="form-control" id="inverter_modules_per_string_' + inverter + '" name="inverter_modules_per_string">' + 
                                                                '<i>(Type module strings)</i>' + 
                                                            '</div>' + 
                                                        '</div>');
                        
                        $("#inverter_modbus_address_"+inverter).val(modbus_data.inverters[inverter].name);
                        $("#inverter_manufacturer_"+inverter).val(modbus_data.inverters[inverter].manufacturer);

                        $("#inverter_"+inverter).attr('id', 'inverter_' + inverter)
                            .find('input')
                            .each(function () {
                                validatorModbus.addField($(this)[0].name);
                        })

                        single_inverter_present = 1;

                    }

                    if(single_inverter_present == 1) {
                                    
                        var field_option = ["single_inverter_name", "inverter_model_number", "inverter_serial_number", "inverter_dc_capacity", "single_inverter_capacity", "inverter_number_of_MPPT", "inverter_string_per_mppt", "inverter_modules_per_string", "inverter_modbus_address", "inverter_manufacturer"];

                        for(var field = 0; field < field_option.length; field++) {
                            option.fields[field_option[field]] = {
                                message: 'The value is not valid',
                                validators: {
                                    notEmpty: {
                                        message: 'The value is required.'
                                    }
                                }
                            }
                        }

                        $('#create_plant').bootstrapValidator('revalidateField', field_option[0]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[1]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[2]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[3]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[4]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[5]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[6]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[7]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[8]);
                        $('#create_plant').bootstrapValidator('revalidateField', field_option[9]);
                    }

                }

                if(modbus_data.modbus.length > 0) {

                    $("#modbus_details").empty();
                    $("#modbus_details").append('<h3 class="text-center">Modbus Details</h3>' +
                                                '<div class="row" id="modbus_device_original"></div>');

                    $("#modbus_device_original").empty();

                    for (var modbus = 0; modbus < modbus_data.modbus.length; modbus++) {
                        var validatorModbus = $('#create_plant').data('bootstrapValidator');
                        $("#modbus_device_original").append('<div class="row"><div id="modbus_device_'+modbus+'"></div></div>');

                        $("#modbus_device_"+modbus).empty();
                        $("#modbus_device_"+modbus).append('<div class="mar-all col-lg-2 col-md-2 col-sm-2" id="modbus_address_div_' + modbus + '" style="margin-right: 2px;">' +
                                                            '<div class="form-group">' +
                                                                '<input type="text" class="form-control" id="modbus_address_' + modbus + '" name="modbus_address" placeholder="Modbus Address" required="required" readonly>' + 
                                                                '<i>(Pre-filled Modbus Address)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2 col-sm-2" id="manufacturer_div_' + modbus + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" class="form-control" id="manufacturer_' + modbus + '" name="manufacturer" placeholder="Field Template" required="required" readonly>' + 
                                                                '<i>(Pre-filled Device Manufacturer)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2 col-sm-2" style="margin-bottom: 0px;margin-right: 0px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<select class="form-control" id="modbus_device_select_' + modbus + '" name="modbus_device" modbus="' + modbus + '">' + 
                                                                    '<option value="" disabled selected> --Select Device-- </option>' + 
                                                                    '<option value="inverter">Inverter</option>' + 
                                                                    '<option value="energy_meter">Energy Meter</option>' + 
                                                                    '<option value="scb">SCB</option>' + 
                                                                '</select>' + 
                                                                '<i>(Select a Device)</i>' + 
                                                            '</div>' + 
                                                        '</div>');

                        $("#modbus_device_select_"+modbus).on('change', function() {

                            var modbus_device_count = $(this).attr('modbus');

                            var modbus_device_selected = $("#modbus_device_select_"+modbus_device_count).val();

                            if(modbus_device_selected == "inverter") {
                                $("#inverters_name_div_"+modbus_device_count).remove();
                                $("#model_number_div_"+modbus_device_count).remove();
                                $("#serial_number_div_"+modbus_device_count).remove();
                                $("#inverter_group_div_"+modbus_device_count).remove();
                                $("#dc_capacity_div_"+modbus_device_count).remove();
                                $("#inverter_capacity_div_"+modbus_device_count).remove();
                                $("#number_of_mppts_div_"+modbus_device_count).remove();
                                $("#strings_mppt_div_"+modbus_device_count).remove();
                                $("#modules_string_div_"+modbus_device_count).remove();
                                $("#modbus_device_"+modbus_device_count).append('<div id="inverter_option_'+modbus_device_count+'"><div class="mar-all col-lg-2 col-md-2" id="inverters_name_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Inverter Name" type="text" class="form-control" id="idinverterName_' + modbus_device_count + '" name="inverterName">' + 
                                                                '<i>(Type a inverter name)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="model_number_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Model Number" type="text" class="form-control" id="model_number_' + modbus_device_count + '" name="modelNumber">' + 
                                                                '<i>(Type inverter model number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="serial_number_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Serial Number" type="text" class="form-control" id="idserialNumber_' + modbus_device_count + '" name="serialNumber">' + 
                                                                '<i>(Type inverter serial number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="dc_capacity_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="DC Capacity in kW" type="text" class="form-control" id="iddcCapacity_' + modbus_device_count + '" name="dcCapacity">' + 
                                                                '<i>(Type dc capacity in kW)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="inverter_capacity_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Inverter Capacity in kW" type="text" class="form-control" id="idinverterCapacity_' + modbus_device_count + '" name="inverterCapacity" min="1">' + 
                                                                '<i>(Type inverters capacity in kW)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="number_of_mppts_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Number Of MPPTs" type="text" class="form-control" id="number_of_MPPT_' + modbus_device_count + '" name="number_of_MPPT" min="1">' + 
                                                                '<i>(Type a number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="strings_mppt_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="number" placeholder="Strings per MPPT" type="text" class="form-control" id="idstringsMPPT_' + modbus_device_count + '" name="stringsMPPT" min="1">' + 
                                                                '<i>(Type string mppt)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                        '<div class="mar-all col-lg-2 col-md-2" id="modules_string_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Modules per String" type="text" class="form-control" id="idmodulesString_' + modbus_device_count + '" name="modulesString">' + 
                                                                '<i>(Type module strings)</i>' + 
                                                            '</div>' + 
                                                        '</div></div>');
                                
                                $("#inverter_option_"+modbus_device_count).attr('id', 'inverter_option_' + modbus)
                                    .find('input')
                                    .each(function () {
                                        validatorModbus.addField($(this)[0].name);
                                })

                                inverter_present++;

                                if(inverter_present == 1) {
                                    
                                    var field_option = ["inverterName", "modelNumber", "serialNumber", "dcCapacity", "inverterCapacity", "number_of_MPPT", "stringsMPPT", "modulesString"];

                                    for(var field = 0; field < field_option.length; field++) {
                                        if(field_option[field] == "inverterName") {
                                            option.fields[field_option[field]] = {
                                                validators: {
                                                    notEmpty: {
                                                        message: 'The value is required.'
                                                    },
                                                    regexp: {
                                                        regexp: /^[a-zA-Z0-9_ ]+$/,
                                                        message: 'The first name can only consist of alphabetical characters and spaces'
                                                    }
                                                }
                                            }
                                        } else {
                                            option.fields[field_option[field]] = {
                                                message: 'The value is not valid',
                                                validators: {
                                                    notEmpty: {
                                                        message: 'The value is required.'
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    console.log(option);
                                }

                                $('#create_plant').bootstrapValidator('revalidateField', "inverterName");
                                $('#create_plant').bootstrapValidator('revalidateField', "modelNumber");
                                $('#create_plant').bootstrapValidator('revalidateField', "serialNumber");
                                $('#create_plant').bootstrapValidator('revalidateField', "dcCapacity");
                                $('#create_plant').bootstrapValidator('revalidateField', "inverterCapacity");
                                $('#create_plant').bootstrapValidator('revalidateField', "number_of_MPPT");
                                $('#create_plant').bootstrapValidator('revalidateField', "stringsMPPT");
                                $('#create_plant').bootstrapValidator('revalidateField', "modulesString");
                                
                                console.log(isValid);

                                $('#create_plant').bootstrapValidator('validate');

                            } else if(modbus_device_selected == "energy_meter") {

                                console.log("inverter not selected");

                                $("#inverters_name_div_"+modbus_device_count).remove();
                                $("#model_number_div_"+modbus_device_count).remove();
                                $("#serial_number_div_"+modbus_device_count).remove();
                                $("#inverter_group_div_"+modbus_device_count).remove();
                                $("#dc_capacity_div_"+modbus_device_count).remove();
                                $("#inverter_capacity_div_"+modbus_device_count).remove();
                                $("#number_of_mppts_div_"+modbus_device_count).remove();
                                $("#strings_mppt_div_"+modbus_device_count).remove();
                                $("#modules_string_div_"+modbus_device_count).remove();

                                $("#modbus_device_"+modbus_device_count).append('<div id="energy_meter_option_'+modbus_device_count+'"><div class="mar-all col-lg-2 col-md-2" id="model_number_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Model Number" type="text" class="form-control" id="model_number_' + modbus_device_count + '" name="modelNumber">' + 
                                                                '<i>(Type Energy Meter model number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                    '</div>');

                                $("#energy_meter_option_"+modbus_device_count).attr('id', 'energy_meter_option_' + modbus)
                                    .find('input')
                                    .each(function () {
                                        validatorModbus.addField($(this)[0].name);
                                })

                                $('#create_plant').bootstrapValidator('revalidateField', "modelNumber");

                            } else {

                                console.log("inverter not selected");

                                $("#inverters_name_div_"+modbus_device_count).remove();
                                $("#model_number_div_"+modbus_device_count).remove();
                                $("#serial_number_div_"+modbus_device_count).remove();
                                $("#inverter_group_div_"+modbus_device_count).remove();
                                $("#dc_capacity_div_"+modbus_device_count).remove();
                                $("#inverter_capacity_div_"+modbus_device_count).remove();
                                $("#number_of_mppts_div_"+modbus_device_count).remove();
                                $("#strings_mppt_div_"+modbus_device_count).remove();
                                $("#modules_string_div_"+modbus_device_count).remove();

                                $("#modbus_device_"+modbus_device_count).append('<div id="scb_option_'+modbus_device_count+'"><div class="mar-all col-lg-2 col-md-2" id="model_number_div_' + modbus_device_count + '" style="margin-right: 2px;">' + 
                                                            '<div class="form-group">' + 
                                                                '<input type="text" placeholder="Model Number" type="text" class="form-control" id="model_number_' + modbus_device_count + '" name="modelNumber">' + 
                                                                '<i>(Type SCB model number)</i>' + 
                                                            '</div>' + 
                                                        '</div>' + 
                                                    '</div>');

                                $("#scb_option_"+modbus_device_count).attr('id', 'scb_option_' + modbus)
                                    .find('input')
                                    .each(function () {
                                        validatorModbus.addField($(this)[0].name);
                                })

                                $('#create_plant').bootstrapValidator('revalidateField', "modelNumber");

                            }
                        })

                        $("#modbus_address_"+modbus).val(modbus_data.modbus[modbus].address);
                        $("#manufacturer_"+modbus).val(modbus_data.modbus[modbus].manufacturer);

                        $("#modbus_device_"+modbus).attr('id', 'modbus_device_' + modbus)
                            .find('input')
                            .each(function () {
                                validatorModbus.addField($(this)[0].name);
                        })

                    }

                } else {
                    noty_message("No Devices Present!", 'error', 5000)
                    return;
                }

            }
            
        },
        error: function(data) {
            console.log("error_streams_data");
            
            console.log(data);

            if(data == 1) {
                noty_message("Seems like you’re adding an inverter of a new manufacturer, please contact the dataglen team to add the definition file.", 'information', 5000)
                return;
            } else if(data == 2) {
                noty_message("Error reading configuration file of this webdyn device, please contact the dataglen team.", 'error', 5000)
                return;
            } else if(data == 3) {
                noty_message("Error reading INV configuration of this webdyn device, please contact the webdyn or dataglen team.", 'error', 5000)
                return;
            } else if(data == 4) {
                noty_message("Seems like you’re adding a modbus device of a new manufacturer, please contact the dataglen team to add the definition file.", 'information', 5000)
                return;
            } else if(data == 5) {
                noty_message("Unknown error while parsing modbus device, please contact the dataglen team to add the definition file.", 'error', 5000)
                return;
            } else {
                noty_message("Error in Webdyn ID given!", 'error', 5000)
                return;
            }

        }
    });

}

$("#select_stream_0").on('change', function() {

        var stream_device_io = $("#select_stream_0").val();

        $("#irradiation_div_0").empty();

        if(stream_device_io == "IRRADIATION") {
            $("#irradiation_div_0").append('<div class="form-group">' + 
                                            '<input type="text" placeholder="Tilt Angle" type="text" class="form-control" id="tilt_angle_0" name="tilt_angle">' + 
                                            '<i>(Type Tilt Angle)</i>' + 
                                        '</div>');
        }
    })

function devices_io(device_io_number) {

    $("#devices_io").append('<div class="row" id="devices_row_'+device_io_number+'">' + 
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' + 
                                    '<div class="form-group">' + 
                                        '<input type="text" placeholder="Input ID" type="text" class="form-control" id="input_id_'+device_io_number+'" name="input_id" readonly>' + 
                                        '<i>(Input ID)</i>' + 
                                    '</div>' + 
                                '</div>' +
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' +
                                    '<div class="form-group">' + 
                                        '<select class="form-control" id="select_stream_'+device_io_number+'" name="select_stream" device_io="'+device_io_number+'">' + 
                                            '<option value="" disabled selected> --Select a Stream-- </option>' + 
                                            '<option value="AMBIENT_TEMPERATURE">AMBIENT TEMPERATURE</option>' + 
                                            '<option value="DAILY_PLANT_ENERGY">DAILY PLANT ENERGY</option>' + 
                                            '<option value="ENERGY_METER_DATA">ENERGY METER DATA</option>' + 
                                            '<option value="EXTERNAL_IRRADIATION">EXTERNAL IRRADIATION</option>' + 
                                            '<option value="FREQUENCY">FREQUENCY</option>' + 
                                            '<option value="HIGHEST_AMBIENT_TEMPERATURE">HIGHEST AMBIENT TEMPERATURE</option>' + 
                                            '<option value="IRRADIATION">IRRADIATION</option>' + 
                                            '<option value="MODULE_TEMPERATURE">MODULE TEMPERATURE</option>' + 
                                            '<option value="PLANT_ACTIVE_POWER">PLANT ACTIVE POWER</option>' + 
                                            '<option value="TOTAL_PLANT_ENERGY">TOTAL PLANT ENERGY</option>' + 
                                            '<option value="WINDSPEED">WINDSPEED</option>' + 
                                            '<option value="TRANSFORMER">TRANSFORMER</option>' + 
                                            '<option value="CIRCUIT_BREAKER_STATUS1">CIRCUIT BREAKER STATUS1</option>' + 
                                            '<option value="CIRCUIT_BREAKER_STATUS2">CIRCUIT BREAKER STATUS2</option>' + 
                                            '<option value="OTI">OTI</option>' + 
                                            '<option value="WTI">WTI</option>' + 
                                        '</select>' + 
                                        '<i>(Select a Stream)</i>' + 
                                    '</div>' + 
                                '</div>' + 
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' + 
                                    '<div class="form-group">' + 
                                        '<input type="text" placeholder="Manufacturer" type="text" class="form-control" id="device_manufacturer_'+device_io_number+'" name="device_manufacturer">' + 
                                        '<i>(Manufacturers name)</i>' + 
                                    '</div>' + 
                                '</div>' + 
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' + 
                                    '<div class="form-group">' + 
                                        '<input type="text" placeholder="Lower Bound" type="text" class="form-control" id="lower_bound_'+device_io_number+'" name="lower_bound">' + 
                                        '<i>(Enter Lower Bound)</i>' + 
                                    '</div>' + 
                                '</div>' + 
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' + 
                                    '<div class="form-group">' + 
                                        '<input type="text" placeholder="Upper Bound" type="text" class="form-control" id="upper_bound_'+device_io_number+'" name="upper_bound">' + 
                                        '<i>(Enter Upper Bound)</i>' + 
                                    '</div>' + 
                                '</div>' + 
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;">' + 
                                    '<div class="form-group">' + 
                                        '<select class="form-control" id="output_range_'+device_io_number+'" name="output_range">' + 
                                            '<option value="" disabled selected> --Select Output Range-- </option>' + 
                                            '<option value="4-20mA">4-20 mA</option>' + 
                                            '<option value="0-10V">0-10 V</option>' +
                                        '</select>' + 
                                        '<i>(Option)</i>' + 
                                    '</div>' + 
                                '</div>' +
                                '<div class="mar-all col-lg-2 col-md-2" style="margin-right: 2px;" id="irradiation_div_'+device_io_number+'" name="'+device_io_number+'">' + 

                                '</div>' +
                            '</div>');
    
    $("#input_id_"+device_io_number).val(device_io_number+1);

    $("#select_stream_"+device_io_number).on('change', function() {

        var device_number = $(this).attr('device_io');
        var stream_device_io = $("#select_stream_"+device_number).val();

        $("#irradiation_div_"+device_number).empty();

        if(stream_device_io == "IRRADIATION") {
            $("#irradiation_div_"+device_number).append('<div class="form-group">' + 
                                            '<input type="text" placeholder="Tilt Angle" type="text" class="form-control" id="tilt_angle_'+device_io_number+'" name="tilt_angle">' + 
                                            '<i>(Type Tilt Angle)</i>' + 
                                        '</div>');
        }
    })

}

function add_plant_details(webdyn_id_data) {

    $("#client_spinner").show();

    var devices_details = {
        "group_details": [],
        "inverters": [],
        "modbus": [],
        "io": []
    };

    var panel_area = ($("#length_panel_area").val() * $("#breadth_panel_area").val() * $("#panel_number").val())/1000000;

    devices_details["group_details"][0] = {
        "name": $("#group_name").val(),
        "data_logger_device_id": $("#device_id").val(),
        "panel_numbers": $("#panel_number").val(),
        "panel_area": panel_area,
        "tilt_angle": $("#tilt_angle").val(),
        "type": $("#group_type").val(),
        "azimuth": $("#azimuth").val()
    };

    if(webdyn_id_data.modbus.length > 0) {
        for(var device = 0; device < webdyn_id_data.modbus.length; device++) {

            var modbus_address = $("#modbus_address_"+device).val();
            var device_manufacturer = $("#manufacturer_"+device).val();

            var modbus_device_selected = $("#modbus_device_select_"+device).val();
            console.log(modbus_device_selected);

            if(modbus_device_selected == "inverter") {
                var inverter_name = $("#idinverterName_"+device).val();
                var model_num = $("#model_number_"+device).val();
                var serial_num = $("#idserialNumber_"+device).val();
                var dc_capacity = $("#iddcCapacity_"+device).val();
                var inverter_capacity = $("#idinverterCapacity_"+device).val();
                var number_of_mppts = $("#number_of_MPPT_"+device).val();
                var string_per_mppts = $("#idstringsMPPT_"+device).val();
                var modules_per_string = $("#idmodulesString_"+device).val();

                devices_details["modbus"][device] = {
                    "modbus_address": modbus_address,
                    "device": "Inverter",
                    "manufacturer": device_manufacturer,
                    "name": inverter_name,
                    "model_number": model_num,
                    "capacity": inverter_capacity,
                    "connected_dc_capacity": dc_capacity,
                    "serial_number": serial_num,
                    "number_of_mppts": number_of_mppts,
                    "strings_per_mppt": string_per_mppts,
                    "modules_per_string": modules_per_string
                };
            } else if(modbus_device_selected == "energy_meter") {

                var model_number = $("#model_number_"+device).val();

                devices_details["modbus"][device] = {
                    "modbus_address": modbus_address,
                    "device": "Energy_Meter",
                    "manufacturer": device_manufacturer,
                    "model_number": model_number
                };

            } 

        } 
    }

    if(webdyn_id_data.inverters.length > 0) {
        for(var device = 0; device < webdyn_id_data.inverters.length; device++) {

            var modbus_address = $("#inverter_modbus_address_"+device).val();
            var device_manufacturer = $("#inverter_manufacturer_"+device).val();

            var inverter_name = $("#single_inverter_"+device).val();
            var model_num = $("#inverter_model_number_"+device).val();
            var serial_num = $("#inverter_serial_number_"+device).val();
            var dc_capacity = $("#inverter_dc_capacity_"+device).val();
            var inverter_capacity = $("#single_inverter_capacity_"+device).val();
            var number_of_mppts = $("#inverter_number_of_MPPT_"+device).val();
            var string_per_mppts = $("#inverter_string_per_mppt_"+device).val();
            var modules_per_string = $("#inverter_modules_per_string_"+device).val();

            devices_details["inverters"][device] = {
                "modbus_address": modbus_address,
                "manufacturer": device_manufacturer,
                "name": inverter_name,
                "model_number": model_num,
                "capacity": inverter_capacity,
                "connected_dc_capacity": dc_capacity,
                "serial_number": serial_num,
                "number_of_mppts": number_of_mppts,
                "strings_per_mppt": string_per_mppts,
                "modules_per_string": modules_per_string
            };

        } 
    }

    for(var io_device = 0; io_device <= device_io_number; io_device++) {
        devices_details["io"][io_device] = {
            "input_id": $("#input_id_"+io_device).val(),
            "stream": $("#select_stream_"+io_device).val(),
            "manufacturer": $("#device_manufacturer_"+io_device).val(),
            "lower_bound": $("#lower_bound_"+io_device).val(),
            "upper_bound": $("#upper_bound_"+io_device).val(),
            "output_range": $("#output_range_"+io_device).val()
        };
    }

    console.log(devices_details);

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: "/api/v1/plant/devices/?plant_slug=".concat(plant_slug),
        data: JSON.stringify(devices_details),
        headers : {
            Authorization : 'Bearer ' + csrftoken
        },
        success: function(devices_details) {

            console.log(devices_details);

            $("#client_spinner").hide();

            window.location.href = ("/solar/plant/" + plant_slug + "/");
            
            noty_message("Your device has been added!", 'success', 5000)
            return;

        },
        error: function(data) {
            console.log("error_streams_data");

            $("#client_spinner").hide();

            $("#previous_button").trigger("click");

            noty_message("Device can not be added. Please check the details again.", 'error', 5000)
            return;

        }
    });

}

$("#finish_button").click(function() {

    console.log("finish clicked");

    $("#finish_button").addClass("disabled");

    add_plant_details(webdyn_id_data);

    $("#finish_button").addClass("disabled");

})

$("#reload_button").click(function() {

    location.reload();

})

$("#add_io_device").click(function() {

    device_io_number++;

    if(device_io_number < 8) {
        devices_io(device_io_number);    
    } else {
        device_io_number = 8;

        noty_message("The maximum number of I/O Devices can be 8!", 'information', 5000)
        return;
    }

})

$("#minus_io_device").click(function() {

    if(device_io_number > 0) {
        $("#devices_row_"+device_io_number).remove();
    } else {
        device_io_number = 0;

        noty_message("The minimum number of I/O Devices cannot be less than 1!", 'information', 5000)
        return;
    }

    device_io_number--;

})

function inverter_fields_validation() {

    $("form[name='add_plant_details']").validator('update', {
        rules: {
            inverterName: "required",
            modelNumber: "required",
            serialNumber: "required",
            dcCapacity: "required",
            inverterCapacity: "required",
            number_of_MPPT: "required",
            stringsMPPT: "required",
            modulesString: "required"
        },
        messages: {
            inverterName: "Please enter the inverter name",
            modelNumber: "Please enter the model number",
            serialNumber: "Please enter the serial number",
            dcCapacity: "Please enter the dc capacity",
            inverterCapacity: "Please enter the inverter capacity",
            number_of_MPPT: "Please enter the number of MPPT",
            stringsMPPT: "Please enter the strings MPPT",
            modulesString: "Please enter the modules in String"
        }
    })

}