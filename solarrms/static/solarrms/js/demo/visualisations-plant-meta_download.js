$(document).ready(function() {
  streams_data();
  limit_compare_start_date();
});

$(function() {
    $(".datetimepicker_start_time").datetimepicker({
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_time").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

/*$(function() {
    $(".datetimepicker_end_time").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_end_time").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});*/

function get_dates(){
    // get the start date
    /*var st = $(id).val();*/
    var st = $('#start_time').val();

    console.log(st);

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

function limit_compare_start_date() {
  var dat = new Date();
  var d = dat;

  $(function(){
    $('#start_time').datetimepicker({
      onShow:function( ct ){
          this.setOptions({
            maxDate: dat
          })
        },
      });
    });
  }

function limit_compare_end_date() {
  var dat = new Date($('#start_time').val());
  var d = dat;

  $(function(){
    $('#end_time').datetimepicker({
      onShow:function( ct ){
          this.setOptions({
            minDate: new Date($('#start_time').val()),
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

  function download_multiple(url) {
    document.getElementById('my_iframe_multiple').src = url;
  };

  function parameter_data() {

    var fields = [];
      
    $('#streams_dropdown > option:selected').each(function() {
        fields.push($(this).val());
    });

    var st = $("#start_time").val();
    var et = $("#end_time").val();

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

    if(st == "") {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select start date.");
        
        return;
    } else {
        $("#row_plot").empty(); 
    }

    if(et == "") {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("Select end date.");
        
        return;
    } else {
        $("#row_plot").empty(); 
    }

    /*if(newet < newst) {
        $("#row_plot").empty();
        $("#row_plot").append("<div class='alert alert-warning' id='alert'></div>");
        $("#alert").empty();
        $("#alert").append("End Date should be greater than Start Date.");
        
        return;
    } else {
        $("#row_plot").empty();
    }*/
    
    var download_url = "/solar/plant/".concat(plant_slug).concat('/data/').concat('file/').concat("?inverters=").concat(source_key);
    $.ajax({
      type: "GET",
      async: false,
      url: download_url,
      data: {startTime: st, endTime: et, streamNames: fields.join(",")},
      success: function(data) {
        var n = {startTime: st, endTime: et, streamNames: fields.join(",")};
        final_download_url = "/solar/plant/".concat(plant_slug).concat('/data/').concat('file/').concat("?inverters=").concat(source_key).concat("&startTime=").concat(st).concat("&endTime=").concat(et).concat("&streamNames=").concat(fields[0]).concat("&file=TRUE");
        download_multiple(final_download_url);
      },
      error: function(data) {
        console.log("error_streams_data_download");
        data = null;
      }
    });
  
  }