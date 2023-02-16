$("#multiple_parameters-before").on('click', function() {
    var st = $("#start_time").val();

    if(st == "") {
        st = new Date();
    } else {
        st = new Date(st);    
    }
    st.setDate(st.getDate() - 1);
    st = dateFormat(st, "yyyy/mm/dd");

    $("#start_time").val(st);
    plot_multiple_parameters("chart");
})

$("#multiple_parameters-next").on('click', function() {
    var st = $("#start_time").val();

    if(st == "") {
        st = new Date();
    } else {
        st = new Date(st);
    }
    st.setDate(st.getDate() + 1);
    st = dateFormat(st, "yyyy/mm/dd");

    $("#start_time").val(st);
    plot_multiple_parameters("chart");
})