$(document).ready(function() {

  $("#breadcrumb_page_path").empty();
  $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Inverter Set</a></li>')

  limit_plant_future_inverters_end_day_date();
  inverters_data();

  $("input[name$='radios']").click(function() {
    var r_button = $(this).val();
    
    if(r_button == "NORTH"||r_button == "SOUTH"||r_button == "EAST"||r_button == "WEST"||r_button == "SOUTH-WEST"||r_button == "EAST-WEST"||r_button == "ALL") {
      $("#"+r_button).click(function() {
          multipleinverter_dropdown_select = 0;
          $("#multiple_dropdown").hide();
      });
    } else if(r_button == "SELECT_INVERTERS") {
      $("#"+r_button).click(function() {
          multipleinverter_dropdown_select = 1;
          $("#multiple_dropdown").show();
      });
    }
  });
});

$(function() {
    $(".datetimepicker_multiple_inverters_start_time").datetimepicker({
      
    });
    $(".datetimepicker_multiple_inverters_start_time").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function limit_plant_future_inverters_start_day_date() {
  $(function(){
      $('#multiple_inverters_start_date').datetimepicker({
          onShow:function( ct ){
              this.setOptions({
                  maxDate: new Date()
              })
          }
      });
  });
}

function limit_plant_future_inverters_end_day_date() {
  var dat = new Date($('#multiple_inverters_start_date').val());
  var d = dat;

  $(function(){
    $('#multiple_inverters_end_date').datetimepicker({
      onShow:function( ct ){
          this.setOptions({
            minDate: new Date($('#multiple_inverters_start_date').val()),
            maxDate:(new Date(d.setHours(d.getHours()+168)))
        })
      },
    });
  });
}

function get_dates(){
  // get the startTime date
  var st = $('#multiple_inverters_time').val();
  if (st == '')
      st = new Date();
  else
      st = new Date(st);
  // prepare an end date
  var e = new Date(st.getTime());
  e = new Date(e.setDate(st.getDate() + 1));
  // convert them into strings
  st = dateFormat(st, "yyyy/mm/dd");
  e = dateFormat(e, "yyyy/mm/dd");

  return [st, e]
}

function select_all_inverters_compare_inverters() {
  $('#inverters_dropdown_compare option').prop('selected', true);

  var fields_inverters_compare = [];

  $('#inverters_dropdown_compare > option:selected').each(function() {
      fields_inverters_compare.push($(this).val());
  });
}

/*$(function() {
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
  function download_chart_as_png_inv() {
    saveSvgAsPng(document.getElementById("svg_chart_inverter_download"), "chart.png", {backgroundColor: "white"});
  }*/

  var invertersPacks = [];
  function inverters_data() {
    $.ajax({
      type: "GET",
      url: "/api/solar/plants/".concat(plant_slug).concat("/inverters/"),
      success: function(inverters){
        var keys = [];
        var list = $("#inverters_dropdown_compare");
        var list2 = $("#multipleinverter_dropdown_compare");
        $("#inverters_dropdown_compare").html('');
        $("#multipleinverter_dropdown_compare").html('');
        if (inverters.length == 0) {
          $("#inverters_dropdown_compare").append("<option>No Streams are present! </option>");
        } else {
          $("#inverters_dropdown_compare").append("<option value='' disabled selected>--Choose Inverter--</option>");
          $("#multipleinverter_dropdown_compare").append("<option value='' disabled selected>--Choose Inverter--</option>");
          var north = $("<option id='north' disabled style='font-size:15px;font-weight:900;'><strong>NORTH</strong></option>");
          var south = $("<option id='south' disabled style='font-size:15px;font-weight:900;'><strong>SOUTH</strong></option>");
          var east = $("<option id='east' disabled style='font-size:15px;font-weight:900;'><strong>EAST</strong></option>");
          var west = $("<option id='west' disabled style='font-size:15px;font-weight:900;'><strong>WEST</strong></option>");
          var south_west = $("<option id='south_west' disabled style='font-size:15px;font-weight:900;'><strong>SOUTH-WEST</strong></option>");
          var east_west = $("<option id='east_west' disabled style='font-size:15px;font-weight:900;'><strong>EAST-WEST</strong></option>");
          list.append(north);
          list.append(south);
          list.append(east);
          list.append(west);
          list.append(south_west);
          list.append(east_west);
          for (var i = inverters.length-1; i >= 0; i--) {
            if(inverters[i].orientation == "NORTH") {
              $("#north").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "SOUTH") {
              $("#south").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "EAST") {
              $("#east").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "WEST") {
              $("#west").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "SOUTH-WEST") {
              $("#south_west").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "EAST-WEST") {
              $("#east_west").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            }
            keys[i] = inverters[i].sourceKey;
            invertersPacks.push({name: inverters[i].name, sourceKey: inverters[i].sourceKey});
          }
          var north1 = $("<option id='north1' disabled style='font-size:15px;font-weight:900;'><strong>NORTH</strong></option>");
          var south1 = $("<option id='south1' disabled style='font-size:15px;font-weight:900;'><strong>SOUTH</strong></option>");
          var east1 = $("<option id='east1' disabled style='font-size:15px;font-weight:900;'><strong>EAST</strong></option>");
          var west1 = $("<option id='west1' disabled style='font-size:15px;font-weight:900;'><strong>WEST</strong></option>");
          var south_west1 = $("<option id='south_west1' disabled style='font-size:15px;font-weight:900;'><strong>SOUTH-WEST</strong></option>");
          var east_west1 = $("<option id='east_west1' disabled style='font-size:15px;font-weight:900;'><strong>EAST-WEST</strong></option>");
          list2.append(north1);
          list2.append(south1);
          list2.append(east1);
          list2.append(west1);
          list2.append(south_west1);
          list2.append(east_west1);
          for (var i = inverters.length-1; i >= 0; i--) {
            if(inverters[i].orientation == "NORTH") {
              $("#north1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "SOUTH") {
              $("#south1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "EAST") {
              $("#east1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "WEST") {
              $("#west1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "SOUTH-WEST") {
              $("#south_west1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            } else if(inverters[i].orientation == "EAST-WEST") {
              $("#east_west1").after("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            }
            keys[i] = inverters[i].sourceKey;
            invertersPacks.push({name: inverters[i].name, sourceKey: inverters[i].sourceKey});
          }
        }
        streams_data(inverters, invertersPacks); 
      },
      error: function(data){
        console.log("no data");
      }
    });
  }

  function streams_data(inverters, invertersPacks) {
    $.ajax({
      type: "GET",
      url: "/api/sources/".concat(inverters[0].sourceKey).concat('/streams/'),
      success: function(streams){
          /*$("#singleStream_dropdown").html('');*/
          $("#multipleinverterStream_dropdown").html('');
          if (streams.length == 0) {
              /*$("#singleStream_dropdown").append("<option>No Streams are present! </option>");*/
              $("#multipleinverterStream_dropdown").append("<option>No Streams are present! </option>");
          } else {
              for (var i = 0 ; i <= streams.length-1 ; i++) {
                /*$('#singleStream_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");*/
                $("#multipleinverterStream_dropdown").append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
              } 
          }
      },
      error: function(data){
          console.log("no data");
      }
    }); 
  }

  /*function inverters_chart_data() {

    var fields_inverters = [];

    $('#inverters_dropdown_compare > option:selected').each(function() {
        fields_inverters.push($(this).val());
    });

    if(fields_inverters.length == 0) {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select 1 or more Inverters.");

        return;
    } else {
        $("#row_plot").empty();
    }

    var multiple_inv = [];
    
    for(var i = 0; i < fields_inverters.length; i++) {
      var fields = [];  
      $('#singleStream_dropdown > option:selected').each(function() {
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

      var st = $('#inverters_start_time').val();
      var et = $('#inverters_end_time').val();

      if(st == '') {
          $("#row_plot").empty();
          $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
          $("#alert").empty();
          $("#alert").append("Select a Starting Date.");
          return;
      } else {
          $("#row_plot").empty();
      }

      if(et == '') {
          $("#row_plot").empty();
          $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
          $("#alert").empty();
          $("#alert").append("Select a End Date.");
          
          return;
      } else {
          $("#row_plot").empty();
      }

      var newst = new Date(st).getTime();
      var newet = new Date(et).getTime();

      if(newet < newst) {
          $("#row_plot").empty();
          $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
          $("#alert").empty();
          $("#alert").append("End Date should be greater than Start Date.");
          
          return;
      } else {
          $("#row_plot").empty();
      }

      var invertersNames = [];

      var y = 0;

      for(var j = 0; j < invertersPacks.length; j++) {
          for(var h = 0; h < fields_inverters.length; h++) {
              if(fields_inverters[h] == invertersPacks[j].sourceKey) {
                  invertersNames[y] = invertersPacks[j].name;
                  y++;
              }
          }
      }

      $.ajax({
          type: "GET",
          async: false,
          url: "/api/solar/plants/".concat(plant_slug).concat('/inverters/').concat(fields_inverters[i]).concat('/data/'),
          data: {streamNames: fields.join(","), startTime: st, endTime: et},
          success: function(data) {
              multiple_inv.push(data);     
          },
          error: function(data) {
              console.log("error_streams_data");
              data = null;
          }
      });
    }
    var packagedData = [];
    var streamNames = [];

    for(var n = 0; n < multiple_inv.length; n++) {
      var arrayValue = [];
      for (var j = multiple_inv[n].streams[0].timestamps.length-1; j > 0; j--) {
          arrayValue.push({x: new Date(multiple_inv[n].streams[0].timestamps[j]), y: parseFloat(multiple_inv[n].streams[0].values[j])});
      }
      packagedData.push(arrayValue);
    }
    inverters_chart(packagedData, invertersNames, invertersPacks);
}*/

function download(url) {
  document.getElementById('my_iframe').src = url;
};

/*function stream_data_download() {

  var fields_inverters = [];
  $('#inverters_dropdown_compare > option:selected').each(function() {
    fields_inverters.push($(this).val());
  });

  var fields = [];
  $('#singleStream_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  var st = $('#inverters_start_time').val();
  var et = $('#inverters_end_time').val();

  var download_url = "/solar/plant/".concat(plant_slug).concat('/inverter/').concat(fields_inverters).concat('/data/').concat('download/');
  $.ajax({
    type: "GET",
    async: false,
    url: download_url,
    data: {streamNames: fields.join(","), startTime: st, endTime: et},
    success: function(data) {
      var n = {streamNames: fields.join(","), startTime: st, endTime: et};
      final_download_url = "/solar/plant/".concat(plant_slug).concat('/inverter/').concat(fields_inverters).concat('/data/').concat('download/').concat("?streamNames=").concat(fields[0]).concat("&startTime=").concat(st).concat("&endTime=").concat(et);
      download(final_download_url);
    },
    error: function(data) {
      console.log("error_streams_data_download");
      data = null;
    }
  });

}

function inverters_chart(packagedData, invertersNames, invertersPacks) {

  color = ["#ff7f0e","#7777ff","#2ca02c","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700"];

  nv.addGraph(function() {
    var chart = nv.models.lineChart()
                  .margin({left: 80, right: 50, bottom:80})  //Adjust chart margins to give the x-axis some breathing room.
                  .useInteractiveGuideline(true)  //We want nice looking tooltips   and a guideline!
                  .showLegend(true)       //Show the legend, allowing users to turn on/off line series.
                  .showYAxis(true)        //Show the y-axis
                  .showXAxis(true)        //Show the x-axis
    ;
      chart.xAxis     //Chart x-axis settings
        .axisLabel('')
        .tickFormat(function(ts) { 
          return d3.time.format('%y-%m-%d %H:%M')(new Date(ts)); 
        })
        .rotateLabels(-45);

    var stream_name_y = $("#singleStream_dropdown").val();

      chart.yAxis     //Chart y-axis settings
        .axisLabel(stream_name_y)
        .tickFormat(d3.format('.02f'));

      var result = [];

      for(var i = 0; i < packagedData.length; i++) {
        if(packagedData[i] != 0) {
        result.push({
            values: packagedData[i], 
            key: invertersNames[i], 
            color: color[i]  
        });
      
        d3.select('#inverter_comparison_data svg')    //Select the <svg> element you want to render the chart in.   
          .datum(result)         //Populate the <svg> element with chart data...
          .call(chart);    
        }  
      }

    //Update the chart when window resizes.
    nv.utils.windowResize(function() { chart.update() });
    return chart;
  });
  
  var inverter_names_count = 0;

  for(var i =0; i < packagedData.length; i++) {
    if(packagedData[i].length != 0) {

    } else {
        inverter_names_count++;
    }
  }

  if(invertersNames.length == inverter_names_count) {
    $("#svg_chart_inverter_download").empty();
    $("#row_plot").empty();
    $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
    $("#alert").empty();
    $("#alert").append("There is no data generation either for the selected parameter or for this range of dates. Select some different range of dates or parameter.");
    $("#download_chart_image").hide();
  } else {
    $("#download_chart_image").show();
    stream_data_download();
  }
}*/

function download_multiple(url) {
  document.getElementById('my_iframe_multiple').src = url;
};

function multiple_stream_data_download() {

  var radio = $('.active').attr('id');
  var fields_inverters = [];

  $.ajax({
    type: "GET",
    async: false,
    url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
    success: function(data) {
      if(radio == "NORTH"||radio == "SOUTH"||radio == "EAST"||radio == "WEST"||radio == "SOUTH-WEST"||radio == "EAST-WEST") {
        for(var i = 0; i < data.inverters.length; i++) {
          if(data.inverters[i].orientation == radio) {
            fields_inverters.push(data.inverters[i].key);
          }
        }
      } else if(radio == "ALL") {
          for(var i = 0; i < data.inverters.length; i++) {
            fields_inverters.push(data.inverters[i].key);
          }
      }
    },
    error: function(data) {
        console.log("error_data");
        data = null;
    }
  });

  if(multipleinverter_dropdown_select == 1) {
    $('#multipleinverter_dropdown_compare > option:selected').each(function() {
      fields_inverters.push($(this).val());
    });
  }

  var fields_inverters_length = fields_inverters.length;

  if(fields_inverters[0] == "") {
    var index = fields_inverters.indexOf(fields_inverters[0]);
    fields_inverters.splice(index, 1);
  }

  if(fields_inverters[fields_inverters_length-1] == "") {
    fields_inverters.pop();
  }

  var fields = [];
  $('#multipleinverterStream_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  var st = $('#multiple_inverters_start_date').val();
  var et = $('#multiple_inverters_end_date').val();  

  var download_url = "/solar/plant/".concat(plant_slug).concat('/data/').concat('file/').concat("?inverters=").concat(fields_inverters);
  console.log(download_url);
  $.ajax({
    type: "GET",
    async: false,
    url: download_url,
    data: {startTime: st, endTime: et, streamNames: fields.join(",")},
    success: function(data) {
      var n = {startTime: st, endTime: et, streamNames: fields.join(",")};
      final_download_url = "/solar/plant/".concat(plant_slug).concat('/data/').concat('file/').concat("?inverters=").concat(fields_inverters).concat("&startTime=").concat(st).concat("&endTime=").concat(et).concat("&streamNames=").concat(fields[0]).concat("&file=TRUE");
      download_multiple(final_download_url);
    },
    error: function(data) {
      console.log("error_streams_data_download");
      data = null;
    }
  });
}