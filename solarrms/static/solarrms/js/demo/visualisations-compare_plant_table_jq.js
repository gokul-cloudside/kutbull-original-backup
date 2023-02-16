$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Compare Plant Parameters</a></li>')

    limit_compare_parameters_date();

});

$(function() {
    $(".datetimepicker_start_compare_plant_table_day").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_compare_plant_table_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function limit_compare_parameters_date() {
    $(function(){
        $('#start_compare_parameters_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            },
        });
    });
}

function get_dates(){
    // get the start date
    var st = $("#start_compare_parameters_day").val();
    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        var date = [];
        date = st.split('/');
        st = date[2] + "/" + date[1] + "/" + date[0];
        st = new Date(st);
    }
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function inverter_parameters(query_string) {

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    query_string = "/api/msources/data/?start=".concat(st).concat("&end=").concat(et).concat("&"+query_string+"&fill=ffill");

    parametersMultipleArray = [];

    $.ajax({
        type: "GET",
        url: query_string,
        success: function(data){
            if(data == "") {
                /*$("#parameters_selected").empty();
                $("#parameters_selected").append("<div class='alert alert-warning' id='alert'>Either no data for selected parameters or no parameter selected.</div>");*/

                $("#multiple_line_chart").empty();
                $("#multiple_line_chart").append("<svg style='float: left;'></svg>")

                $("#no_plot").empty();
                $("#no_plot").append("<div class='alert alert-warning' id='alert'>Visualisations can not be done as there is no data.</div>");

            } else { 
                $("#parameters_selected").empty();

                $("#no_plot").empty();

                var parsed_data = Papa.parse(data);

                console.log(parsed_data);
                
                $('#table_div').html('');
                $('<div class="ibox-content" id="data_table"> ' +
                '</div>').appendTo('#table_div');

                $('#table_div').append("<table class='table table-striped table-bordered table-hover dataScroll dataTables-example'> <thead> <tr id='heading_table'> </tr></thread> <tbody id='table_body'> </tbody></table>");

                /*var table_content = "<table class='table table-striped table-bordered table-hover dataTables-example'> <thead> <tr>";
                table_content+='<th>' + 'Timestamp' + '</th>';
                table_content+='<th>' + data['streams'][0]['name'] + '</th>';
                table_content+='</tr></thead><tbody>';

                for (i = 0; i < data['streams'][0].count; i++) {
                    table_content += '<tr>';
                    table_content += '<td>' + new Date(data['streams'][0]["timestamps"][i]) + '</td>';
                    table_content += '<td>' + data["streams"][0]["values"][i] + '</td>';
                    table_content += '</tr>';
                }
                table_content += '</tbody></table>';*/

                $('#heading_table').append("<th>Timestamp</th>");
                for(var heading = 1; heading < parsed_data.data[0].length; heading++) {
                    $('#heading_table').append("<th>"+ parsed_data.data[0][heading] +"</th>");
                }

                for(var invidual_array = 1; invidual_array < parsed_data.data.length-1; invidual_array++) {
                    $('#table_body').append("<tr id='row"+invidual_array+"'> </tr>");
                    for(var invidual_data = 0; invidual_data < parsed_data.data[invidual_array].length; invidual_data++) {
                        $('#row'+invidual_array).append("<td>" + parsed_data.data[invidual_array][invidual_data] + "</td>");
                    }
                }

                /*$('#data_table').append(table_content);*/

                $('.dataTables-example').dataTable({
                    responsive: true,
                    "sScrollX": "100%",
                    "sScrollXInner": "120%",
                    "bScrollCollapse": true,
                    "dom": 'T<"clear">lfrtip',
                    "tableTools": {
                        "sSwfPath": "/static/dataglen/js/copy_csv_xls_pdf.swf"
                    },
                    buttons: [
                        'copy', 'csv', 'excel', 'pdf', 'print'
                    ]
                });

                for (var i = 0; i < parsed_data.data[0].length-1; i++) {
                    arrayData = [];
                    for (var j = 1; j < parsed_data.data.length - 1; j++) {
                        var d = new Date(parsed_data.data[j][0]);
                        var date = d.getTime();
                        var date_form_api = new Date(date);
                        /*var date_form_api = new Date(date - (330 * 60000));*/
                        if (parsed_data.data[j][i+1] != '') {
                            var val_dt = parseFloat(parsed_data.data[j][i+1]);
                        } else {
                            var val_dt = null;
                        }
                        arrayData.push({x: date_form_api, y: val_dt});
                    }
                    parametersMultipleArray.push({
                        "key": parsed_data.data[0][i+1],
                        "values": arrayData
                    });
                }
                
                select_parameters_chart(parametersMultipleArray);

            }
        },
        error: function(data){
            console.log("no data");

            /*$("#parameters_selected").empty();
            $("#parameters_selected").append("<div class='alert alert-warning' id='alert'>Either no data for selected parameters or no parameter selected.</div>");*/

            $('#table_div').empty();
            $('#table_div').append("<div class='alert alert-warning' id='alert'>No parameteres selected. Select atleast 1 parameter.</div>");

            $("#multiple_line_chart").empty();
            $("#multiple_line_chart").append("<svg style='float: left;'></svg>")

            $("#no_plot").empty();
            $("#no_plot").append("<div class='alert alert-warning' id='alert'>Visualisations can not be done because no parameteres are selected.</div>");
        }
    });

}

function select_parameters_chart(packagedData) {

    $("#multiple_line_chart").empty();
    $("#multiple_line_chart").append("<svg style='float: left;'></svg>")

    nv.addGraph(function() {
        /*color = ["#1F77B4","#AEC7E8","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700","#ff7f0e"];*/
        line_chart = nv.models.lineChart()
                .margin({top: 5, right: 31, bottom: 20, left: 65})
                .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                .showLegend(false)       //Show the legend, allowing users to turn on/off line series.
                .showYAxis(true)        //Show the y-axis
                .showXAxis(true)        //Show the x-axis
                ;

        line_chart.xAxis
            .axisLabel('')
            .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        line_chart.yAxis
          .axisLabel('')
          .tickFormat(d3.format('.02f'));

        d3.select('#multiple_line_chart svg')
                .datum(packagedData)
                .call(line_chart);

        nv.utils.windowResize(function() { line_chart.update() });
    });
}