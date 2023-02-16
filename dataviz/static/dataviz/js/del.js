/* Copyright: Vida Lab Inc. 2014
 * License: BSD
 */

/*--- IMPORTANT GUIDELINES --- 
1. Use div #canvas-svg for svg rendering
    var svg = d3.select("#canvas-svg");
2. 'data' variable contains JSON data from Data tab
    Do NOT overwrite this variable 
3. To define customizable properties, use capitalized variable names,
    and define them in Properties tab ---*/

var drawD3Document = function(data) {
  var WIDTH = 480, HEIGHT = 150;

  var svg = d3.select("#canvas-svg");
  
  var chartColors = d3.scale.category20();
  var chartCount = 0;

  // since its a csv file we need to format the data a bit
  var dateFormat = d3.time.format("%Y-%m-%d %H:%M +0000");

  data.forEach(function(e) {
    e.dd = new Date(dateFormat.parse(e.time).setHours(0,0,0,0));
  });

  var data_range = d3.extent(data, function(d) {
    return d.dd;
  });

  // feed it through crossfilter
  var ndx = crossfilter(data);
  var all = ndx.groupAll();

  var dateDim = ndx.dimension(function (d) {
    return d.dd;
  });

  var tweetsGroupByDate = dateDim.group().reduceSum(function(d) {
    return 1;
  });
  
  var x_domain = d3.extent(data, function(d) {
    return d.dd;
  });

  var x_scale = d3.time.scale();

  x_scale.domain(x_domain);

  var volumeChart = dc.barChart("#" + "tweets" + "-bar-chart");
  
  // draw tweet timeline chart
  volumeChart
    .width(WIDTH)
    .height(HEIGHT + 30)
    .x(d3.time.scale().domain([new Date(1985, 0, 1), Date.now()]))
    .yAxisLabel("")
    .centerBar(true)
    .dimension(dateDim)
    .alwaysUseRounding(true)
    .group(tweetsGroupByDate);
  
  volumeChart.elasticX(true);
  volumeChart.xAxisPadding(1);
  volumeChart.xAxis().tickFormat(d3.time.format("%b %y"));
  volumeChart.yAxis().tickFormat(d3.format("d"));
  volumeChart.render();
  
  var lineCharts = [];
  var impressionsChart = drawLineChart(data, "impressions", "integer");
  lineCharts.push(impressionsChart);
  var engagementsChart = drawLineChart(data, "engagements", "integer");
  lineCharts.push(engagementsChart);
  var retweetsChart = drawLineChart(data, "retweets", "integer");
  lineCharts.push(retweetsChart);
  var favoritesChart = drawLineChart(data, "favorites", "integer");
  lineCharts.push(favoritesChart);
  var userProfileClicksChart = drawLineChart(data, "user profile clicks", "integer");
  lineCharts.push(userProfileClicksChart);
  var urlClicksChart = drawLineChart(data, "url clicks", "integer");
  lineCharts.push(urlClicksChart);
  var hashtagClicksChart = drawLineChart(data, "hashtag clicks", "integer");
  lineCharts.push(hashtagClicksChart);
  var detailExpandsChart = drawLineChart(data, "detail expands", "integer");
  lineCharts.push(detailExpandsChart);
  var permalinkClicksChart = drawLineChart(data, "permalink clicks", "integer");
  lineCharts.push(permalinkClicksChart);
  var followsChart = drawLineChart(data, "follows", "integer");
  lineCharts.push(followsChart);
  
  volumeChart.on("filtered", function (chart) {
        var fdata = volumeChart.dimension().top(Infinity);
        analyzeTopics(fdata);
        dc.events.trigger(function () {
          for (var i = 0; i < lineCharts.length; i++) {
            lineCharts[i].focus(chart.filter());
            lineCharts[i].focus(chart.filter());
          }
          dc.redrawAll(chart.chartGroup());
        });
    });
  
  // day of week
  // counts per weekday
  var dayOfWeek = ndx.dimension(function (d) {
      var day = d.dd.getDay();
      var name=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
      return day+"."+name[day];
  });
  var dayOfWeekGroup = dayOfWeek.group();
  
  var dayOfWeekChart = dc.rowChart("#day-of-week-chart");
  dayOfWeekChart.width(280)
      .height(180)
      .margins({top: 0, left: 10, right: 10, bottom: 20})
      .group(dayOfWeekGroup)
      .dimension(dayOfWeek)
      .on("filtered", function() {
        var fdata = dayOfWeekChart.dimension().top(Infinity);
        analyzeTopics(fdata);
      })
      // assign colors to each value in the x scale domain
      .ordinalColors(d3.scale.category20().range())
      .label(function (d) {
          return d.key.split(".")[1];
      })
      // title sets the row text
      .title(function (d) {
          return d.value;
      })
      .elasticX(true)
      .xAxis().ticks(4)
  dayOfWeekChart.xAxis().tickFormat(d3.format("d"));
  dayOfWeekChart.labelOffsetY(13);
  dayOfWeekChart.render();
  
  // count
  dc.dataCount(".dc-data-count")
    .dimension(ndx)
    .group(all)
    // (optional) html, for setting different html for some records and all records.
    // .html replaces everything in the anchor with the html given using the following function.
    // %filter-count and %total-count are replaced with the values obtained.
    .html({
        some:"<strong>%filter-count</strong> selected out of <strong>%total-count</strong> records | <a href='javascript:dc.filterAll(); dc.renderAll();''>Reset All</a>",
        all:"All records selected. Please click on the graph to apply filters."
    });
  
  // data table
  dc.dataTable(".dc-data-table")
      .dimension(dateDim)
      // data table does not use crossfilter group but rather a closure
      // as a grouping function
      .group(function (d) {
          return d3.time.format("%Y-%m")(d.dd);
      })
      .size(50) // (optional) max number of records to be shown, :default = 25
      // dynamic columns creation using an array of closures
      .columns([
          function (d) {
              return d["Tweet text"] + " <span class='tweet-date'>" + d3.time.format("%b %d")(d.dd) + "</span>";
          },
          function (d) {
              return d.impressions;
          },
          function (d) {
              return d.engagements;
          },
          function (d) {
              return d.retweets;
          },
          function (d) {
              return d.favorites;
          }
      ])
      // (optional) sort using the given field, :default = function(d){return d;}
      .sortBy(function (d) {
          return d.dd;
      })
      // (optional) sort order, :default ascending
      .order(d3.descending)
      // (optional) custom renderlet to post-process chart using D3
      .renderlet(function (table) {
          table.selectAll(".dc-table-group").classed("info", true);
      })
      .render();
  
  function drawLineChart(data, field, format) {
    var dateGroup = dateDim.group().reduceSum(function(d) {
      return +d[field];
    });

    var chart = dc.lineChart("#" + field.replace(/ /g, "-") + "-line-chart");
    // impressions chart
    chart
      .renderArea(true)
      .width(WIDTH)
      .height(HEIGHT)
      .x(x_scale)
      .brushOn(false)
      .yAxisLabel("")
      .dimension(dateDim)
      .group(dateGroup)
      .elasticY(true)
      .colors([chartColors.range()[chartCount]]);
    chart.xAxis().tickFormat(d3.time.format("%b %d"));
    if (format === "percent") {
      chart.yAxis().tickFormat(function(v) {return v + "%";});
    } else if (format === "integer") {
      chart.yAxis().tickFormat(d3.format("d"));
    }
    
    chart.renderTitle(true);
    chart.title(function(p) {
        return d3.time.format("%b %d, %Y")(p.key)
            + "\n"
            + "Value: " + p.value;
    });

    chart.render();

    chartCount++;
    
    return chart;
  }
};

