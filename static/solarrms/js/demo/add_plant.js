$(document).ready(function() {
    
    console.log("new form");

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Add Plant</a></li>')

    /*download_options();*/    
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
        plant_name: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        location: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        city: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        plant_dc_capacity: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        plant_ac_capacity: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        latitude: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        longitude: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        spv_module_wp_stc: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        spv_module_efficiency_stc: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        length_module: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        breadth_module: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        spv_module_make: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        spv_module_technology: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        total_number_of_spv: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        }
    }
};

$("#create_plant").bootstrapValidator(option).on('success.field.bv', function(e, data) {
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
    isValid = false;
});

$('#plant_name').keypress(function(eve) {
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#plant_name').keyup(function(eve) {
        var plant_name = $(this).val().toLowerCase();
        var plant_no = "plant";

        var plant_not = plant_name.indexOf(plant_no) !== -1;

        if(plant_not == true) {
            $("#form_error_message_plant").empty();
            $("#form_error_message_plant").append("<div class='alert alert-warning' id='alert'>The plant name is unacceptable. Remove 'plant' from the name.</div>");
        } else {
            $("#form_error_message_plant").empty();
        }
    });
});

$('#plant_dc_capacity').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#plant_dc_capacity').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#plant_ac_capacity').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#plant_ac_capacity').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#latitude').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#latitude').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#longitude').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#longitude').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#elevation').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).charset().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#elevation').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#spv_module_efficiency_stc').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#spv_module_efficiency_stc').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#length_module').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#length_module').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$('#breadth_module').keypress(function(eve) {
    if ((eve.which != 46 || $(this).val().indexOf('.') != -1) && (eve.which < 48 || eve.which > 57) || (eve.which == 46 && $(this).caret().start == 0) ) {
        eve.preventDefault();
    }
     
    // this part is when left part of number is deleted and leaves a . in the leftmost position. For example, 33.25, then 33 is deleted
    $('#breadth_module').keyup(function(eve) {
        if($(this).val().indexOf('.') == 0) {    
            $(this).val($(this).val().substring(1));
        }
    });
});

$("#create_plant-button").click(function(e) {
    
    $("#client_spinner").show();

    $('#create_plant').bootstrapValidator('validate');
    
    console.log("create plant");

	var plant_data = {
        "plant_details": {},
        "module_details": {}
    }

    plant_data["plant_details".toString()] = {
        "name": $("#plant_name").val(),
        "location": $("#location").val(),
        "city": $("#city").val(),
        "ac_capacity": $("#plant_ac_capacity").val(),
        "dc_capacity": $("#plant_dc_capacity").val(),
        "lat": $("#latitude").val(),
        "long": $("#longitude").val()
    }

    var elevation = $("#elevation").val();

    if(elevation != "") {
        plant_data["plant_details".toString()]["elevation".toString()] = elevation;
    }

    console.log(elevation);

    var spv_module_area = ($("#length_module").val() * $("#breadth_module").val() * $("#total_number_of_spv").val())/1000000;

    plant_data["module_details".toString()] = {
        "panel_capacity": $("#spv_module_wp_stc").val(),
        "panel_efficiency": $("#spv_module_efficiency_stc").val(),
        "panel_area": spv_module_area,
        "panel_manufacturer": $("#spv_module_make").val(),
        "model_number": $("#spv_module_technology").val(),
        "total_number_of_panels": $("#total_number_of_spv").val()
    }

    console.log(plant_data);

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: "/api/v1/plant/entry/",
        data: JSON.stringify(plant_data),
        success: function(plant_details) {

            console.log(plant_details);
            window.location.href = ("/solar/plant/" + plant_details.plant_slug + "/add_plant_options/");
            
            $("#client_spinner").hide();

        },
        error: function(data) {
            console.log(data);
            console.log("error_streams_data");

            $("#client_spinner").hide();

            noty_message("Plant can not be created. Please check the name and all other required parameters are filled.", 'error', 5000)
            return;
        }
    });

});