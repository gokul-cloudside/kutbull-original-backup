$(document).ready(function() {
  limit_compare_inverter_date();
  inverters_data();
});

function select_all_inverters_compare_inverters() {
  $('#inverters_dropdown_compare option').prop('selected', true);

  var fields_inverters_compare = [];

  $('#inverters_dropdown_compare > option:selected').each(function() {
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
  function download_chart_as_png_inv() {
    saveSvgAsPng(document.getElementById("svg_chart_inverter_download"), "chart.png", {backgroundColor: "white"});
  }

  var invertersPacks = [];
  function inverters_data() {
    $.ajax({
      type: "GET",
      url: "/api/solar/plants/".concat(plant_slug).concat("/inverters/"),
      success: function(inverters){
        var keys = [];
        $("#inverters_dropdown_compare").html('');
        if (inverters.length == 0) {
          $("#inverters_dropdown_compare").append("<option>No Streams are present! </option>");
        } else {
          for (var i = 0 ; i <= inverters.length-1 ; i++) {
            $('#inverters_dropdown_compare').append("<option value=" + inverters[i].sourceKey + ">" + inverters[i].name + "</option>");
            keys[i] = inverters[i].sourceKey;
            invertersPacks.push({name: inverters[i].name, sourceKey: inverters[i].sourceKey});
          }
          streams_data(inverters, invertersPacks); 
        }
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
          $("#singleStream_dropdown").html('');
          if (streams.length == 0) {
              $("#singleStream_dropdown").append("<option>No Streams are present! </option>");
          } else {
              for (var i = 0 ; i <= streams.length-1 ; i++) {
                  $('#singleStream_dropdown').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");
              } 
          }
      },
      error: function(data){
          console.log("no data");
      }
    }); 
  }

  function inverters_chart_data() {

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
}

var z = 1;

function download(url) {
  document.getElementById('my_iframe'+z).src = url;
};

function stream_data_download() {

  var fields_inverters = [];
  $('#inverters_dropdown_compare > option:selected').each(function() {
    fields_inverters.push($(this).val());
  });

  var fields = [];
  $('#singleStream_dropdown > option:selected').each(function() {
    fields.push($(this).val());
  });

  var streamNames = 0;

  for(var i = 0; i < fields_inverters.length; i++) {

    var st = $('#inverters_start_time').val();
    var et = $('#inverters_end_time').val();

    var inverter_sourceKey = fields_inverters[i];

    var download_url = "/solar/plant/".concat(plant_slug).concat('/inverter/').concat(inverter_sourceKey).concat('/data/').concat('download/');
    $.ajax({
      type: "GET",
      async: false,
      url: download_url,
      data: {streamNames: fields.join(","), startTime: st, endTime: et},
      success: function(data) {
        var n = {streamNames: fields.join(","), startTime: st, endTime: et};
        final_download_url = "/solar/plant/".concat(plant_slug).concat('/inverter/').concat(inverter_sourceKey).concat('/data/').concat('download/').concat("?streamNames=").concat(fields[0]).concat("&startTime=").concat(st).concat("&endTime=").concat(et);
        download(final_download_url);
        z++;
      },
      error: function(data) {
        console.log("error_streams_data_download");
        data = null;
      }
    });
  }
  $("#inverters_download_numbers").empty();
  $("#inverters_download_numbers").append("<div class='alert alert-info' id='alert_inverters_download_numbers_link'></div>");
  $("#alert_inverters_download_numbers_link").append("The number of inverters you choose will be the number of download links you get. Here the links appearing will be <b>"+fields_inverters.length+"</b> for the number of inverters you have chosen");
  z = 1;
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
        enable_button_download_inverters_png();   
    } else {
        inverter_names_count++;
    }
  }

  if(invertersNames.length == inverter_names_count) {
    $("#svg_chart_inverter_download").empty();
    $("#row_plot").empty();
    $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
    $("#alert").empty();
    $("#alert").append("There is no data generation either for the selected parameter or for this range of dates. Select some different range of dates or parameters.");
    $("#download_chart_image").hide();
  } else {
    $("#download_chart_image").show();
    stream_data_download();
  }
}