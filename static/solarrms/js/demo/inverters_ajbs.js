$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Reports</a></li>')

    inverters_ajbs();
});

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        window.dispatchEvent(new Event('resize'));
    });
}

$("#devices").change(function(){
  var device = $(".filter-option").text();

    console.log(device);

  if(device == "Ajbs") {
    ajbs();
  } else {
    inverters_ajbs();
  }
});

function inverters_ajbs() {

  $(".loader").show();

  /*$("#inverters_filters_and_sorts").empty();
  $("#inverters_filters_and_sorts").append('<div class="row"><div class="col-lg-4 col-md-4 col-sm-4"><h3 class="text-info">Filter</h3>' +
                    '<div id="filters" class="btn-group">  <button class="btn btn-default is-checked" data-filter="*">Show All</button>' +
                        '<button class="btn btn-default" data-filter=".connected">Operational</button>' +
                        '<button class="btn btn-default" data-filter=".unknown">Alarms/Errors</button>' +
                        '<button class="btn btn-default" data-filter=".disconnected">Disconnected</button>' +
                    '</div></div>' +
                    '<div class="col-lg-4 col-md-4 col-sm-4"><h3 class="text-info">Sort</h3>' +
                    '<div id="sorts" class="btn-group">  <button class="btn btn-default is-checked" data-sort-by="original-order">Inverter Name</button>' +
                        '<button class="btn btn-default" data-sort-by="energy">Energy</button>' +
                        '<button class="btn btn-default" data-sort-by="power">Power</button>' +
                    '</div></div>' + 
                    '<div class="col-lg-4 col-md-4 col-sm-4"><h3 class="text-info">Selection</h3>' + 
                    '<div id="selection" class="btn-group">' +
                        '<button class="btn btn-default selection_button is-checked" data-filter=".ajbs_down">Ajbs Down</button>' +
                        '<button class="btn btn-default selection_button" data-filter=".inside_temperature">Inside Temp.</button>' +
                        '<button class="btn btn-default selection_button" data-filter=".spd_status">Status</button>' +
                    '</div></div></div>');*/

  $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
        success: function(data) {
            console.log(data);

            $("#inverters_grid").empty();

            var connection, connection_panel, connection_status, connection_text_color_status, group_name, solar_status, total_ajbs_down, ajbs_down_number, total_ajbs_down_class, errors, errors_hide;

            for(var i = 0; i < data.inverters.length; i++) {
              if(data.inverters[i].solar_group) {
                group_name = data.inverters[i].solar_group;
              }

              if(data.inverters[i].last_three_errors.length) {
                if(data.inverters[i].last_three_errors.length > 0) {
                  errors_hide = "show";
                  errors = "";
                  for(var j = 0; j < data.inverters[i].last_three_errors.length; j++) {
                    errors = errors + data.inverters[i].last_three_errors[j] + ", ";
                  }
                  errors = errors.slice(0, -2);
                } else {
                  errors_hide = "hidden";
                }
              } else {
                errors_hide = "hidden";
              }

              if(data.inverters[i].total_ajbs && data.inverters[i].total_ajbs > 0) {
                  ajbs_down_number = data.inverters[i].total_ajbs;
                  total_ajbs_down = data.inverters[i].total_ajbs + " AJBs" ;
                  total_ajbs_down_class = "show";
              } else {
                  ajbs_down_number = 0;
                  total_ajbs_down = "NA";
                  total_ajbs_down_class = "hidden";
              }

              if(data.inverters[i].connected == "connected" && ajbs_down_number == 0 && errors_hide == "hidden") {
                  connection_status = "connected";
                  connection = "connected_no_alarms_no_ajbs_down";
                  connection_text_color_status = "badge-success";
                  connection_panel = "panel panel-bordered-success";
              } else if(data.inverters[i].connected == "connected" && ajbs_down_number != 0 && errors_hide == "show") {
                  connection_status = "connected";
                  connection = "connected_alarms_ajbs_down";
                  connection_text_color_status = "badge-danger";
                  connection_panel = "panel panel-bordered-danger";
              } else if(data.inverters[i].connected == "disconnected") {
                  connection_status = "disconnected";
                  connection = "disconnected";
                  connection_text_color_status = "badge-warning";
                  connection_panel = "panel panel-bordered-warning";
              } else if(data.inverters[i].connected == "unknown"){
                  connection_status = "communictaion error";
                  connection = "unknown";
                  connection_text_color_status = "badge-info";
                  connection_panel = "panel panel-bordered-info";
              }

              if(data.inverters[i].last_inverter_status && data.inverters[i].last_inverter_status["0"] && data.inverters[i].last_inverter_status["0"].status) {
                  solar_status = data.inverters[i].last_inverter_status["0"].status;
              } else {
                  solar_status = "NA";
              }

              $("#inverters_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel grey_panel" data-category="' + connection + '" id="inverter_'+i+'" style="padding-bottom: 5px;">' +
    '<div class="row">' + 
        '<div class="col-lg-6 col-md-6 col-sm-6 col-xs-6">' + 
            '<div class="row">' + 
                '<div class="pull-left"><span class="power text-dark text-bold">' + parseFloat(data.inverters[i].power).toFixed(1) + '</span><span class="power_unit text-dark text-bold" style="font-size: small" id="power_unit"> kW</span></div>' +
            '</div>' +
            '<div class="row">' + 
                '<div class="pull-left"><p class="power_text text-dark text-sm text-bold">Current Power</p></div>' + 
            '</div>' +
        '</div>' +
        /*'<div class="col-lg-6 col-md-6 col-sm-6 col-xs-6">' + 
            '<div class="row">' + 
                '<div class="pull-right"><span class="energy text-dark">' +  + '</span><span class="text-dark" style="font-size: small" id="energy_unit"> kW</span></div>' + 
            '</div>' +
            '<div class="row">' + 
                '<div class="pull-right"><p class="energy_text text-dark text-sm">Capacity</p></div>' + 
            '</div>' + 
        '</div>' +*/
      '</div>' +
      '<div class="row">' + 
        '<div class="row text-center">' + 
            '<span class="energy text-dark text-bold text-2x">' + (parseFloat(data.inverters[i].generation)).toFixed(1) + '</span><span class="text-dark text-bold" style="font-size: small" id="energy_unit"> kWh</span>' + 
        '</div>' +
        '<div class="row text-center">' + 
            '<p class="energy_text text-bold text-dark text-sm">Generation Today</p>' + 
        '</div>' + 
        '<div class="row text-center">' +
            '<span class="name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.inverters[i].name + ", " + parseFloat(data.inverters[i].capacity) + ' kW</span> <span class="group_name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.inverters[i].solar_group + '</span>' +
        '</div>' +
        '<div class="row text-center pad-top">' +
            '<button total_ajbs="' + data.inverters[i].total_ajbs + '" id="inverter_know_' + i + '" name="' + data.inverters[i].name + '" class="btn btn-xs btn-info text-bold">Know More</button>' +
        '</div>' +
      '</div>' +
      /*'<div class="row">' + 
          '<div class="col-lg-4 col-md-4 col-sm-4 col-xs-4 pad-top" style="padding-left: 0px;padding-right: 0px;">' + 
              '<span class="solar_status_value pull-left text-info">Status: ' + solar_status + '</span>' +
          '</div>' +
          '<div class="col-lg-4 col-md-4 col-sm-4 col-xs-4">' +
              '<div class=" ajbs_down">' +
                  '<div class="row pad-top">' + 
                        '<span class="ajbs_down text-sm text-danger pad-rgt' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' + 
                  '</div>' +
              '</div>' +
              '<div class="pull-right inside_temperature" hidden>' +
                  '<div class="row pad-top">' + 
                        '<span class="inside_temperature_value text-primary">' + data.inverters[i].inside_temperature + '&#8451;</span> <i class="fa fa-thermometer-three-quarters" aria-hidden="true"></i>' +
                  '</div>' +
              '</div>' +
              '<div class="pull-right solar_status pad-top" hidden>' +
                  '<div class="row">' + 
                        '<span class="solar_status_value text-info">Status: ' + solar_status + '</span>' +
                  '</div>' +
              '</div>' +
          '</div>' +
          '<div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 ' + errors_hide + ' pad-top text-center">' +
              '<span class="solar_status_value text-info">Errors: ' + errors + '</span>' +
          '</div>' +
          '<div class="col-lg-2 col-md-2 col-sm-2 col-xs-2 pull-right">' +
              '<div class="ajbs_down pull-right">' +
                  '<div class="row pad-top">' + 
                        '<span class="ajbs_down text-sm text-danger pad-rgt' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' + 
                  '</div>' +
              '</div>' +
              '<div class="pull-right inside_temperature" hidden>' +
                  '<div class="row pad-top">' + 
                        '<span class="inside_temperature_value text-primary">' + data.inverters[i].inside_temperature + '&#8451;</span> <i class="fa fa-thermometer-three-quarters" aria-hidden="true"></i>' +
                  '</div>' +
              '</div>' +
          '</div>' +
      '</div>' +
  '</div>*/'</div>');

            $("#inverter_"+i).removeClass("panel panel-bordered-success");
            $("#inverter_"+i).removeClass("panel panel-bordered-danger");
            $("#inverter_"+i).removeClass("panel panel-bordered-info");
            $("#inverter_"+i).addClass(connection);

            $("#inverter_know_"+i).click(function() {
                var inverter_name = $(this).attr("name");
                console.log(inverter_name);

                $.ajax({
                    type: "GET",
                    url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
                    data: {device_type: "ajb", inverter: inverter_name},
                    success: function(inverter_ajb_data) {
                        console.log(inverter_name);

                        if(inverter_ajb_data.ajbs.length) {
                            
                            $("#info_modal").modal({
                                showClose: false
                            });

                            var modal_info = $("#modal_info");
                            modal_info.empty();

                            modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>All AJBs in " + inverter_name + "</span></div><br/>");
                            modal_info.append('<div class="panel-body"><table class="table table-vcenter"><thead><tr><th class="text-center min-width">AJB Name</th><th class="text-center">Power (kW)</th><th class="text-center">Current (A)</th><th class="text-center">Voltage (W)</th><th class="text-center">Connection</th></tr></thead><tbody id="table_data"></tbody></table></div>');

                            var table_data = $("#table_data");
                            table_data.empty();

                            for(var ajb_table_row = 0; ajb_table_row < inverter_ajb_data.ajbs.length; ajb_table_row++) {
                                table_data.append("<tr id='modal_row"+ajb_table_row+"'><td class='text-center'><span class='text-semibold'>" + inverter_ajb_data.ajbs[ajb_table_row].name + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].power)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].current)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].voltage)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + inverter_ajb_data.ajbs[ajb_table_row].connected + "</span></td></tr>");
                            }

                        } else {

                            noty_message("No Ajbs for " +  inverter_name + "!", "information", 4000);
                            return;

                        }
                    },
                    error: function(data) {
                        console.log("error_streams_data");

                        noty_message("No Ajbs for " +  inverter_name + "!", "information", 4000);
                        return;
                    }
                });
              });
            }

          var $grid = $('#inverters_grid').isotope({
              itemSelector: '.element-item',
              layoutMode: 'fitRows',
              getSortData: {
                  name: '.name',
                  energy: '.energy',
                  power: '.power',
                  connection: '[data-category]'
                  /*power: function( itemElem ) {
                      var power = $( itemElem ).find('.power').text();
                      return parseFloat( power );
                  }*/
              }
          });

          /*$(".ajbs_down").click(function(){
              $("#filter_click").empty();
              $("#filter_click").append('<div class="row">' + 
                      '<span class="total_ajbs_down text-danger pad-lft ' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' +
                  '</div>' +
                  '<div class="row">' + 
                      '<span class="total_ajbs_down_text text-danger pad-rgt ' + total_ajbs_down_class + '">AJBs <i class="fa fa-long-arrow-down" aria-hidden="true"></i></p>' + 
                  '</div>');
          });*/

          // filter functions
          var filterFns = {

            // show if number is greater than 50
            /*numberGreaterThan50: function() {
              var number = $(this).find('.number').text();
              return parseInt( number, 10 ) > 50;
            },
            // show if name ends with -ium
            ium: function() {
              var name = $(this).find('.name').text();
              return name.match( /ium$/ );
            }*/
          };

          // bind filter button click
          filters("#filters", $grid);

          // bind sort button click
          sorts("#sorts", $grid);

          // change is-checked class on buttons
          button_in_check();

          $(".selection_button").click(function() {
              var selection_checked = $(this).text();

              if(selection_checked == "Ajbs Down") {
                $(".inside_temperature").hide();
                $(".solar_status").hide();
                $(".ajbs_down").show();
              } else if(selection_checked == "Inside Temp.") {
                $(".ajbs_down").hide();
                $(".solar_status").hide();
                $(".inside_temperature").show();
              } else if(selection_checked == "Status") {
                $(".ajbs_down").hide();
                $(".inside_temperature").hide();
                $(".solar_status").show();
              }

              filters("#filters", $grid);
          })

          $(".loader").hide();

          ajbs();

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $(".loader").hide();
        }
    });

}

