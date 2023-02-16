$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Context Analysis</a></li>')

    limit_compare_plant_date();
    parameters_dropdown();

    $("input[name$='radios']").click(function() {
        var r_button = $(this).val();
        
        if(r_button == "Power") {
          comparison_select = 0;
        } else if(r_button == "Energy") {
          comparison_select = 1;
        }
    });
});

$(function() {
    $(".datetimepicker_plant_level_start_time").datetimepicker({
        timepicker: false,
        format: 'Y/m/d',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_plant_level_start_time").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function get_dates(){
    // get the start date
    var st = $("#plant_level_start_time").val();
    /*var st = new Date();*/
    if (st == '')
        st = new Date();
    else
        st = new Date(st);
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function limit_compare_plant_date() {
  $(function(){
    $('#plant_level_start_time').datetimepicker({
      onShow:function( ct ){
          this.setOptions({
          maxDate: new Date()
        })
      },
    });
  });
}

function parameters_dropdown() {

    $('#parameters_dropdown').empty();
    $("#parameters_dropdown").append("<option value='' disabled selected>-- Choose Parameter --</option>");

    /*for(var i = 0; i < streams.length; i++) {
        $("#parameters_dropdown").append("<option value='"+streams[i]+"'>" + streams[i] + "</option>");
    }*/

    $('#parameters_dropdown').empty();
    $.ajax({
      type: "GET",
      url: "/api/sources/".concat(sourcekey).concat('/streams/'),
      success: function(streams){
          $('#parameters_dropdown').html('');
          if (streams.length == 0) {
              $('#parameters_dropdown').append("<option>No Streams are present! </option>");
          } else {
              for (var i = 0 ; i <= streams.length-1 ; i++) {
                $('#parameters_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
              }
          }
      },
      error: function(data){
          console.log("no data");
      }
    });

    /*var streams_array = ["IRRADIATION", "MODULE_TEMPERATURE", "ENERGY_METER_DATA", "EXTERNAL_IRRADIATION", "AMBIENT_TEMPERATURE", "FREQUENCY"];

    for (var i = 0 ; i <= streams_array.length-1 ; i++) {
      $('#parameters_dropdown').append("<option value=" + streams_array[i] + ">" + streams_array[i] + "</option>");
    }*/

    /*$.ajax({
      type: "GET",
      url: "/api/sources/".concat("sZmA3R5563fooMq").concat('/streams/'),
      success: function(streams){
        if (streams.length == 0) {
            $("#parameters_dropdown").append("<option>No Streams are present! </option>");
        } else {
            for (var i = 0 ; i <= streams.length-1 ; i++) {
                $('#parameters_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
                $('#parameters_single_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
            } 
        }
      },
      error: function(data){
          console.log("no data");
      }
    });*/
}

/*function plant_power() {

    var separate_id = "plant_level_start_time";

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    if(comparison_select == 0) {
      power_data(plant_slug, st, et, 'power_data_id', null);
    } else if(comparison_select == 1) {
      day_energy_data();
    }

}*/

/*function parameter_data() {

    var separate_id = "plant_level_start_time";

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    var fields = [];

    var arrayValue = [];
    var packagedData = [];

    $('#parameters_dropdown > option:selected').each(function() {
        fields.push($(this).val());
    });

    $.ajax({
        type: "GET",
        async: false,
        url: "/api/sources/".concat(sourcekey).concat('/data/'),
        data: {streamNames: fields.join(","), startTime: st, endTime: et},
        success: function(data) {
            if(data.streams[0].count == 0) {
                $("#plantlevel_comparison_chart").empty();
                $("#no_data_parameter_value").empty();
                $("#no_data_parameter_value").append("<div class='alert alert-warning' id='alert'></div>");
                $("#plantlevel_comparison_chart").css("height", "0px");
                $("#alert").empty();
                $("#alert").append("No data for the Parameter.");

                return;
            } else {
                $("#no_data_parameter_value").empty();
                $("#plantlevel_comparison_chart").empty();
                $("#plantlevel_comparison_chart").append("<svg></svg>");
                $("#plantlevel_comparison_chart").css("height", "255px");

                if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
                  if(data.streams[0].name == "IRRADIATION" || data.streams[0].name == "EXTERNAL_IRRADIATION" || data.streams[0].name == "IRRADIATION1" || data.streams[0].name == "IRRADIATION2") {
                    for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                      arrayValue.push({x:new Date(data.streams[0].timestamps[j]),y:(parseFloat(data.streams[0].values[j]))*1000});
                    }                
                  } else {
                    for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                      arrayValue.push({x:new Date(data.streams[0].timestamps[j]),y:parseFloat(data.streams[0].values[j])});
                    }
                  }
                } else {
                    for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                      arrayValue.push({x:new Date(data.streams[0].timestamps[j]),
                                       y:parseFloat(data.streams[0].values[j])});
                    }
                }

                packagedData.push(arrayValue);

                parameter_chart(packagedData, fields);
            }
        },
        error: function(data) {
          console.log("error_streams_data");
          data = null;
        }
    });

}*/
function plant_power_backup() {

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    var fields = [];

    var arrayData = [];
    var arrayValue = [];

    var powerValue = [];

    $.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: st, endTime: et},
        success: function(power) {
            
            for (var n = power.length-1; n > 0; n--) {
                var date = new Date(power[n].timestamp);
                var timestamp = date.getTime();
                arrayData.push([timestamp, parseFloat(power[n].power)]);
            }
            
            var packagedData = [{
                    "key": "TOTAL PLANT POWER",
                    "values": arrayData,
                    "bar": true,
                    "color": "#CCCCFF"
                }, {
                    "key": fields,
                    "values": arrayValue,
                    "color": "#4C85AB"
                }
            ];
            
            multiple_line_charts(packagedData, fields);

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        },
    });
}
/*
function parameter_chart(data, fields) {

  color = ["#ff7f0e","#7777ff","#2ca02c","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700"];

  nv.addGraph(function() {
    var chart = nv.models.lineChart()
                  .margin({left: 90, right: 50, bottom:110})  //Adjust chart margins to give the x-axis some breathing room.
                  .useInteractiveGuideline(true)  //We want nice looking tooltips   and a guideline!
                  .showYAxis(true)        //Show the y-axis
                  .showXAxis(true)        //Show the x-axis
    ;
      chart.xAxis     //Chart x-axis settings
        .axisLabel('')
        .tickFormat(function(ts) { 
          return d3.time.format('%I:%M %p')(new Date(ts)); 
        });

      chart.yAxis     //Chart y-axis settings
        .axisLabel(fields[0])
        .tickFormat(d3.format('.02f'));

      var result = [];

      for(var i = 0; i < data.length; i++) {
        if(data[i] != 0) {
        result.push({
            values: data[0], 
            key: fields[0], 
            color: color[0]  
        });
      
        d3.select('#plantlevel_comparison_chart svg')    //Select the <svg> element you want to render the chart in.   
          .datum(result)         //Populate the <svg> element with chart data...
          .call(chart);    
        }
      }

    //Update the chart when window resizes.
    nv.utils.windowResize(function() { chart.update() });

    $(".nvd3-svg").css("float", "left");

    return chart;
  });
}*/

/*function day_energy_data() {

    var id = 'plant_level_start_time'

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: "FIVE_MINUTES"},
        success: function(data) {
          if(data == '') {
              $("#power_data_id").empty();
              $("#no_data_power_value").empty();
              $("#no_data_power_value").append("<div class='alert alert-warning' style='margin-bottom: 0px;'>No data for the day</div>");
              return;
          } else {
              $("#power_data_id").empty();
              $("#power_data_id").empty();
              $("#power_data_id").append("<svg></svg>");
          }

          var arrayData = [];

          // populate the data array and calculate the day_energy
          for(var n= data.length-1; n >=0 ; n--) {
            var local_values = [];
            var ts = new Date(data[n].timestamp);

            local_values.push([ts, 0.0]);
                    local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].energy)]);
            arrayData.push({"values": local_values,
              "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].energy).toString()),
              "color":"#4C85AB"});
          }

          // plot the chart
          day_line_energy_chart(arrayData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}*/

/*function day_line_energy_chart(data) {
    nv.addGraph(function () {
        live_chart = nv.models.lineChart()
            .x(function (d) { return d[0] })
            .y(function (d) { return d[1] })
            .showYAxis(true)
            .showLegend(false)
            .showXAxis(true)
            .margin({top: 5, right: 44, bottom: 20, left: 65})
            .useInteractiveGuideline(false)
            .clipEdge(true)
            ;

            live_chart.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.point[1] !=  '0') {
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' kWH' + '</p>' ;
                }
            });

        live_chart.interactiveLayer.tooltip
              .headerFormatter(function(d, i) {
                return nv.models.axis().tickFormat()(d, i);
        });
        live_chart.xAxis
              .axisLabel("")
              .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });
        live_chart.yAxis
              .axisLabel("Energy (kWh)")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#power_data_id svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);

        $(".nvd3-svg").css("float", "left");
        
        return live_chart;
    });
}*/

function singlechart_plant_comparison_data() {

  var single_id = "single_plant_level_start_time";

  var dates = get_dates();
  var st = dates[0];
  var et = dates[1];

  if(comparison_select == 0) {
    single_chart_power_parameter(st, et);
  } else if(comparison_select == 1) {
    single_chart_energy_parameter(st, et);
  }

}

/*function singlechart_plant_power_data(st, et) {

  var arrayData = [];
  var comparison_parameter = "POWER";

  $.ajax({
    type: "GET",
    url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
    data: {startTime: st, endTime: et},
    success: function(data) {
      if(data == '') {
          $("#single_no_data_power_value").empty();
          $("#single_no_data_power_value").append("<div class='alert alert-warning'> No power for the date </div>");

          return;
      } else {
          $("#single_no_data_power_value").empty();
          $("#plantlevel_comparison_single_chart").empty();
          $("#plantlevel_comparison_single_chart").append("<svg></svg>");
      }

      // populate the data array and calculate the day_energy
      for(var n= data.length-1; n >=0 ; n--) {
        if(data[n].power > 0) {
          var local_values = [];
          var ts = new Date(data[n].timestamp);

          local_values.push([ts, 0.0]);
                  local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power)]);
          arrayData.push({"values": local_values,
                  "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].power).toString()),
                  "color":"#4C85AB"});
        }
      }

      comparison_parameter_data(arrayData, st, et, comparison_parameter);
    },
    error: function(data) {
        console.log("error_streams_data");
        data = null;
    },
  });
}*/

/*function singlechart_plant_energy_data(st, et) {

  var comparison_parameter = "ENERGY";
  var arrayData = [];

  $.ajax({
    type: "GET",
    url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
    data: {startTime: (st), endTime: (et), aggregator: "FIVE_MINUTES"},
    success: function(data) {
      if(data == '') {
          $("#single_no_data_power_value").empty();
          $("#single_no_data_power_value").append("<div class='alert alert-warning'> No energy for the date </div>");

          $(".plant-power-generation h2").empty();
          return;
      } else {
          $("#single_no_data_power_value").empty();
          $("#plantlevel_comparison_single_chart").empty();
          $("#plantlevel_comparison_single_chart").append("<svg></svg>");
      }

      // populate the data array and calculate the day_energy
      for(var n= data.length-1; n >=0 ; n--) {
        var local_values = [];
        var ts = new Date(data[n].timestamp);

        local_values.push([ts, 0.0]);
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].energy)]);
        arrayData.push({"values": local_values,
          "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].energy).toString()),
          "color":"#4C85AB"});
      }

      comparison_parameter_data(arrayData, st, et, comparison_parameter);
    },
    error: function(data) {
        console.log("error_streams_data");
        data = null;
    },
  });
}*/

/*function comparison_parameter_data(arrayData, st, et, comparison_parameter) {

  var fields = [];
  var parameter = [];

  $('#parameters_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/sources/".concat(sourcekey).concat('/data/'),
    data: {streamNames: fields.join(","), startTime: st, endTime: et},
    success: function(data) {
      parameter = fields;

      if(data.streams[0].count == 0) {
        $("#plantlevel_comparison_single_chart").empty();
        $("#single_no_data_parameter_value").empty();
        $("#single_no_data_parameter_value").append("<div class='alert alert-warning' id='alert'>No data for this parameter.</div>");

        return;
      } else {
        $("#colors_specification").append("<div class='col-md-6'><span class='label label-warning'></span> - " + parameter +"</div>");
        $("#single_no_data_parameter_value").empty();
        $("#plantlevel_comparison_single_chart").empty();

        for(var n= data.streams[0].timestamps.length-1; n >=0 ; n--) {
          var local_values = [];
          var ts = new Date(data.streams[0].timestamps[n]);

          local_values.push([ts, 0.0]);

          if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
            if(data.streams[0].name == "IRRADIATION" || data.streams[0].name == "EXTERNAL_IRRADIATION") {
              local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), (parseFloat(data.streams[0].values[n]))*1000]);
            } else {
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data.streams[0].values[n])]);
            }
          } else {
              local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data.streams[0].values[n])]);
          }

          arrayData.push({"values": local_values,
                      "key": dateFormat(data.streams[0].timestamps[n], 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data.streams[0].timestamps[n]).toString()),
                      "color":"#FF7F0E"});
        }

      }
    },
    error: function(data) {
      console.log("error_streams_data");
      data = null;
    }
  });
  singlechart_data_comparison_chart(arrayData, parameter, comparison_parameter);
}*/

/*function singlechart_data_comparison_chart(data, parameter, comparison_parameter) {

  $("#plantlevel_comparison_single_chart").append("<svg> </svg>");

    nv.addGraph(function () {
        live_chart = nv.models.lineChart()
            .x(function (d) { return d[0] })
            .y(function (d) { return d[1] })
            .showYAxis(true)
            .showLegend(false)
            .showXAxis(true)
            .useInteractiveGuideline(false)
            .margin({top: 5, right: 44, bottom: 20, left: 65})
            .tooltipContent(function(key, y, e, graph) {
                if(key.point[1] !=  '0') {
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + '</p>' ;
                }
            });

        live_chart.interactiveLayer.tooltip
              .headerFormatter(function(d, i) {
                return nv.models.axis().tickFormat()(d, i);
        });

        live_chart.xAxis
            .showMaxMin(true)
            .axisLabel("")
            .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        live_chart.yAxis
              .axisLabel(comparison_parameter+" & "+parameter)
              .tickFormat(d3.format(",.2f"));

        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select("#plantlevel_comparison_single_chart svg")
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);
        return live_chart;
    });

}*/

function single_chart_power_parameter(st, et) {

  var power = {};
  var parameter_choosen = {};

  var timestamps_power = [], power_points = [], timestamps_parameter = [], parameter_value = [];

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
    data: {startTime: st, endTime: et},
    success: function(data) {
      if(data == '') {
          $("#single_no_data_power_value").empty();
          $("#single_no_data_power_value").append("<div class='alert alert-warning'> No power for the date </div>");

          $(".plant-power-generation h2").empty();
          return;
      } else {
          $("#single_no_data_power_value").empty();
      }

      // populate the data array and calculate the day_energy
      for(var n = 0; n < data.length ; n++) {
        if(data[n].power > 0) {
          var date = new Date(data[n].timestamp);
          date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
          var power_value = parseFloat(data[n].power);

          timestamps_power.push(date);
          power_points.push(power_value);
        }
      }

    },
    error: function(data) {
        console.log("error_streams_data");
        data = null;
    },
  });
  
  var fields = [];
  var parameter = [];

  $('#parameters_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/sources/".concat(sourcekey).concat('/data/'),
    data: {streamNames: fields.join(","), startTime: st, endTime: et},
    success: function(data) {
      /*data = {"sourceKey":"O9SkB6yuxo63uBs","streams":[{"name":"IRRADIATION","count":406,"startTime":"2016-10-04T06:04:05.939000+05:30","endTime":"2016-10-04T17:14:42.593000+05:30","values":["0.186904281616","0.191902435303","0.19654737854","0.200232681274","0.108026756287","0.146139343262","0.0897401733398","0.102921974182","0.0709671096802","0.0689278640747","0.0688212356567","0.0727864379883","0.0830159912109","0.166818359375","0.0802969970703","0.0786909255981","0.0791974029541","0.0873543930054","0.0960511779785","0.193141967773","0.103081916809","0.107073768616","0.343972900391","0.353222839355","0.371136199951","0.382778564453","0.384384643555","0.401758239746","0.418498718262","0.414740112305","0.142220779419","0.147118972778","0.186877624512","0.38961605835","0.145859436035","0.139388504028","0.134783538818","0.124727249146","0.120275558472","0.120308883667","0.124980491638","0.132630996704","0.134270385742","0.137422561646","0.141554367065","0.156362228394","0.181013122559","0.573374816895","0.396293579102","0.139528442383","0.139315200806","0.144406646729","0.161840209961","0.181599563599","0.424669769287","0.510851257324","0.206990188599","0.615226013184","0.581411865234","0.708078369141","0.713936218262","0.709991027832","0.29172555542","0.734148742676","0.742885498047","0.729870361328","0.617245300293","0.172629547119","0.149191543579","0.143400344849","0.630547058105","0.144633224487","0.151184143066","0.749343139648","0.590295227051","0.160640640259","0.157988296509","0.172716186523","0.674417480469","0.231714385986","0.226869506836","0.51743548584","0.219618850708","0.794246520996","0.852218444824","0.864453918457","0.235466339111","0.209096084595","0.232527420044","0.216060165405","0.85209185791","0.871078186035","0.231094619751","0.663968017578","0.902179992676","0.90499230957","0.539607299805","0.247135360718","0.88692565918","0.773214294434","0.869412109375","0.91856060791","0.888265136719","0.950302246094","0.96143145752","0.964870178223","0.96361730957","0.959085632324","0.983909790039","1.01776397705","1.0105333252","0.434352844238","0.366617889404","0.311684844971","0.316449737549","0.278650390625","0.305307189941","0.222831008911","0.205144210815","0.201552200317","0.197440383911","0.195527755737","0.20274508667","0.195681030273","0.195074584961","0.195561080933","0.241104248047","1.01726416016","1.02216900635","1.03297839355","1.04733300781","1.0575826416","1.05214465332","0.665794006348","0.253339736938","0.364711914063","1.02678735352","0.505259979248","1.07161071777","1.06751220703","1.06466662598","1.04841931152","1.05023193359","1.06529968262","1.0416151123","0.613959838867","0.466480987549","1.12352490234","0.30430090332","0.362586029053","0.565111206055","0.302468231201","0.240624435425","0.290832550049","1.0944822998","0.321094696045","1.14121166992","1.15713244629","1.2064609375","1.17949755859","1.19400549316","1.20086303711","0.671951721191","0.43348651123","1.23453723145","0.341407196045","0.380559387207","1.17928430176","1.15531311035","0.590641784668","1.13242163086","1.10500500488","1.13663342285","1.12377148437","1.1071776123","1.11774707031","1.10083996582","1.07295019531","1.05962182617","1.0748494873","1.08987060547","1.1104296875","1.1750324707","1.1962779541","0.344845916748","0.330724487305","0.338055084229","1.15125463867","1.1476159668","0.351976623535","0.390895568848","0.297276824951","0.65329864502","0.862714599609","0.981357421875","0.322707427979","0.300249053955","0.300382354736","0.314363861084","0.312504547119","0.703893249512","0.343039916992","0.289199829102","0.289126495361","0.330191345215","0.991460327148","0.498249237061","1.15368041992","0.320135040283","0.906578369141","1.1872746582","1.1836159668","1.2083269043","1.21129907227","1.23732287598","0.353289459229","1.11024316406","0.388123260498","1.15855859375","0.895495788574","0.86470715332","1.14522351074","1.16594921875","0.993459594727","0.37762713623","0.338748168945","0.347871459961","0.484754241943","0.252639984131","0.243936538696","1.0654263916","1.07588244629","1.08749157715","1.07318347168","0.555248168945","0.64176953125","1.06073474121","1.02288873291","1.0084140625","1.00582836914","1.02240893555","0.243556671143","0.967355895996","0.962304443359","0.999650634766","0.322534179688","0.328631896973","0.970794677734","0.937713562012","0.943804626465","0.950568786621","0.93303527832","0.921606140137","0.913182617188","0.938833129883","0.945590637207","0.22447706604","0.231294540405","0.183878723145","0.687272766113","0.924138549805","0.93827331543","0.306400115967","0.269533752441","0.825028503418","0.90764465332","0.489672424316","0.260796966553","0.204764343262","0.340440887451","0.872924133301","0.896248840332","0.43602557373","0.368477203369","0.79888482666","0.777419433594","0.765937011719","0.778239135742","0.807255065918","0.221778060913","0.753348327637","0.743938476563","0.725005432129","0.725798522949","0.726858093262","0.696322753906","0.683540771484","0.673911010742","0.667233459473","0.654804748535","0.646327880859","0.654491516113","0.343113220215","0.650299743652","0.628714355469","0.613533325195","0.618951293945","0.60274395752","0.596959411621","0.591374816895","0.574894287109","0.578512939453","0.583491088867","0.56609753418","0.561739135742","0.555561401367","0.545191894531","0.539927185059","0.5343359375","0.528691345215","0.519034912109","0.510211486816","0.500515075684","0.495623535156","0.487253295898","0.486107055664","0.480329193115","0.465654632568","0.462582427979","0.455951538086","0.448840820312","0.437711608887","0.433926330566","0.429088134766","0.425016296387","0.419498352051","0.416232879639","0.423710113525","0.418465393066","0.424982971191","0.35235647583","0.39977230835","0.350777069092","0.20115234375","0.393048126221","0.373888519287","0.368197296143","0.359927001953","0.355621948242","0.353209503174","0.345265777588","0.339614532471","0.331617462158","0.325113220215","0.321527862549","0.32101473999","0.309232421875","0.295744049072","0.276211273193","0.272006164551","0.277837341309","0.280876220703","0.26485546875","0.216586639404","0.138029006958","0.189070144653","0.208796188354","0.198933166504","0.187504058838","0.174648803711","0.0769582290649","0.159594360352","0.154322982788","0.147225601196","0.140541412354","0.134010482788","0.126379974365","0.117363304138","0.110998985291","0.106347373962","0.10326184845","0.0846287307739","0.0737860717773","0.0832692337036","0.0942984924316","0.0907464752197","0.0811900024414","0.0728730773926","0.0602377433777","0.0524672813416","0.052693862915","0.0508145599365","0.0454098892212","0.0401984825134","0.036599811554","0.0344472732544","0.0313750743866","0.0280163154602","0.0254372673035","0.0226449661255","0.0204524440765","0.0183065700531","0.0166338539124","0.0150077886581","0.0130218553543","0.010609413147","0.00819697189331","0.00639763641357","0.00465161466599","0.00361199879646","0.00307219815254","0.00267234587669","0.00217253065109","0.00182599198818","0.00125287044048","0.000306553393602"],"timestamps":["2016-10-04T17:14:42.593000+05:30","2016-10-04T17:13:03.331000+05:30","2016-10-04T17:11:24.057000+05:30","2016-10-04T17:09:44.674000+05:30","2016-10-04T17:08:05.313000+05:30","2016-10-04T17:06:25.866000+05:30","2016-10-04T17:04:46.432000+05:30","2016-10-04T17:03:07.013000+05:30","2016-10-04T17:01:27.710000+05:30","2016-10-04T16:59:48.211000+05:30","2016-10-04T16:58:08.756000+05:30","2016-10-04T16:56:29.363000+05:30","2016-10-04T16:54:50.011000+05:30","2016-10-04T16:53:10.516000+05:30","2016-10-04T16:51:31.020000+05:30","2016-10-04T16:49:51.672000+05:30","2016-10-04T16:48:12.361000+05:30","2016-10-04T16:46:32.974000+05:30","2016-10-04T16:44:53.716000+05:30","2016-10-04T16:43:14.600000+05:30","2016-10-04T16:41:35.328000+05:30","2016-10-04T16:39:55.892000+05:30","2016-10-04T16:38:16.500000+05:30","2016-10-04T16:36:37.171000+05:30","2016-10-04T16:34:57.872000+05:30","2016-10-04T16:33:18.591000+05:30","2016-10-04T16:31:39.173000+05:30","2016-10-04T16:29:59.881000+05:30","2016-10-04T16:28:20.526000+05:30","2016-10-04T16:26:41.441000+05:30","2016-10-04T16:25:01.937000+05:30","2016-10-04T16:23:22.610000+05:30","2016-10-04T16:21:43.252000+05:30","2016-10-04T16:20:03.788000+05:30","2016-10-04T16:18:24.656000+05:30","2016-10-04T16:16:45.220000+05:30","2016-10-04T16:15:05.921000+05:30","2016-10-04T16:13:26.402000+05:30","2016-10-04T16:11:46.950000+05:30","2016-10-04T16:10:07.380000+05:30","2016-10-04T16:08:27.911000+05:30","2016-10-04T16:06:48.583000+05:30","2016-10-04T16:05:09.336000+05:30","2016-10-04T16:03:29.975000+05:30","2016-10-04T16:01:50.600000+05:30","2016-10-04T16:00:10.919000+05:30","2016-10-04T15:58:31.544000+05:30","2016-10-04T15:56:52.354000+05:30","2016-10-04T15:55:13.098000+05:30","2016-10-04T15:53:33.943000+05:30","2016-10-04T15:51:54.764000+05:30","2016-10-04T15:50:15.444000+05:30","2016-10-04T15:48:36.129000+05:30","2016-10-04T15:46:56.766000+05:30","2016-10-04T15:45:17.257000+05:30","2016-10-04T15:43:37.887000+05:30","2016-10-04T15:41:58.738000+05:30","2016-10-04T15:40:19.735000+05:30","2016-10-04T15:38:40.576000+05:30","2016-10-04T15:37:01.214000+05:30","2016-10-04T15:35:21.732000+05:30","2016-10-04T15:33:42.273000+05:30","2016-10-04T15:32:03.043000+05:30","2016-10-04T15:30:23.665000+05:30","2016-10-04T15:28:44.078000+05:30","2016-10-04T15:27:04.851000+05:30","2016-10-04T15:25:25.557000+05:30","2016-10-04T15:23:46.042000+05:30","2016-10-04T15:22:06.690000+05:30","2016-10-04T15:20:27.366000+05:30","2016-10-04T15:18:48.128000+05:30","2016-10-04T15:17:08.978000+05:30","2016-10-04T15:15:29.486000+05:30","2016-10-04T15:13:50.211000+05:30","2016-10-04T15:12:10.736000+05:30","2016-10-04T15:10:31.301000+05:30","2016-10-04T15:08:51.928000+05:30","2016-10-04T15:07:12.527000+05:30","2016-10-04T15:05:33.119000+05:30","2016-10-04T15:03:53.659000+05:30","2016-10-04T15:02:14.386000+05:30","2016-10-04T15:00:35.095000+05:30","2016-10-04T14:58:55.698000+05:30","2016-10-04T14:57:16.111000+05:30","2016-10-04T14:55:36.757000+05:30","2016-10-04T14:53:57.235000+05:30","2016-10-04T14:52:17.953000+05:30","2016-10-04T14:50:38.527000+05:30","2016-10-04T14:48:59.385000+05:30","2016-10-04T14:47:19.993000+05:30","2016-10-04T14:45:40.424000+05:30","2016-10-04T14:44:01.061000+05:30","2016-10-04T14:42:21.461000+05:30","2016-10-04T14:40:41.991000+05:30","2016-10-04T14:39:02.629000+05:30","2016-10-04T14:37:23.300000+05:30","2016-10-04T14:35:43.759000+05:30","2016-10-04T14:34:04.206000+05:30","2016-10-04T14:32:24.978000+05:30","2016-10-04T14:30:45.493000+05:30","2016-10-04T14:29:06.172000+05:30","2016-10-04T14:27:26.708000+05:30","2016-10-04T14:25:47.194000+05:30","2016-10-04T14:24:07.902000+05:30","2016-10-04T14:22:28.557000+05:30","2016-10-04T14:20:49.242000+05:30","2016-10-04T14:19:09.710000+05:30","2016-10-04T14:17:30.144000+05:30","2016-10-04T14:15:50.815000+05:30","2016-10-04T14:14:11.442000+05:30","2016-10-04T14:12:31.986000+05:30","2016-10-04T14:10:52.541000+05:30","2016-10-04T14:09:13.080000+05:30","2016-10-04T14:07:33.532000+05:30","2016-10-04T14:05:54.084000+05:30","2016-10-04T14:04:14.614000+05:30","2016-10-04T14:02:35.091000+05:30","2016-10-04T14:00:55.675000+05:30","2016-10-04T13:59:16.105000+05:30","2016-10-04T13:57:36.649000+05:30","2016-10-04T13:55:57.352000+05:30","2016-10-04T13:54:17.952000+05:30","2016-10-04T13:52:38.555000+05:30","2016-10-04T13:50:59.283000+05:30","2016-10-04T13:49:19.790000+05:30","2016-10-04T13:47:40.506000+05:30","2016-10-04T13:46:01.025000+05:30","2016-10-04T13:44:21.715000+05:30","2016-10-04T13:42:42.522000+05:30","2016-10-04T13:41:02.852000+05:30","2016-10-04T13:39:23.469000+05:30","2016-10-04T13:37:44.132000+05:30","2016-10-04T13:36:04.946000+05:30","2016-10-04T13:34:25.808000+05:30","2016-10-04T13:32:46.449000+05:30","2016-10-04T13:31:07.038000+05:30","2016-10-04T13:29:27.707000+05:30","2016-10-04T13:27:48.385000+05:30","2016-10-04T13:26:09.315000+05:30","2016-10-04T13:24:30.180000+05:30","2016-10-04T13:22:51.126000+05:30","2016-10-04T13:21:11.687000+05:30","2016-10-04T13:19:32.324000+05:30","2016-10-04T13:17:53.286000+05:30","2016-10-04T13:16:14.356000+05:30","2016-10-04T13:14:35.104000+05:30","2016-10-04T13:12:55.695000+05:30","2016-10-04T13:11:16.266000+05:30","2016-10-04T13:09:37.032000+05:30","2016-10-04T13:07:57.863000+05:30","2016-10-04T13:06:18.446000+05:30","2016-10-04T13:04:39.371000+05:30","2016-10-04T13:02:59.973000+05:30","2016-10-04T13:01:20.721000+05:30","2016-10-04T12:59:41.075000+05:30","2016-10-04T12:58:01.805000+05:30","2016-10-04T12:56:22.469000+05:30","2016-10-04T12:54:43.086000+05:30","2016-10-04T12:53:03.889000+05:30","2016-10-04T12:51:24.599000+05:30","2016-10-04T12:49:45.415000+05:30","2016-10-04T12:48:06.220000+05:30","2016-10-04T12:46:26.920000+05:30","2016-10-04T12:44:47.533000+05:30","2016-10-04T12:43:08.011000+05:30","2016-10-04T12:41:28.365000+05:30","2016-10-04T12:39:49.249000+05:30","2016-10-04T12:38:09.972000+05:30","2016-10-04T12:36:30.598000+05:30","2016-10-04T12:34:51.108000+05:30","2016-10-04T12:33:11.604000+05:30","2016-10-04T12:31:32.144000+05:30","2016-10-04T12:29:52.563000+05:30","2016-10-04T12:28:13.268000+05:30","2016-10-04T12:26:34.085000+05:30","2016-10-04T12:24:54.568000+05:30","2016-10-04T12:23:15.121000+05:30","2016-10-04T12:21:35.834000+05:30","2016-10-04T12:19:56.524000+05:30","2016-10-04T12:18:16.935000+05:30","2016-10-04T12:16:37.409000+05:30","2016-10-04T12:14:58.123000+05:30","2016-10-04T12:13:18.591000+05:30","2016-10-04T12:11:39.106000+05:30","2016-10-04T12:09:59.847000+05:30","2016-10-04T12:08:20.392000+05:30","2016-10-04T12:06:40.964000+05:30","2016-10-04T12:05:01.692000+05:30","2016-10-04T12:03:22.290000+05:30","2016-10-04T12:01:42.885000+05:30","2016-10-04T12:00:03.549000+05:30","2016-10-04T11:58:24.385000+05:30","2016-10-04T11:56:45.120000+05:30","2016-10-04T11:55:05.785000+05:30","2016-10-04T11:53:26.524000+05:30","2016-10-04T11:51:47.073000+05:30","2016-10-04T11:50:07.805000+05:30","2016-10-04T11:48:28.558000+05:30","2016-10-04T11:46:49.270000+05:30","2016-10-04T11:45:09.818000+05:30","2016-10-04T11:43:30.472000+05:30","2016-10-04T11:41:51.294000+05:30","2016-10-04T11:40:12.065000+05:30","2016-10-04T11:38:32.785000+05:30","2016-10-04T11:36:53.576000+05:30","2016-10-04T11:35:14.034000+05:30","2016-10-04T11:33:34.689000+05:30","2016-10-04T11:31:55.315000+05:30","2016-10-04T11:30:15.723000+05:30","2016-10-04T11:28:36.308000+05:30","2016-10-04T11:26:56.970000+05:30","2016-10-04T11:25:17.556000+05:30","2016-10-04T11:23:38.171000+05:30","2016-10-04T11:21:58.941000+05:30","2016-10-04T11:20:19.719000+05:30","2016-10-04T11:18:40.447000+05:30","2016-10-04T11:17:01.190000+05:30","2016-10-04T11:15:21.807000+05:30","2016-10-04T11:13:42.482000+05:30","2016-10-04T11:12:03.156000+05:30","2016-10-04T11:10:23.821000+05:30","2016-10-04T11:08:44.391000+05:30","2016-10-04T11:07:04.939000+05:30","2016-10-04T11:05:25.463000+05:30","2016-10-04T11:03:46.097000+05:30","2016-10-04T11:02:06.808000+05:30","2016-10-04T11:00:27.285000+05:30","2016-10-04T10:58:47.893000+05:30","2016-10-04T10:57:08.367000+05:30","2016-10-04T10:55:28.941000+05:30","2016-10-04T10:53:49.766000+05:30","2016-10-04T10:52:10.651000+05:30","2016-10-04T10:50:31.275000+05:30","2016-10-04T10:48:52.101000+05:30","2016-10-04T10:47:12.805000+05:30","2016-10-04T10:45:33.253000+05:30","2016-10-04T10:43:53.915000+05:30","2016-10-04T10:42:14.526000+05:30","2016-10-04T10:40:35.123000+05:30","2016-10-04T10:38:55.763000+05:30","2016-10-04T10:37:16.505000+05:30","2016-10-04T10:35:36.991000+05:30","2016-10-04T10:33:57.701000+05:30","2016-10-04T10:32:18.532000+05:30","2016-10-04T10:30:39.192000+05:30","2016-10-04T10:28:59.590000+05:30","2016-10-04T10:27:20.340000+05:30","2016-10-04T10:25:41.259000+05:30","2016-10-04T10:24:01.797000+05:30","2016-10-04T10:22:22.582000+05:30","2016-10-04T10:20:43.278000+05:30","2016-10-04T10:19:03.902000+05:30","2016-10-04T10:17:24.520000+05:30","2016-10-04T10:15:45.378000+05:30","2016-10-04T10:14:05.884000+05:30","2016-10-04T10:12:26.431000+05:30","2016-10-04T10:10:46.931000+05:30","2016-10-04T10:09:07.297000+05:30","2016-10-04T10:07:27.895000+05:30","2016-10-04T10:05:48.415000+05:30","2016-10-04T10:04:09.096000+05:30","2016-10-04T10:02:29.641000+05:30","2016-10-04T10:00:50.389000+05:30","2016-10-04T09:59:11.180000+05:30","2016-10-04T09:57:31.938000+05:30","2016-10-04T09:55:52.739000+05:30","2016-10-04T09:54:13.442000+05:30","2016-10-04T09:52:34.102000+05:30","2016-10-04T09:50:54.929000+05:30","2016-10-04T09:49:15.420000+05:30","2016-10-04T09:47:36.009000+05:30","2016-10-04T09:45:56.631000+05:30","2016-10-04T09:44:17.211000+05:30","2016-10-04T09:42:37.796000+05:30","2016-10-04T09:40:58.340000+05:30","2016-10-04T09:39:19.044000+05:30","2016-10-04T09:37:39.701000+05:30","2016-10-04T09:36:00.409000+05:30","2016-10-04T09:34:21.258000+05:30","2016-10-04T09:32:41.880000+05:30","2016-10-04T09:31:02.607000+05:30","2016-10-04T09:29:23.219000+05:30","2016-10-04T09:27:43.847000+05:30","2016-10-04T09:26:04.762000+05:30","2016-10-04T09:24:25.664000+05:30","2016-10-04T09:22:46.467000+05:30","2016-10-04T09:21:07.019000+05:30","2016-10-04T09:19:27.596000+05:30","2016-10-04T09:17:48.424000+05:30","2016-10-04T09:16:09.047000+05:30","2016-10-04T09:14:29.518000+05:30","2016-10-04T09:12:50.291000+05:30","2016-10-04T09:11:10.989000+05:30","2016-10-04T09:09:31.545000+05:30","2016-10-04T09:07:52.288000+05:30","2016-10-04T09:06:13.348000+05:30","2016-10-04T09:04:33.995000+05:30","2016-10-04T09:02:54.460000+05:30","2016-10-04T09:01:15.228000+05:30","2016-10-04T08:59:35.656000+05:30","2016-10-04T08:57:56.285000+05:30","2016-10-04T08:56:16.889000+05:30","2016-10-04T08:54:37.594000+05:30","2016-10-04T08:52:58.323000+05:30","2016-10-04T08:51:18.771000+05:30","2016-10-04T08:49:39.166000+05:30","2016-10-04T08:47:59.744000+05:30","2016-10-04T08:46:20.420000+05:30","2016-10-04T08:44:41.191000+05:30","2016-10-04T08:43:01.962000+05:30","2016-10-04T08:41:22.770000+05:30","2016-10-04T08:39:43.354000+05:30","2016-10-04T08:38:03.951000+05:30","2016-10-04T08:36:24.566000+05:30","2016-10-04T08:34:45.330000+05:30","2016-10-04T08:33:05.964000+05:30","2016-10-04T08:31:26.535000+05:30","2016-10-04T08:29:47.255000+05:30","2016-10-04T08:28:07.964000+05:30","2016-10-04T08:26:28.784000+05:30","2016-10-04T08:24:49.573000+05:30","2016-10-04T08:23:10.220000+05:30","2016-10-04T08:21:30.875000+05:30","2016-10-04T08:19:51.571000+05:30","2016-10-04T08:18:12.309000+05:30","2016-10-04T08:16:32.748000+05:30","2016-10-04T08:14:53.352000+05:30","2016-10-04T08:13:13.879000+05:30","2016-10-04T08:11:34.623000+05:30","2016-10-04T08:09:55.225000+05:30","2016-10-04T08:08:15.875000+05:30","2016-10-04T08:06:36.685000+05:30","2016-10-04T08:04:57.423000+05:30","2016-10-04T08:03:18.262000+05:30","2016-10-04T08:01:39.092000+05:30","2016-10-04T07:59:59.522000+05:30","2016-10-04T07:58:20.233000+05:30","2016-10-04T07:56:40.901000+05:30","2016-10-04T07:55:01.429000+05:30","2016-10-04T07:53:22.060000+05:30","2016-10-04T07:51:42.721000+05:30","2016-10-04T07:50:03.343000+05:30","2016-10-04T07:48:23.735000+05:30","2016-10-04T07:46:44.449000+05:30","2016-10-04T07:45:04.945000+05:30","2016-10-04T07:43:25.702000+05:30","2016-10-04T07:41:46.431000+05:30","2016-10-04T07:40:06.934000+05:30","2016-10-04T07:38:27.347000+05:30","2016-10-04T07:36:48.020000+05:30","2016-10-04T07:35:08.641000+05:30","2016-10-04T07:33:29.191000+05:30","2016-10-04T07:31:49.834000+05:30","2016-10-04T07:30:10.339000+05:30","2016-10-04T07:28:30.987000+05:30","2016-10-04T07:26:51.538000+05:30","2016-10-04T07:25:12.507000+05:30","2016-10-04T07:23:33.453000+05:30","2016-10-04T07:21:54.181000+05:30","2016-10-04T07:20:14.872000+05:30","2016-10-04T07:18:35.614000+05:30","2016-10-04T07:16:56.228000+05:30","2016-10-04T07:15:17.196000+05:30","2016-10-04T07:13:37.998000+05:30","2016-10-04T07:11:58.504000+05:30","2016-10-04T07:10:19.249000+05:30","2016-10-04T07:08:39.899000+05:30","2016-10-04T07:07:00.552000+05:30","2016-10-04T07:05:21.371000+05:30","2016-10-04T07:03:42.181000+05:30","2016-10-04T07:02:03.018000+05:30","2016-10-04T07:00:23.457000+05:30","2016-10-04T06:58:44.197000+05:30","2016-10-04T06:57:04.831000+05:30","2016-10-04T06:55:25.403000+05:30","2016-10-04T06:53:46.133000+05:30","2016-10-04T06:52:06.850000+05:30","2016-10-04T06:50:27.259000+05:30","2016-10-04T06:48:47.921000+05:30","2016-10-04T06:47:08.570000+05:30","2016-10-04T06:45:29.137000+05:30","2016-10-04T06:43:49.638000+05:30","2016-10-04T06:42:10.106000+05:30","2016-10-04T06:40:30.555000+05:30","2016-10-04T06:38:51.285000+05:30","2016-10-04T06:37:11.864000+05:30","2016-10-04T06:35:32.523000+05:30","2016-10-04T06:33:53.232000+05:30","2016-10-04T06:32:13.886000+05:30","2016-10-04T06:30:34.533000+05:30","2016-10-04T06:28:55.064000+05:30","2016-10-04T06:27:15.432000+05:30","2016-10-04T06:25:36.243000+05:30","2016-10-04T06:23:57.062000+05:30","2016-10-04T06:22:17.820000+05:30","2016-10-04T06:20:38.652000+05:30","2016-10-04T06:18:59.126000+05:30","2016-10-04T06:17:19.955000+05:30","2016-10-04T06:15:40.685000+05:30","2016-10-04T06:14:01.370000+05:30","2016-10-04T06:12:22.250000+05:30","2016-10-04T06:10:43.074000+05:30","2016-10-04T06:09:03.670000+05:30","2016-10-04T06:07:24.490000+05:30","2016-10-04T06:05:45.070000+05:30","2016-10-04T06:04:05.939000+05:30"]}]};
      console.log(data);*/

      parameter = fields;

      if(data.streams[0].count == 0) {
        $("#single_no_data_parameter_value").empty();
        $("#single_no_data_parameter_value").append("<div class='alert alert-warning' id='alert'>No data for this parameter.</div>");

        return;
      } else {
        $("#single_no_data_parameter_value").empty();

        var parameter = null;

        for(var n = data.streams[0].timestamps.length-1; n >=0 ; n--) {
          var date = new Date(data.streams[0].timestamps[n]);
          date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
          if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
            if(data.streams[0].name == "IRRADIATION" || data.streams[0].name == "EXTERNAL_IRRADIATION") {
              parameter = parseFloat((data.streams[0].values[n])*1000);
            } else {
                parameter = parseFloat(data.streams[0].values[n]);
            }
          } else {
              parameter = parseFloat(data.streams[0].values[n]);
          }
          timestamps_parameter.push(date);
          parameter_value.push(parameter);
        }
      }
    },
    error: function(data) {
      console.log("error_streams_data");
      data = null;
    }
  });
  
  var name1 = 'POWER';
  var name2 = fields[0];
  var title_dual_axis_chart = 'FOR DATE ' + dateFormat(st, "dd-mm-yyyy");
  var width = 1030;
  var height = 400;
  var div_name = 'single_chart_dual_axis';
  var page = 0;

  dual_axis_chart_plotly(timestamps_power, power_points, timestamps_parameter, parameter_value, name1, name2, title_dual_axis_chart, width, height, div_name, page);
}

