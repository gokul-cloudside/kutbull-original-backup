

    // d3.csv('data/energy-data-clean.csv', function (data) {
    // d3.csv('data/grand-total-records1.csv', function (data) {
    function loadData (consumption_data) {
            'use strict';

            //var quarterChart = dc.pieChart('#quarter-chart');
            var premisePieChart = dc.pieChart('#premise-pie-chart');
            var dayOfWeekChart = dc.rowChart('#day-of-week-chart');
            var tsApcChart = dc.lineChart('#tsapc-chart');
            var data = JSON.parse(consumption_data)

        /* since its a csv file we need to format the data a bit */
        var dateFormat = d3.time.format('%Y-%m-%d %H:%M:%S');
        var numberFormat = d3.format('.2f');
       
        var devices = [];
        var keys = {};

        data.forEach(function (d) {
        	keys[d.premise] = true;
            d.dd = dateFormat.parse(d.date);
            d.month = d3.time.month(d.dd); // pre-calculate month for better performance
            
        });

       var counter = 0;
       var firstDevice; 
       for (var k in keys){
        if(counter == 0){
            counter = counter + 1;
            firstDevice = k;
        }
        else{
            devices.push(k);
        }
       }

        //### Create Crossfilter Dimensions and Groups
        //See the [crossfilter API](https://github.com/square/crossfilter/wiki/API-Reference) for reference.
        var ndx = crossfilter(data);
        var all = ndx.groupAll();

       var x_domain = d3.extent(data, function(d) {
        return d.dd;
        });

      var x_scale = d3.time.scale();

      x_scale.domain(x_domain);

        // dimension by full date
        var dateDimension = ndx.dimension(function (d) {
            return d.dd;
        });

        var dateGroup = dateDimension.group().reduce(
        function(p, v) { // add
            p[v.premise] = (p[v.premise] || 0) + v.apc;
            return p;
        },
        function(p, v) { // remove
            p[v.premise] -= v.apc;
            return p;
        },
        function() { // initial
            return {};
        });


         var premiseDimension = ndx.dimension(function (d){
            return d.premise;
        });

        var device_1=dateDimension.group().reduceSum(function(d) {if (d.premise == firstDevice) {return Math.floor(d.apc);}else{return 0;}});

        var premiseGroup = premiseDimension.group().reduceSum(function (d){
            return d.apc;
        });

        // summerize consumption by quarter
        var quarter = ndx.dimension(function (d) {
            var month = d.dd.getMonth();
            if (month <= 2) {
                return 'Q1';
            } else if (month > 2 && month <= 5) {
                return 'Q2';
            } else if (month > 5 && month <= 8) {
                return 'Q3';
            } else {
                return 'Q4';
            }
        });

        var quarterGroup = quarter.group().reduceSum(function (d) {
            return Math.round(d.apc);
        });

        // counts per weekday
        var dayOfWeek = ndx.dimension(function (d) {
            var day = d.dd.getDay();
            var name = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            return day + '.' + name[day];
        });

        var dayOfWeekGroup = dayOfWeek.group().reduceSum(function (d) {
            return Math.round(d.apc);
        });

        premisePieChart.width(180)
            .height(180)
            .radius(80)
            .innerRadius(30)
            .dimension(premiseDimension)
            .group(premiseGroup)
            .title(function(d) { return "Devices" })
            .label(function(d) { return "Devices" })
            .ordinalColors(["#56B2EA","#E064CD","#F8B700","#78CC00","#7B71C5"]);

        //quarterChart.width(180)
        //    .height(180)
        //    .radius(80)
        //    .innerRadius(30)
        //    .dimension(quarter)
        //    .group(quarterGroup);

        dayOfWeekChart.width(180)
            .height(180)
            .margins({top: 20, left: 10, right: 10, bottom: 20})
            .group(dayOfWeekGroup)
            .dimension(dayOfWeek)
            // assign colors to each value in the x scale domain
            .ordinalColors(['#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#dadaeb'])
            .label(function (d) {
                return d.key.split('.')[1];
            })
            // title sets the row text
            .title(function (d) {
                return d.value;
            })
            .elasticX(true)
            .xAxis().ticks(4);

        tsApcChart
          .renderArea(true)
          .width(1000)
          .height(200)
          .ordinalColors(["#56B2EA","#E064CD","#F8B700","#78CC00","#7B71C5"])
          .legend(dc.legend().x(860).y(10).itemHeight(13).gap(5))
          .x(x_scale)
          .brushOn(true)
          .yAxisLabel("")
          .dimension(dateDimension)
          .group(device_1, firstDevice)
          .elasticY(true);

            devices.forEach(function(device, i) {
                // alert(device);
             tsApcChart.stack(dateGroup, device, 
                 function (d) {
                            return (d.value[device]) + i;
                 });
            });


        dc.dataCount('.dc-data-count')
            .dimension(ndx)
            .group(all)
            .html({
                some:'<strong>%filter-count</strong> selected out of <strong>%total-count</strong> records' +
                    ' | <a href=\'javascript:dc.filterAll(); dc.renderAll();\'\'>Reset All</a>',
                all:'All records selected. Please click on the graph to apply filters.'
            });

        dc.renderAll();
        d3.selectAll('#version').text(dc.version);
    };

    
