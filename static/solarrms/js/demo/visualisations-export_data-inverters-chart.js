$(document).ready(function() {

  $("#breadcrumb_page_path").empty();
  $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Download Chart</a></li>')

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
        var list = $("#inverters_dropdown_compare");
        $("#inverters_dropdown_compare").html('');
        if (inverters.length == 0) {
          $("#inverters_dropdown_compare").append("<option>No Streams are present! </option>");
        } else {
          /*$("#inverters_dropdown_compare").append("<option value='' disabled selected>--Choose Inverter--</option>");*/
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

    var fields_inverters_sourcekeys = [];
    var fields_inverters_inverters = [];

    var fields_sourcekeys = [];
    var fields_inverters = [];

    $('#inverters_dropdown_compare > option:selected').each(function() {
        fields_sourcekeys.push($(this).val());
        fields_inverters.push($(this).text());
    });

    for(var i = 0; i < fields_sourcekeys.length; i++) {
      if(fields_sourcekeys[i] != "NORTH" && fields_sourcekeys[i] != "SOUTH" && fields_sourcekeys[i] != "EAST" && fields_sourcekeys[i] != "WEST" && fields_sourcekeys[i] != "SOUTH-WEST" && fields_sourcekeys[i] != "EAST-WEST") {
        fields_inverters_sourcekeys.push(fields_sourcekeys[i]);
        fields_inverters_inverters.push(fields_inverters[i]);
      }
    }

    if(fields_inverters_sourcekeys.length == 0) {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select 1 or more Inverters.");

        return;
    } else {
        $("#row_plot").empty();
    }

    var multiple_inv = [];
    var stream_name = [];

    $('#singleStream_dropdown > option:selected').each(function() {
        stream_name.push($(this).val());
    });

    if(stream_name.length == 0) {
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
    
    /*for(var i = 0; i < fields_inverters.length; i++) {
      var fields = [];  

      var invertersNames = [];*

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
    }*/

    var stream_inverter_data = inverters_csv_parse_data(st, et, fields_inverters_sourcekeys, stream_name);

    /*var packagedData = [];
    var streamNames = [];

    for(var n = 0; n < multiple_inv.length; n++) {
      var arrayValue = [];
      for (var j = multiple_inv[n].streams[0].timestamps.length-1; j > 0; j--) {
          arrayValue.push({x: new Date(multiple_inv[n].streams[0].timestamps[j]), y: parseFloat(multiple_inv[n].streams[0].values[j])});
      }
      packagedData.push(arrayValue);
    }*/

    if(stream_inverter_data.data.length > 2) {

      $("#inverter_comparison_no_data").empty();
      $("#inverter_comparison_data").append("<svg id='svg_chart_inverter_download'></svg>");

      var arrayData = [];
      var inverters_stream_packaged_data = [];

      for (var i = 0; i < fields_inverters_inverters.length; i++) {
        arrayData = [];
        for (var j = 1; j < stream_inverter_data.data.length - 1; j++) {
          var d = new Date(stream_inverter_data.data[j][0]);
          var date = d.getTime();
          var date_form_api = new Date(date - (330 * 60000));
          var data_value = parseFloat(stream_inverter_data.data[j][i+1]);
          if(isNaN(data_value)) {
            data_value = null;
          }
          arrayData.push({x: date_form_api, y: data_value});
        }
        inverters_stream_packaged_data.push({
          "key": fields_inverters_inverters[i],
          "values": arrayData
        });
      }
    } else {
      document.getElementById("button_chart_as_png_download_inverter").disabled = true;

      $("#inverter_comparison_data").empty();
      $("#inverter_comparison_no_data").empty();
      $("#inverter_comparison_no_data").append("<div class='alert alert-warning' id='alert'></div>");
      $("#alert").empty();
      $("#alert").append("No data for this parameter. Try some other parameter.");
      
      return;
    }

    inverters_chart(inverters_stream_packaged_data, fields_inverters_inverters, invertersPacks);
}

function inverters_chart(packagedData, invertersNames, invertersPacks) {

  nv.addGraph(function() {
    color = ["#1F77B4","#AEC7E8","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700","#ff7f0e"];
    line_chart = nv.models.lineChart()
            .margin({top: 5, right: 31, bottom: 80, left: 65})
            .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
            .showLegend(false)
            .showYAxis(true)        //Show the y-axis
            .showXAxis(true)        //Show the x-axis
            ;

    line_chart.xAxis
        .axisLabel('')
        .tickFormat(function(ts) { 
          return d3.time.format('%y-%m-%d %H:%M')(new Date(ts)); 
        })
        .rotateLabels(-45);

    var stream_name_y = $("#singleStream_dropdown").val();

    line_chart.yAxis
      .axisLabel(stream_name_y)
      .tickFormat(d3.format('.02f'));

    d3.select('#svg_chart_inverter_download')
            .datum(packagedData)
            .call(line_chart);

    nv.utils.windowResize(function() { line_chart.update() });

    $(".nvd3-svg").css("float", "left");

    return line_chart;
  });
  
  var inverter_names_count = 0;

  for(var i =0; i < packagedData.length; i++) {
    console.log("in");
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
    $("#alert").append("There is no data generation either for the selected parameter or for this range of dates. Select some different range of dates or parameter.");
    $("#download_chart_image").hide();
  } else {
    $("#download_chart_image").show();
  }
}

// create context and horizon
/*var context = cubism.context().size(1010)
var horizon = context.horizon().extent([0,2])*/
 
// define metric accessor
/*function random_ma(packagedData, name) {
   return context.metric(function(start,stop,step,callback){
        var values = [];
        for(var i = 0; i < packagedData.length; i++) {
          for(var j = 0; j < 10; j++) {
            start = packagedData[0][j].x;
            values.push(packagedData[0][j].y);
          }
        }*/
        /*while (+start < +stop){ start = +start +step; values.push(1);}*/
       /*callback(null, values);
   }, name);
}*/

/*function cubism_chart(packagedData, invertersNames, invertersPacks) {*/
  // draw graph
  /*console.log(packagedData);

  var arrayData = [];

  var arrayData = random_ma(packagedData, invertersNames);
  
  horizon.metric(arrayData);
   
  d3.select("#graph").selectAll(".horizon")
        .data(invertersNames)
        .enter()
        .append("div")
        .attr("class", "horizon")
        .call(horizon);*/
   
  // set rule
  /*d3.select("#body").append("div")
    .attr("class", "rule")
    .call(context.rule());*/
   
  // set focus
  /*context.on("focus", function(i) {
      d3.selectAll(".value")
          .style( "right", i == null ? null : context.size() - i + "px");
  });*/
  // set axis