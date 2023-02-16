$(document).ready(function() {

    var csrftoken = Cookies.get('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    grid();
});

var content = null;

var configuration = [];

function redraw_id() {
    window.dispatchEvent(new Event('resize'));
}

function configuration_data() {
    $("#row_alert").show();

    $("#row_alert").empty();
    $("#row_alert").append("<div class='alert alert-warning' id='alert'></div>");
    $("#alert").empty();
    $("#alert").append("Save configuration by clicking the save button in the bottom of the page.");

    this.serializedData = _.map($('.grid-stack > .grid-stack-item:visible'), function (el) {
        el = $(el);
        var node = el.data('_gridstack_node');
        return {
            id: el.attr('id'),
            x: el.attr('data-gs-x'),
            y: el.attr('data-gs-y'),
            width: el.attr('data-gs-width'),
            height: el.attr('data-gs-height'),
            name: el.attr('name')
        };
    }, this);

    $("#save").show();
}

function grid() {
    function isBreakpoint(alias) {
        return $('.device-' + alias).is(':visible');
    }

    var options = {
        float: false
    };

    $("#row_alert").hide();

    /*$('.grid-stack').gridstack({
        alwaysShowResizeHandle: true
    });*/

    $('.grid-stack').gridstack(options);

    function resizeGrid() {
        var grid = $('.grid-stack').data('gridstack');
        if (isBreakpoint('xs')) {
            /*$('#grid-size').text('One column mode');*/
        } else if (isBreakpoint('sm')) {
            grid.setGridWidth(3);
            /*$('#grid-size').text(3);*/
        } else if (isBreakpoint('md')) {
            grid.setGridWidth(6);
            /*$('#grid-size').text(6);*/
        } else if (isBreakpoint('lg')) {
            grid.setGridWidth(12);
            /*$('#grid-size').text(12);*/
        }
    };

    /*$('.grid-stack').resize(function() {
        console.log($(this).window);
    });*/

    $('.grid-stack').on('resizestop', function (event, ui) { 
        redraw_id();
        var resized_id = ui.element[0].id;

        /*var a = $("#"+resized_id).find('.col-md-6').find(".panel-title").text();
        console.log(a);*/

        $("#"+resized_id).find('.left').addClass('col-md-12').removeClass('col-md-6');
        configuration_data();
    });

    $('.grid-stack').on('dragstop', function (event, ui) {
        /*var element = $(event.target);
        var node = element.data('_gridstack_node');
        console.log(node);*/

        configuration_data();
    });

    new function () {

        $.ajax({
            type: "GET",
            async: false,
            url: "/api/widgets/",
            success: function(data) {
                configuration = data;
            },
            error: function(data) {
                console.log("error_streams_data");
                data = null;
            },
        });

        /*this.serializedData = [
            {x: 0, y: 0, width: 4, height: 3, name: "weather", id: 1, filepath: "/static/solarrms/widgets/weather/weather.html"},
            {x: 4, y: 0, width: 4, height: 3, name: "gauge", id: 2, filepath: "/static/solarrms/widgets/gauge/gauge.html"},
            {x: 8, y: 0, width: 4, height: 3, name: "meta", id: 3, filepath: "/static/solarrms/widgets/meta/meta.html"},
            {x: 0, y: 4, width: 12, height: 3, name: "power", id: 4, filepath: "/static/solarrms/widgets/power-todays/power-todays.html"},
            {x: 0, y: 8, width: 12, height: 9, name: "inverters_status", id: 5, filepath: "/static/solarrms/widgets/inverter-status/inverter-status.html"}
        ];*/

        this.serializedData = [];

        for(var i = 0; i < configuration.widgets.length; i++) {
            this.serializedData.push(configuration.widgets[i]);
        }

        this.grid = $('.grid-stack').data('gridstack');

        this.loadGrid = function () {
            this.grid.removeAll();
            var items = GridStackUI.Utils.sort(this.serializedData);
            _.each(items, function (node, i) {
                readhtml(node.filepath);
                if(configuration.configure == true) {
                    this.grid.addWidget($('<div id="'+ node.id + '" name="' + node.name + '"><div class="grid-stack-item-content" style="overflow-y: hidden;">' + content + '</div></div>'),node.x, node.y, node.width, node.height);
                } else {
                    this.grid.addWidget($('<div id="'+ node.id + '" name="' + node.name + '" data-gs-no-resize="true" data-gs-no-move="true"><div class="grid-stack-item-content" style="overflow-y: hidden;">' + content + '</div></div>'),node.x, node.y, node.width, node.height);
                }
            }, this);
            
            return false;
        }.bind(this);

        this.loadGrid();
        resizeGrid();
    };

    $("#save_button").append('<button type="submit" id="save" class="btn btn-success width-70" onClick="save_configuration_json()">Save</button>');

    $("#save").hide();

}

function save_configuration_json() {

    $("#row_alert").empty();

    $("#row_alert").hide();

    this.serializedData = _.map($('.grid-stack > .grid-stack-item:visible'), function (el) {
        el = $(el);
        var node = el.data('_gridstack_node');
        return {
            id: el.attr('id'),
            x: node.x,
            y: node.y,
            width: node.width,
            height: node.height,
            name: el.attr('name')
        };
    }, this);

    var config = JSON.stringify(this.serializedData, null, '    ');

    var sorted_items = GridStackUI.Utils.sort(this.serializedData);

    configuration.widgets = sorted_items;

    var string_configuration = JSON.stringify(configuration, null, '    ');

    $.ajax({
        url : "/api/widgets/".concat(configuration.id),
        data : string_configuration,
        type : 'PATCH',
        contentType : 'application/json',
        success: function(data) {

        },
        error: function(data) {
            console.log("error_patching_data");
            data = null;
        }
    });

    $("#save").hide();
}

function readhtml(filepath) {
    
    content = null;
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", filepath, false);
    rawFile.onreadystatechange = function ()
    {
        if(rawFile.readyState === 4)
        {
            if(rawFile.status === 200 || rawFile.status == 0)
            {
                content = rawFile.responseText;
            }
        }
    }
    rawFile.send(null);

}