function single_chart_energy_parameter(st, et) {

  var timestamps_energy = [], energy_points = [], timestamps_parameter = [], parameter_value = [];

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
    data: {startTime: (st), endTime: (et), aggregator: "FIVE_MINUTES"},
    success: function(data) {
      if(data == '') {
          $("#single_no_data_power_value").empty();
          $("#single_no_data_power_value").append("<div class='alert alert-warning'> No power for the date </div>");

          $(".plant-power-generation h2").empty();
          return;
      } else {
          $("#single_no_data_power_value").empty();
      }
      
      // populate the data array and calculate the day_energy
      for(var n = 0; n < data.length ; n++) {
        var date = new Date(data[n].timestamp);
        date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
        var energy_value = parseFloat(data[n].energy);
        timestamps_energy.push(date);
        energy_points.push(energy_value);
      }

    },
    error: function(data) {
        console.log("error_streams_data");
        data = null;
    },
  });
  
  var fields = [];
  var parameter = [];

  $('#parameters_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/sources/".concat(sourcekey).concat('/data/'),
    data: {streamNames: fields.join(","), startTime: st, endTime: et},
    success: function(data) {
      /*data = {"sourceKey":"O9SkB6yuxo63uBs","streams":[{"name":"IRRADIATION","count":406,"startTime":"2016-10-04T06:04:05.939000+05:30","endTime":"2016-10-04T17:14:42.593000+05:30","values":["0.186904281616","0.191902435303","0.19654737854","0.200232681274","0.108026756287","0.146139343262","0.0897401733398","0.102921974182","0.0709671096802","0.0689278640747","0.0688212356567","0.0727864379883","0.0830159912109","0.166818359375","0.0802969970703","0.0786909255981","0.0791974029541","0.0873543930054","0.0960511779785","0.193141967773","0.103081916809","0.107073768616","0.343972900391","0.353222839355","0.371136199951","0.382778564453","0.384384643555","0.401758239746","0.418498718262","0.414740112305","0.142220779419","0.147118972778","0.186877624512","0.38961605835","0.145859436035","0.139388504028","0.134783538818","0.124727249146","0.120275558472","0.120308883667","0.124980491638","0.132630996704","0.134270385742","0.137422561646","0.141554367065","0.156362228394","0.181013122559","0.573374816895","0.396293579102","0.139528442383","0.139315200806","0.144406646729","0.161840209961","0.181599563599","0.424669769287","0.510851257324","0.206990188599","0.615226013184","0.581411865234","0.708078369141","0.713936218262","0.709991027832","0.29172555542","0.734148742676","0.742885498047","0.729870361328","0.617245300293","0.172629547119","0.149191543579","0.143400344849","0.630547058105","0.144633224487","0.151184143066","0.749343139648","0.590295227051","0.160640640259","0.157988296509","0.172716186523","0.674417480469","0.231714385986","0.226869506836","0.51743548584","0.219618850708","0.794246520996","0.852218444824","0.864453918457","0.235466339111","0.209096084595","0.232527420044","0.216060165405","0.85209185791","0.871078186035","0.231094619751","0.663968017578","0.902179992676","0.90499230957","0.539607299805","0.247135360718","0.88692565918","0.773214294434","0.869412109375","0.91856060791","0.888265136719","0.950302246094","0.96143145752","0.964870178223","0.96361730957","0.959085632324","0.983909790039","1.01776397705","1.0105333252","0.434352844238","0.366617889404","0.311684844971","0.316449737549","0.278650390625","0.305307189941","0.222831008911","0.205144210815","0.201552200317","0.197440383911","0.195527755737","0.20274508667","0.195681030273","0.195074584961","0.195561080933","0.241104248047","1.01726416016","1.02216900635","1.03297839355","1.04733300781","1.0575826416","1.05214465332","0.665794006348","0.253339736938","0.364711914063","1.02678735352","0.505259979248","1.07161071777","1.06751220703","1.06466662598","1.04841931152","1.05023193359","1.06529968262","1.0416151123","0.613959838867","0.466480987549","1.12352490234","0.30430090332","0.362586029053","0.565111206055","0.302468231201","0.240624435425","0.290832550049","1.0944822998","0.321094696045","1.14121166992","1.15713244629","1.2064609375","1.17949755859","1.19400549316","1.20086303711","0.671951721191","0.43348651123","1.23453723145","0.341407196045","0.380559387207","1.17928430176","1.15531311035","0.590641784668","1.13242163086","1.10500500488","1.13663342285","1.12377148437","1.1071776123","1.11774707031","1.10083996582","1.07295019531","1.05962182617","1.0748494873","1.08987060547","1.1104296875","1.1750324707","1.1962779541","0.344845916748","0.330724487305","0.338055084229","1.15125463867","1.1476159668","0.351976623535","0.390895568848","0.297276824951","0.65329864502","0.862714599609","0.981357421875","0.322707427979","0.300249053955","0.300382354736","0.314363861084","0.312504547119","0.703893249512","0.343039916992","0.289199829102","0.289126495361","0.330191345215","0.991460327148","0.498249237061","1.15368041992","0.320135040283","0.906578369141","1.1872746582","1.1836159668","1.2083269043","1.21129907227","1.23732287598","0.353289459229","1.11024316406","0.388123260498","1.15855859375","0.895495788574","0.86470715332","1.14522351074","1.16594921875","0.993459594727","0.37762713623","0.338748168945","0.347871459961","0.484754241943","0.252639984131","0.243936538696","1.0654263916","1.07588244629","1.08749157715","1.07318347168","0.555248168945","0.64176953125","1.06073474121","1.02288873291","1.0084140625","1.00582836914","1.02240893555","0.243556671143","0.967355895996","0.962304443359","0.999650634766","0.322534179688","0.328631896973","0.970794677734","0.937713562012","0.943804626465","0.950568786621","0.93303527832","0.921606140137","0.913182617188","0.938833129883","0.945590637207","0.22447706604","0.231294540405","0.183878723145","0.687272766113","0.924138549805","0.93827331543","0.306400115967","0.269533752441","0.825028503418","0.90764465332","0.489672424316","0.260796966553","0.204764343262","0.340440887451","0.872924133301","0.896248840332","0.43602557373","0.368477203369","0.79888482666","0.777419433594","0.765937011719","0.778239135742","0.807255065918","0.221778060913","0.753348327637","0.743938476563","0.725005432129","0.725798522949","0.726858093262","0.696322753906","0.683540771484","0.673911010742","0.667233459473","0.654804748535","0.646327880859","0.654491516113","0.343113220215","0.650299743652","0.628714355469","0.613533325195","0.618951293945","0.60274395752","0.596959411621","0.591374816895","0.574894287109","0.578512939453","0.583491088867","0.56609753418","0.561739135742","0.555561401367","0.545191894531","0.539927185059","0.5343359375","0.528691345215","0.519034912109","0.510211486816","0.500515075684","0.495623535156","0.487253295898","0.486107055664","0.480329193115","0.465654632568","0.462582427979","0.455951538086","0.448840820312","0.437711608887","0.433926330566","0.429088134766","0.425016296387","0.419498352051","0.416232879639","0.423710113525","0.418465393066","0.424982971191","0.35235647583","0.39977230835","0.350777069092","0.20115234375","0.393048126221","0.373888519287","0.368197296143","0.359927001953","0.355621948242","0.353209503174","0.345265777588","0.339614532471","0.331617462158","0.325113220215","0.321527862549","0.32101473999","0.309232421875","0.295744049072","0.276211273193","0.272006164551","0.277837341309","0.280876220703","0.26485546875","0.216586639404","0.138029006958","0.189070144653","0.208796188354","0.198933166504","0.187504058838","0.174648803711","0.0769582290649","0.159594360352","0.154322982788","0.147225601196","0.140541412354","0.134010482788","0.126379974365","0.117363304138","0.110998985291","0.106347373962","0.10326184845","0.0846287307739","0.0737860717773","0.0832692337036","0.0942984924316","0.0907464752197","0.0811900024414","0.0728730773926","0.0602377433777","0.0524672813416","0.052693862915","0.0508145599365","0.0454098892212","0.0401984825134","0.036599811554","0.0344472732544","0.0313750743866","0.0280163154602","0.0254372673035","0.0226449661255","0.0204524440765","0.0183065700531","0.0166338539124","0.0150077886581","0.0130218553543","0.010609413147","0.00819697189331","0.00639763641357","0.00465161466599","0.00361199879646","0.00307219815254","0.00267234587669","0.00217253065109","0.00182599198818","0.00125287044048","0.000306553393602"],"timestamps":["2016-10-04T17:14:42.593000+05:30","2016-10-04T17:13:03.331000+05:30","2016-10-04T17:11:24.057000+05:30","2016-10-04T17:09:44.674000+05:30","2016-10-04T17:08:05.313000+05:30","2016-10-04T17:06:25.866000+05:30","2016-10-04T17:04:46.432000+05:30","2016-10-04T17:03:07.013000+05:30","2016-10-04T17:01:27.710000+05:30","2016-10-04T16:59:48.211000+05:30","2016-10-04T16:58:08.756000+05:30","2016-10-04T16:56:29.363000+05:30","2016-10-04T16:54:50.011000+05:30","2016-10-04T16:53:10.516000+05:30","2016-10-04T16:51:31.020000+05:30","2016-10-04T16:49:51.672000+05:30","2016-10-04T16:48:12.361000+05:30","2016-10-04T16:46:32.974000+05:30","2016-10-04T16:44:53.716000+05:30","2016-10-04T16:43:14.600000+05:30","2016-10-04T16:41:35.328000+05:30","2016-10-04T16:39:55.892000+05:30","2016-10-04T16:38:16.500000+05:30","2016-10-04T16:36:37.171000+05:30","2016-10-04T16:34:57.872000+05:30","2016-10-04T16:33:18.591000+05:30","2016-10-04T16:31:39.173000+05:30","2016-10-04T16:29:59.881000+05:30","2016-10-04T16:28:20.526000+05:30","2016-10-04T16:26:41.441000+05:30","2016-10-04T16:25:01.937000+05:30","2016-10-04T16:23:22.610000+05:30","2016-10-04T16:21:43.252000+05:30","2016-10-04T16:20:03.788000+05:30","2016-10-04T16:18:24.656000+05:30","2016-10-04T16:16:45.220000+05:30","2016-10-04T16:15:05.921000+05:30","2016-10-04T16:13:26.402000+05:30","2016-10-04T16:11:46.950000+05:30","2016-10-04T16:10:07.380000+05:30","2016-10-04T16:08:27.911000+05:30","2016-10-04T16:06:48.583000+05:30","2016-10-04T16:05:09.336000+05:30","2016-10-04T16:03:29.975000+05:30","2016-10-04T16:01:50.600000+05:30","2016-10-04T16:00:10.919000+05:30","2016-10-04T15:58:31.544000+05:30","2016-10-04T15:56:52.354000+05:30","2016-10-04T15:55:13.098000+05:30","2016-10-04T15:53:33.943000+05:30","2016-10-04T15:51:54.764000+05:30","2016-10-04T15:50:15.444000+05:30","2016-10-04T15:48:36.129000+05:30","2016-10-04T15:46:56.766000+05:30","2016-10-04T15:45:17.257000+05:30","2016-10-04T15:43:37.887000+05:30","2016-10-04T15:41:58.738000+05:30","2016-10-04T15:40:19.735000+05:30","2016-10-04T15:38:40.576000+05:30","2016-10-04T15:37:01.214000+05:30","2016-10-04T15:35:21.732000+05:30","2016-10-04T15:33:42.273000+05:30","2016-10-04T15:32:03.043000+05:30","2016-10-04T15:30:23.665000+05:30","2016-10-04T15:28:44.078000+05:30","2016-10-04T15:27:04.851000+05:30","2016-10-04T15:25:25.557000+05:30","2016-10-04T15:23:46.042000+05:30","2016-10-04T15:22:06.690000+05:30","2016-10-04T15:20:27.366000+05:30","2016-10-04T15:18:48.128000+05:30","2016-10-04T15:17:08.978000+05:30","2016-10-04T15:15:29.486000+05:30","2016-10-04T15:13:50.211000+05:30","2016-10-04T15:12:10.736000+05:30","2016-10-04T15:10:31.301000+05:30","2016-10-04T15:08:51.928000+05:30","2016-10-04T15:07:12.527000+05:30","2016-10-04T15:05:33.119000+05:30","2016-10-04T15:03:53.659000+05:30","2016-10-04T15:02:14.386000+05:30","2016-10-04T15:00:35.095000+05:30","2016-10-04T14:58:55.698000+05:30","2016-10-04T14:57:16.111000+05:30","2016-10-04T14:55:36.757000+05:30","2016-10-04T14:53:57.235000+05:30","2016-10-04T14:52:17.953000+05:30","2016-10-04T14:50:38.527000+05:30","2016-10-04T14:48:59.385000+05:30","2016-10-04T14:47:19.993000+05:30","2016-10-04T14:45:40.424000+05:30","2016-10-04T14:44:01.061000+05:30","2016-10-04T14:42:21.461000+05:30","2016-10-04T14:40:41.991000+05:30","2016-10-04T14:39:02.629000+05:30","2016-10-04T14:37:23.300000+05:30","2016-10-04T14:35:43.759000+05:30","2016-10-04T14:34:04.206000+05:30","2016-10-04T14:32:24.978000+05:30","2016-10-04T14:30:45.493000+05:30","2016-10-04T14:29:06.172000+05:30","2016-10-04T14:27:26.708000+05:30","2016-10-04T14:25:47.194000+05:30","2016-10-04T14:24:07.902000+05:30","2016-10-04T14:22:28.557000+05:30","2016-10-04T14:20:49.242000+05:30","2016-10-04T14:19:09.710000+05:30","2016-10-04T14:17:30.144000+05:30","2016-10-04T14:15:50.815000+05:30","2016-10-04T14:14:11.442000+05:30","2016-10-04T14:12:31.986000+05:30","2016-10-04T14:10:52.541000+05:30","2016-10-04T14:09:13.080000+05:30","2016-10-04T14:07:33.532000+05:30","2016-10-04T14:05:54.084000+05:30","2016-10-04T14:04:14.614000+05:30","2016-10-04T14:02:35.091000+05:30","2016-10-04T14:00:55.675000+05:30","2016-10-04T13:59:16.105000+05:30","2016-10-04T13:57:36.649000+05:30","2016-10-04T13:55:57.352000+05:30","2016-10-04T13:54:17.952000+05:30","2016-10-04T13:52:38.555000+05:30","2016-10-04T13:50:59.283000+05:30","2016-10-04T13:49:19.790000+05:30","2016-10-04T13:47:40.506000+05:30","2016-10-04T13:46:01.025000+05:30","2016-10-04T13:44:21.715000+05:30","2016-10-04T13:42:42.522000+05:30","2016-10-04T13:41:02.852000+05:30","2016-10-04T13:39:23.469000+05:30","2016-10-04T13:37:44.132000+05:30","2016-10-04T13:36:04.946000+05:30","2016-10-04T13:34:25.808000+05:30","2016-10-04T13:32:46.449000+05:30","2016-10-04T13:31:07.038000+05:30","2016-10-04T13:29:27.707000+05:30","2016-10-04T13:27:48.385000+05:30","2016-10-04T13:26:09.315000+05:30","2016-10-04T13:24:30.180000+05:30","2016-10-04T13:22:51.126000+05:30","2016-10-04T13:21:11.687000+05:30","2016-10-04T13:19:32.324000+05:30","2016-10-04T13:17:53.286000+05:30","2016-10-04T13:16:14.356000+05:30","2016-10-04T13:14:35.104000+05:30","2016-10-04T13:12:55.695000+05:30","2016-10-04T13:11:16.266000+05:30","2016-10-04T13:09:37.032000+05:30","2016-10-04T13:07:57.863000+05:30","2016-10-04T13:06:18.446000+05:30","2016-10-04T13:04:39.371000+05:30","2016-10-04T13:02:59.973000+05:30","2016-10-04T13:01:20.721000+05:30","2016-10-04T12:59:41.075000+05:30","2016-10-04T12:58:01.805000+05:30","2016-10-04T12:56:22.469000+05:30","2016-10-04T12:54:43.086000+05:30","2016-10-04T12:53:03.889000+05:30","2016-10-04T12:51:24.599000+05:30","2016-10-04T12:49:45.415000+05:30","2016-10-04T12:48:06.220000+05:30","2016-10-04T12:46:26.920000+05:30","2016-10-04T12:44:47.533000+05:30","2016-10-04T12:43:08.011000+05:30","2016-10-04T12:41:28.365000+05:30","2016-10-04T12:39:49.249000+05:30","2016-10-04T12:38:09.972000+05:30","2016-10-04T12:36:30.598000+05:30","2016-10-04T12:34:51.108000+05:30","2016-10-04T12:33:11.604000+05:30","2016-10-04T12:31:32.144000+05:30","2016-10-04T12:29:52.563000+05:30","2016-10-04T12:28:13.268000+05:30","2016-10-04T12:26:34.085000+05:30","2016-10-04T12:24:54.568000+05:30","2016-10-04T12:23:15.121000+05:30","2016-10-04T12:21:35.834000+05:30","2016-10-04T12:19:56.524000+05:30","2016-10-04T12:18:16.935000+05:30","2016-10-04T12:16:37.409000+05:30","2016-10-04T12:14:58.123000+05:30","2016-10-04T12:13:18.591000+05:30","2016-10-04T12:11:39.106000+05:30","2016-10-04T12:09:59.847000+05:30","2016-10-04T12:08:20.392000+05:30","2016-10-04T12:06:40.964000+05:30","2016-10-04T12:05:01.692000+05:30","2016-10-04T12:03:22.290000+05:30","2016-10-04T12:01:42.885000+05:30","2016-10-04T12:00:03.549000+05:30","2016-10-04T11:58:24.385000+05:30","2016-10-04T11:56:45.120000+05:30","2016-10-04T11:55:05.785000+05:30","2016-10-04T11:53:26.524000+05:30","2016-10-04T11:51:47.073000+05:30","2016-10-04T11:50:07.805000+05:30","2016-10-04T11:48:28.558000+05:30","2016-10-04T11:46:49.270000+05:30","2016-10-04T11:45:09.818000+05:30","2016-10-04T11:43:30.472000+05:30","2016-10-04T11:41:51.294000+05:30","2016-10-04T11:40:12.065000+05:30","2016-10-04T11:38:32.785000+05:30","2016-10-04T11:36:53.576000+05:30","2016-10-04T11:35:14.034000+05:30","2016-10-04T11:33:34.689000+05:30","2016-10-04T11:31:55.315000+05:30","2016-10-04T11:30:15.723000+05:30","2016-10-04T11:28:36.308000+05:30","2016-10-04T11:26:56.970000+05:30","2016-10-04T11:25:17.556000+05:30","2016-10-04T11:23:38.171000+05:30","2016-10-04T11:21:58.941000+05:30","2016-10-04T11:20:19.719000+05:30","2016-10-04T11:18:40.447000+05:30","2016-10-04T11:17:01.190000+05:30","2016-10-04T11:15:21.807000+05:30","2016-10-04T11:13:42.482000+05:30","2016-10-04T11:12:03.156000+05:30","2016-10-04T11:10:23.821000+05:30","2016-10-04T11:08:44.391000+05:30","2016-10-04T11:07:04.939000+05:30","2016-10-04T11:05:25.463000+05:30","2016-10-04T11:03:46.097000+05:30","2016-10-04T11:02:06.808000+05:30","2016-10-04T11:00:27.285000+05:30","2016-10-04T10:58:47.893000+05:30","2016-10-04T10:57:08.367000+05:30","2016-10-04T10:55:28.941000+05:30","2016-10-04T10:53:49.766000+05:30","2016-10-04T10:52:10.651000+05:30","2016-10-04T10:50:31.275000+05:30","2016-10-04T10:48:52.101000+05:30","2016-10-04T10:47:12.805000+05:30","2016-10-04T10:45:33.253000+05:30","2016-10-04T10:43:53.915000+05:30","2016-10-04T10:42:14.526000+05:30","2016-10-04T10:40:35.123000+05:30","2016-10-04T10:38:55.763000+05:30","2016-10-04T10:37:16.505000+05:30","2016-10-04T10:35:36.991000+05:30","2016-10-04T10:33:57.701000+05:30","2016-10-04T10:32:18.532000+05:30","2016-10-04T10:30:39.192000+05:30","2016-10-04T10:28:59.590000+05:30","2016-10-04T10:27:20.340000+05:30","2016-10-04T10:25:41.259000+05:30","2016-10-04T10:24:01.797000+05:30","2016-10-04T10:22:22.582000+05:30","2016-10-04T10:20:43.278000+05:30","2016-10-04T10:19:03.902000+05:30","2016-10-04T10:17:24.520000+05:30","2016-10-04T10:15:45.378000+05:30","2016-10-04T10:14:05.884000+05:30","2016-10-04T10:12:26.431000+05:30","2016-10-04T10:10:46.931000+05:30","2016-10-04T10:09:07.297000+05:30","2016-10-04T10:07:27.895000+05:30","2016-10-04T10:05:48.415000+05:30","2016-10-04T10:04:09.096000+05:30","2016-10-04T10:02:29.641000+05:30","2016-10-04T10:00:50.389000+05:30","2016-10-04T09:59:11.180000+05:30","2016-10-04T09:57:31.938000+05:30","2016-10-04T09:55:52.739000+05:30","2016-10-04T09:54:13.442000+05:30","2016-10-04T09:52:34.102000+05:30","2016-10-04T09:50:54.929000+05:30","2016-10-04T09:49:15.420000+05:30","2016-10-04T09:47:36.009000+05:30","2016-10-04T09:45:56.631000+05:30","2016-10-04T09:44:17.211000+05:30","2016-10-04T09:42:37.796000+05:30","2016-10-04T09:40:58.340000+05:30","2016-10-04T09:39:19.044000+05:30","2016-10-04T09:37:39.701000+05:30","2016-10-04T09:36:00.409000+05:30","2016-10-04T09:34:21.258000+05:30","2016-10-04T09:32:41.880000+05:30","2016-10-04T09:31:02.607000+05:30","2016-10-04T09:29:23.219000+05:30","2016-10-04T09:27:43.847000+05:30","2016-10-04T09:26:04.762000+05:30","2016-10-04T09:24:25.664000+05:30","2016-10-04T09:22:46.467000+05:30","2016-10-04T09:21:07.019000+05:30","2016-10-04T09:19:27.596000+05:30","2016-10-04T09:17:48.424000+05:30","2016-10-04T09:16:09.047000+05:30","2016-10-04T09:14:29.518000+05:30","2016-10-04T09:12:50.291000+05:30","2016-10-04T09:11:10.989000+05:30","2016-10-04T09:09:31.545000+05:30","2016-10-04T09:07:52.288000+05:30","2016-10-04T09:06:13.348000+05:30","2016-10-04T09:04:33.995000+05:30","2016-10-04T09:02:54.460000+05:30","2016-10-04T09:01:15.228000+05:30","2016-10-04T08:59:35.656000+05:30","2016-10-04T08:57:56.285000+05:30","2016-10-04T08:56:16.889000+05:30","2016-10-04T08:54:37.594000+05:30","2016-10-04T08:52:58.323000+05:30","2016-10-04T08:51:18.771000+05:30","2016-10-04T08:49:39.166000+05:30","2016-10-04T08:47:59.744000+05:30","2016-10-04T08:46:20.420000+05:30","2016-10-04T08:44:41.191000+05:30","2016-10-04T08:43:01.962000+05:30","2016-10-04T08:41:22.770000+05:30","2016-10-04T08:39:43.354000+05:30","2016-10-04T08:38:03.951000+05:30","2016-10-04T08:36:24.566000+05:30","2016-10-04T08:34:45.330000+05:30","2016-10-04T08:33:05.964000+05:30","2016-10-04T08:31:26.535000+05:30","2016-10-04T08:29:47.255000+05:30","2016-10-04T08:28:07.964000+05:30","2016-10-04T08:26:28.784000+05:30","2016-10-04T08:24:49.573000+05:30","2016-10-04T08:23:10.220000+05:30","2016-10-04T08:21:30.875000+05:30","2016-10-04T08:19:51.571000+05:30","2016-10-04T08:18:12.309000+05:30","2016-10-04T08:16:32.748000+05:30","2016-10-04T08:14:53.352000+05:30","2016-10-04T08:13:13.879000+05:30","2016-10-04T08:11:34.623000+05:30","2016-10-04T08:09:55.225000+05:30","2016-10-04T08:08:15.875000+05:30","2016-10-04T08:06:36.685000+05:30","2016-10-04T08:04:57.423000+05:30","2016-10-04T08:03:18.262000+05:30","2016-10-04T08:01:39.092000+05:30","2016-10-04T07:59:59.522000+05:30","2016-10-04T07:58:20.233000+05:30","2016-10-04T07:56:40.901000+05:30","2016-10-04T07:55:01.429000+05:30","2016-10-04T07:53:22.060000+05:30","2016-10-04T07:51:42.721000+05:30","2016-10-04T07:50:03.343000+05:30","2016-10-04T07:48:23.735000+05:30","2016-10-04T07:46:44.449000+05:30","2016-10-04T07:45:04.945000+05:30","2016-10-04T07:43:25.702000+05:30","2016-10-04T07:41:46.431000+05:30","2016-10-04T07:40:06.934000+05:30","2016-10-04T07:38:27.347000+05:30","2016-10-04T07:36:48.020000+05:30","2016-10-04T07:35:08.641000+05:30","2016-10-04T07:33:29.191000+05:30","2016-10-04T07:31:49.834000+05:30","2016-10-04T07:30:10.339000+05:30","2016-10-04T07:28:30.987000+05:30","2016-10-04T07:26:51.538000+05:30","2016-10-04T07:25:12.507000+05:30","2016-10-04T07:23:33.453000+05:30","2016-10-04T07:21:54.181000+05:30","2016-10-04T07:20:14.872000+05:30","2016-10-04T07:18:35.614000+05:30","2016-10-04T07:16:56.228000+05:30","2016-10-04T07:15:17.196000+05:30","2016-10-04T07:13:37.998000+05:30","2016-10-04T07:11:58.504000+05:30","2016-10-04T07:10:19.249000+05:30","2016-10-04T07:08:39.899000+05:30","2016-10-04T07:07:00.552000+05:30","2016-10-04T07:05:21.371000+05:30","2016-10-04T07:03:42.181000+05:30","2016-10-04T07:02:03.018000+05:30","2016-10-04T07:00:23.457000+05:30","2016-10-04T06:58:44.197000+05:30","2016-10-04T06:57:04.831000+05:30","2016-10-04T06:55:25.403000+05:30","2016-10-04T06:53:46.133000+05:30","2016-10-04T06:52:06.850000+05:30","2016-10-04T06:50:27.259000+05:30","2016-10-04T06:48:47.921000+05:30","2016-10-04T06:47:08.570000+05:30","2016-10-04T06:45:29.137000+05:30","2016-10-04T06:43:49.638000+05:30","2016-10-04T06:42:10.106000+05:30","2016-10-04T06:40:30.555000+05:30","2016-10-04T06:38:51.285000+05:30","2016-10-04T06:37:11.864000+05:30","2016-10-04T06:35:32.523000+05:30","2016-10-04T06:33:53.232000+05:30","2016-10-04T06:32:13.886000+05:30","2016-10-04T06:30:34.533000+05:30","2016-10-04T06:28:55.064000+05:30","2016-10-04T06:27:15.432000+05:30","2016-10-04T06:25:36.243000+05:30","2016-10-04T06:23:57.062000+05:30","2016-10-04T06:22:17.820000+05:30","2016-10-04T06:20:38.652000+05:30","2016-10-04T06:18:59.126000+05:30","2016-10-04T06:17:19.955000+05:30","2016-10-04T06:15:40.685000+05:30","2016-10-04T06:14:01.370000+05:30","2016-10-04T06:12:22.250000+05:30","2016-10-04T06:10:43.074000+05:30","2016-10-04T06:09:03.670000+05:30","2016-10-04T06:07:24.490000+05:30","2016-10-04T06:05:45.070000+05:30","2016-10-04T06:04:05.939000+05:30"]}]};
      console.log(data);*/
      parameter = fields;
      if(data.streams[0].count == 0) {
        $("#single_no_data_parameter_value").empty();
        $("#single_no_data_parameter_value").append("<div class='alert alert-warning' id='alert'>No data for this parameter.</div>");

        return;
      } else {
        $("#single_no_data_parameter_value").empty();
        
        var parameter = null;

        for(var n = data.streams[0].timestamps.length-1; n >=0 ; n--) {
          var date = new Date(data.streams[0].timestamps[n]);
          date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
          if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
            if(data.streams[0].name == "IRRADIATION" || data.streams[0].name == "EXTERNAL_IRRADIATION") {
              parameter = parseFloat((data.streams[0].values[n])*1000);
            } else {
                parameter = parseFloat(data.streams[0].values[n]);
            }
          } else {
              parameter = parseFloat(data.streams[0].values[n]);
          }
          timestamps_parameter.push(date);
          parameter_value.push(parameter);
        }

      }
    },
    error: function(data) {
      console.log("error_streams_data");
      data = null;
    }
  });
  
  var name1 = 'ENERGY';
  var name2 = fields[0];
  var title_dual_axis_chart = 'FOR DATE ' + dateFormat(st, "dd-mm-yyyy");
  var width = 1030;
  var height = 400;
  var div_name = 'single_chart_dual_axis';
  var page = 0;

  dual_axis_chart_plotly(timestamps_energy, energy_points, timestamps_parameter, parameter_value, name1, name2, title_dual_axis_chart, width, height, div_name, page);

}