/*Pass data as

for (var i = 0; i < 100; i++) {
  sin.push([ i, r1 * Math.sin( r2 +  i / (10 * (r4 + .5) ))]);
  cos.push([ i, r2 * Math.cos( r3 + i / (10 * (r3 + .5) ))]);
  sin2.push([ i, r3 * Math.sin( r1 + i / (10 * (r2 + .5) ))]);
  cos2.push([ i, r4 * Math.cos( r4 + i / (10 * (r1 + .5) ))]);
}

var d3_data = [
  {
    data: sin,
    label: "Sine Wave"
  },
  {
    data: cos,
    label: "Cosine Wave"
  },
  {
    data: sin2,
    label: "Sine2 Wave"
  },
  {
    data: cos2,
    label: "Cosine2 Wave"
  }
];*/

function d3_line_chart(div_chart, arrayData) {
  function log(text) {
    if (console && console.log) console.log(text);
    return text;
  }

  var margin = {top: 30, right: 10, bottom: 50, left: 60},
    chart = d3LineWithLegend()
              .xAxis.label('')
              .width(width(margin))
              .height(height(margin))
              .yAxis.label('Power (kW)');

  var svg = d3.select('#' + div_chart + ' svg')
    .datum(generateData())

  svg.transition().duration(500)
    .attr('width', width(margin))
    .attr('height', height(margin))
    .call(chart);

  chart.dispatch.on('showTooltip', function(e) {
      var offset = $('#d3_power').offset(), // { left: 0, top: 0 }
          left = e.pos[0] + offset.left,
          top = e.pos[1] + offset.top,
          formatter = d3.format(".04f");

      var content = '<h4>' + dateFormat(e.point[0], "dd-mm-yyyy HH:MM:ss") + '</h4>' +
                    '<p>' +
                    '<span class="value">POWER : ' + e.point[1] + '</span><br/><span class="irradiation">IRRADIATION : ' + e.point[2] +
                    '</p>';

      nvtooltip.show([left, top], content);
  });

  chart.dispatch.on('hideTooltip', function(e) {
      nvtooltip.cleanup();
  });

  $(window).resize(function() {
      
      var margin = chart.margin();

      var xScale = d3.time.scale()
          .domain([mindate, maxdate])    // values between for month of january
          .range([padding, width - padding * 2]);

      chart
      .width(width(margin))
      .height(height(margin));

      d3.select('#d3_power svg')
          .attr('width', width(margin))
          .attr('height', height(margin))
          .call(chart);

  });

  function width(margin) {
      var w = $(window).width() - 340;

      return ( (w - margin.left - margin.right - 20) < 0 ) ? margin.left + margin.right + 2 : w;
  }

  function height(margin) {
      
      var h = $(window).height() - 20;

      return ( h - margin.top - margin.bottom - 20 < 0 ) ? 
            margin.top + margin.bottom + 2 : h;
  }

//data
  function generateData() {
    
      return arrayData;

  }

}