function ajbs() {

    /*$("#ajbs_filters_and_sorts").empty();
    $("#ajbs_filters_and_sorts").append('<div class="row"><div class="col-lg-6 col-md-6 col-sm-6"><h3 class="text-info">Filter</h3>' +
                    '<div id="ajbs_filters" class="btn-group">  <button class="btn btn-default is-checked" data-filter="*">Show All</button>' +
                        '<button class="btn btn-default" data-filter=".connected">Operational</button>' +
                        '<button class="btn btn-default" data-filter=".unknown">Alarms/Errors</button>' +
                        '<button class="btn btn-default" data-filter=".disconnected">Disconnected</button>' +
                    '</div></div>' +
                    '<div class="col-lg-6 col-md-6 col-sm-6"><h3 class="text-info">Sort</h3>' +
                    '<div id="ajbs_sorts" class="btn-group">  <button class="btn btn-default is-checked" data-sort-by="original-order">Original Order</button>' +
                        '<button class="btn btn-default" data-sort-by="current">Current</button>' +
                        '<button class="btn btn-default" data-sort-by="ajb_power">Ajb Power</button>' +
                        '<button class="btn btn-default" data-sort-by="voltage_value">Voltage</button>' +
                    '</div></div></div>');*/

  $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
        data: {device_type: "ajb"},
        success: function(data) {
          if(data.ajbs.length) {

            $("#device_list").show();
            $("#ajbs_grid").empty();

            var connection, connection_status, group_name, spd_status, spd_status_class, spd_status_text;

            for(var i = 0; i < data.ajbs.length; i++) {
                if(data.ajbs[i].solar_group) {
                    group_name = data.ajbs[i].solar_group;
                } else {
                    group_name = "NA";
                }
                if(data.ajbs[i].connected == "connected") {
                    connection_status = "connected";
                    connection = "connected";
                    connection_text_color_status = "badge-success";
                } else if(data.ajbs[i].connected == "disconnected") {
                    connection_status = "disconnected";
                    connection = "disconnected";
                    connection_text_color_status = "badge-danger";
                } else {
                    connection_status = "communictaion error";
                    connection = "unknown";
                    connection_text_color_status = "badge-info";
                }

                if(data.ajbs[i].last_spd_status && data.ajbs[i].last_spd_status["0"] && data.inverters[i].ajbs[i].last_spd_status[0].spd_status) {
                    spd_status = data.inverters[i].last_inverter_status["0"].status;
                    spd_status_class = "show";
                } else {
                    spd_status = "NA";
                    spd_status_class = "hidden";
                }

              $("#ajbs_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel panel-bordered-dark grey_panel" data-category="' + data.ajbs[i].connected + '" id="ajb_'+i+'" style="border: 3px solid white;">' +
      '<div class="row">' + 
        '<div class="col-lg-6 col-md-6">' + 
            '<div class="row">' + 
                '<span class="text-dark text-2x current">' + (parseFloat(data.ajbs[i].current)).toFixed(1) + '</span><span class="text-dark" style="font-size: small" id="current_unit"> A</span>' + 
            '</div>' +
            '<div class="row">' + 
                '<p class="current_text text-dark text-sm">Current</p>' + 
            '</div>' + 
        '</div>' +
        '<div class="col-lg-6 col-md-6">' + 
            '<div class="row">' + 
                '<div class="pull-right"><span class="text-dark text-2x ajb_power">' + parseFloat(data.ajbs[i].power).toFixed(1) + '</span><span class="ajb_power_unit text-dark" style="font-size: small" id="ajb_power_unit"> kW</span></div>' +
            '</div>' +
            '<div class="row">' + 
                '<div class="pull-right"><p class="ajb_power_text text-dark text-sm">Power</p></div>' + 
            '</div>' +
        '</div>' +
      '</div>' +
      '<div class="row" style="padding-bottom: 5px;">' + 
          '<div class="col-lg-9 col-md-9 pad-top" style="padding-left: 0px;padding-right: 0px;">' + 
              '<span class="ajb_name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.ajbs[i].name + '</span> <span class="inverter_name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.ajbs[i].inverter_name + '</span>' + 
          '</div>' +
          '<div class="col-lg-3 col-md-3">' +
              '<div class="pull-right voltage">' +
                  '<div class="row">' + 
                        '<span class="text-dark voltage_value">' + (parseFloat(data.ajbs[i].voltage)).toFixed(1) + ' W</span>' +
                  '</div>' +
                  '<div class="row">' + 
                        '<span class="voltage_text text-dark">Voltage</span>' + 
                  '</div>' +
              '</div>' +
          '</div>' +
      '</div>' +
  '</div></div>');

              $("#ajb_"+i).removeClass("connected");
              $("#ajb_"+i).removeClass("disconnected");
              $("#ajb_"+i).removeClass("unknown");
              $("#ajb_"+i).addClass(connection);
            }

            var $grid = $('#ajbs_grid').isotope({
                itemSelector: '.element-item',
                layoutMode: 'fitRows',
                getSortData: {
                    ajb_name: '.ajb_name',
                    current: '.current',
                    ajb_power: '.ajb_power',
                    voltage_value: '.voltage_value',
                    connection: '[data-category]',
                    /*power: function( itemElem ) {
                        var power = $( itemElem ).find('.power').text();
                        return parseFloat( power );
                    }*/
                }
            });

            // filter functions
            var filterFns = {
            // show if number is greater than 50
            /*numberGreaterThan50: function() {
              var number = $(this).find('.number').text();
              return parseInt( number, 10 ) > 50;
            },
            // show if name ends with -ium
            ium: function() {
              var name = $(this).find('.name').text();
              return name.match( /ium$/ );
            }*/
            };

            // bind filter button click
            filters("#ajbs_filters", $grid);

            // bind sort button click
            sorts("#ajbs_sorts", $grid);

            // change is-checked class on buttons
            button_in_check();
          }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $(".loader").hide();
        }
    });

}

function filters(id, grid) {

    $(id).on( 'click', 'button', function() {
        var filterValue = $( this ).attr('data-filter');
        grid.isotope({ filter: filterValue });
    });
}

function sorts(id, grid) {

    $(id).on( 'click', 'button', function() {
        var sortByValue = $(this).attr('data-sort-by');
        console.log($(this).attr('data-sort-by'));
        grid.isotope({ sortBy: sortByValue });
    });

}

function button_in_check() {

    $('.btn-group').each( function( i, buttonGroup ) {
        var $buttonGroup = $( buttonGroup );
        $buttonGroup.on( 'click', 'button', function() {
            $buttonGroup.find('.is-checked').removeClass('is-checked');
            $( this ).addClass('is-checked');
        });
    });

}