function drawWordBubble(root) {
  var diameter = 500,
      format = d3.format(",d"),
      color = d3.scale.category20();
  
  var bubble = d3.layout.pack()
      .sort(null)
      .size([diameter, diameter])
      .padding(1.5);

  $("#tweet-word-bubble").empty();
  var svg = d3.select("#tweet-word-bubble").append("svg")
      .attr("width", diameter)
      .attr("height", diameter)
      .attr("class", "bubble");
  
  var node = svg.selectAll(".node")
    .data(bubble.nodes(classes(root))
    .filter(function(d) { return !d.children; }))
  .enter().append("g")
    .attr("class", "node")
    .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
  
  node.append("circle")
    .attr("r", function(d) { return d.r; })
    .style("fill", function(d) { return color(d.packageName); });
  
  node.append("text")
    .attr("dy", "0em")
    .style("text-anchor", "middle")
    .text(function(d) { return d.className.substring(0, d.r / 3); });
  
  node.append("text")
    .attr("dy", "1.3em")
    .style("font-size", "12px")
    .style("text-anchor", "middle")
    .text(function(d) { return "" + format(d.value).substring(0, d.r / 3); });
  
  // Returns a flattened hierarchy containing all leaf nodes under the root.
  function classes(root) {
    var classes = [];
  
    function recurse(name, node) {
      if (node.children) node.children.forEach(function(child) { recurse(node.name, child); });
      else classes.push({packageName: name, className: node.name, value: node.size});
    }
  
    recurse(null, root);
    return {children: classes};
  }
  
  d3.select(self.frameElement).style("height", diameter + "px");
}

function analyzeTopics(tweetData) {
var postData = [[], 1];

tweetData.forEach(function(d) {
  postData[0].push(d["Tweet text"]);
});

$.ajax({
  url: "https://api.algorithmia.com/api/kenny/LDA",
  type: "POST",
  data: JSON.stringify(postData),
  dataType: 'json',
  contentType: 'application/json',
  processData: false,
  headers: {
    "Content-Type": "application/json",
    "Authorization": "57606badca804e41b5e0efc900a77b00"
  },
  success: function (data) {
    var rootData = {
      "name": "flare",
      "children": [
      ]
    }
    var result = data.result[0];
    for (var i = 0; i < Object.keys(result).length; i++) {
      var node = {
        "name": Object.keys(result)[i],
        "children": [
          {
            "name": Object.keys(result)[i],
            "size": result[Object.keys(result)[i]]
          }
        ]
      }
      rootData.children.push(node);
    }
    drawWordBubble(rootData);
  },
  error: function() { console.log('Failed!'); }
});

}

analyzeTopics(data);