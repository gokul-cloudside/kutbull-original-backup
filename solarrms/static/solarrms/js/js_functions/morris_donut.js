function morris_donut_chart(data, div_name, colors) {

    Morris.Donut({
        element: div_name,
        data: data,
        colors: colors,
        padding: 1,
    formatter: function (y, data) { return y + ' %' } ,

        resize:false
    });

}