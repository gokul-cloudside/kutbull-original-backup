$(document).ready(function() {

  $("#breadcrumb_page_path").empty();
  $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Contextual Data</a></li>')

  streams_data();
});

$(function() {
    $(".datetimepicker_source_time").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_source_time").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function get_dates(){
    // get the start date
    /*var st = $(id).val();*/
    var st = $('#source_time').val();

    var date = [];
    date = st.split('/');
    st = date[2] + "/" + date[1] + "/" + date[0];

    /*if (st == '')
        st = new Date();
    else
        st = new Date(st);*/
    // prepare an end date
    st = new Date(st);

    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function select_all_inverters_compare_inverters() {
  $('#source_dropdown option').prop('selected', true);

  var fields_inverters_compare = [];

  $('#source_dropdown > option:selected').each(function() {
      fields_inverters_compare.push($(this).val());
  });
}

$(function() {
  $(".datetimepicker_inverters_start_time").datetimepicker();
});
  function limit_compare_inverter_date() {
    var dat = new Date($('#inverters_start_time').val());
    var d = dat;

    $(function(){
      $('#inverters_end_time').datetimepicker({
        onShow:function( ct ){
            this.setOptions({
            minDate: new Date($('#inverters_start_time').val()),
            maxDate:(new Date(d.setHours(d.getHours()+168)))
          })
        },
      });
    });
  }
  function enable_button_download_inverters_png() {
    document.getElementById("button_chart_as_png_download_inverter").disabled = false;
  }

  function streams_data() {

    $('#streams_dropdown').empty();
    $.ajax({
      type: "GET",
      url: "/api/sources/".concat(source_key).concat('/streams/'),
      success: function(streams){
          $('#streams_dropdown').html('');
          if (streams.length == 0) {
              $('#streams_dropdown').append("<option>No Streams are present! </option>");
          } else {
              for (var i = 0 ; i <= streams.length-1 ; i++) {
                $('#streams_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
              } 
          }
      },
      error: function(data){
          console.log("no data");
      }
    });

    /*var streams_array = ["IRRADIATION", "MODULE_TEMPERATURE", "ENERGY_METER_DATA", "EXTERNAL_IRRADIATION", "AMBIENT_TEMPERATURE", "FREQUENCY"];

    $('#streams_dropdown').empty();
    for (var i = 0 ; i <= streams_array.length-1 ; i++) {
      $('#streams_dropdown').append("<option value=" + streams_array[i] + ">" + streams_array[i] + "</option>");
    }*/

    /*$.ajax({
      type: "GET",
      url: "/api/sources/".concat("sZmA3R5563fooMq").concat('/streams/'),
      success: function(streams){
        if (streams.length == 0) {
            $("#streams_dropdown").append("<option>No Streams are present! </option>");
        } else {
            for (var i = 0 ; i <= streams.length-1 ; i++) {
                $('#streams_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
            } 
        }
      },
      error: function(data){
          console.log("no data");
      }
    });*/
  }

  function streams_chart_data() {

    var fields = [];
      
    $('#streams_dropdown > option:selected').each(function() {
        fields.push($(this).val());
    });

    if(fields.length == 0) {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select a Parameter.");
        
        return;
    } else {
        $("#row_plot").empty();
    }

    var start_date = $("#source_time").val();

    if(start_date == "") {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select a date.");
        
        return;
    } else {
        $("#row_plot").empty(); 
    }

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    /*if(newet < newst) {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("End Date should be greater than Start Date.");
        
        return;
    } else {
        $("#row_plot").empty();
    }*/

    $.ajax({
        type: "GET",
        url: "/api/sources/".concat(source_key).concat('/data/'),
        data: {streamNames: fields.join(","), startTime: st, endTime: et},
        success: function(data) {
          var packagedData = [];
          var streamNames = [];

          if(data.streams[0].count == 0) {
            $(".nvd3-svg").remove();
            $("#row_plot").empty();
            $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
            $("#alert").empty();
            $("#alert").append("No data for the Parameter.");

            return;
          } else {
              $("#streams_comparison_data").append("<svg></svg>");

              var arrayValue = [];
              if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
                if(data.streams[0].name == "IRRADIATION" || data.streams[0].name == "EXTERNAL_IRRADIATION") {
                  for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                    arrayValue.push({x: new Date(data.streams[0].timestamps[j]), y: (parseFloat(data.streams[0].values[j]))*1000});
                  }                
                } else {
                  for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                    arrayValue.push({x: new Date(data.streams[0].timestamps[j]), y: parseFloat(data.streams[0].values[j])});
                  }
                }
              } else {
                  for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                    arrayValue.push({x: new Date(data.streams[0].timestamps[j]), y: parseFloat(data.streams[0].values[j])});
                  }
              }

              /*for(var n = 0; n < data.length; n++) {*/
              /*var arrayValue = [];
              for (var j = data.streams[0].timestamps.length-1; j > 0; j--) {
                  arrayValue.push({x: new Date(data.streams[0].timestamps[j]), y: parseFloat(data.streams[0].values[j])});
              }*/
              packagedData.push(arrayValue);
            /*}*/
              streams_chart(packagedData, fields); 
          }
        },
        error: function(data) {
          console.log("error_streams_data");
          data = null;
        }
    });
}

function streams_chart(packagedData, fields) {
  color = ["#ff7f0e","#7777ff","#2ca02c","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700"];

  nv.addGraph(function() {
    var chart = nv.models.lineChart()
                  .margin({left: 90, right: 50, bottom:110})  //Adjust chart margins to give the x-axis some breathing room.
                  .useInteractiveGuideline(true)  //We want nice looking tooltips   and a guideline!
                  .showLegend(true)       //Show the legend, allowing users to turn on/off line series.
                  .showYAxis(true)        //Show the y-axis
                  .showXAxis(true)        //Show the x-axis
    ;
      chart.xAxis     //Chart x-axis settings
        .axisLabel('')
        .tickFormat(function(ts) { 
          return d3.time.format('%I:%M %p')(new Date(ts)); 
        });

      var stream_name_y = $("#streams_dropdown").val();

      chart.yAxis     //Chart y-axis settings
        .axisLabel(stream_name_y)
        .tickFormat(d3.format('.02f'));

      var result = [];

      for(var i = 0; i < packagedData.length; i++) {
        if(packagedData[i] != 0) {
        result.push({
            values: packagedData[0], 
            key: fields[0], 
            color: color[0]  
        });
      
        d3.select('#streams_comparison_data svg')    //Select the <svg> element you want to render the chart in.   
          .datum(result)         //Populate the <svg> element with chart data...
          .call(chart);    
        }
      }

    //Update the chart when window resizes.
    nv.utils.windowResize(function() { chart.update() });

    $(".nvd3-svg").css("float", "left");

    return chart;
  });
  
  /*var inverter_names_count = 0;

  for(var i =0; i < packagedData.length; i++) {
    if(packagedData[i].length != 0) {

    } else {
        inverter_names_count++;
    }
  }*/

  /*if(invertersNames.length == inverter_names_count) {
    $("#svg_chart_inverter_download").empty();
    $("#row_plot").empty();
    $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
    $("#alert").empty();
    $("#alert").append("There is no data generation either for the selected parameter or for this range of dates. Select some different range of dates or parameter.");
  } else {
  }*/
}