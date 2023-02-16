
// Dashboard.js
// ====================================================================
// This file should not be included in your project.
// This is just a sample how to initialize plugins or components.
//
// - ThemeOn.net -

$(window).on('load', function() {

    // EXTRA SMALL WEATHER WIDGET
    // =================================================================
    // Require sckycons
    // -----------------------------------------------------------------
    // http://darkskyapp.github.io/skycons/
    // =================================================================

    // on Android, a nasty hack is needed: {"resizeClear": true}
    
    var month = ["January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    var d = new Date();
    $("#todays_date").append(d.toString());

    /*skyconsOptions = {
        "color": "#3bb5e8",
        "resizeClear": true
    };*/

    /* Main Icon */
    /*var skycons = new Skycons(skyconsOptions);
    skycons.add("demo-weather-xs-icon", Skycons.WIND);
    skycons.play();*/

    // PANEL OVERLAY
    // =================================================================
    // Require Nifty js
    // -----------------------------------------------------------------
    // http://www.themeon.net
    // =================================================================


    $('#daypower-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        power_data();
        $el.niftyOverlay('hide');
        $('#daypower-panel-network-update').prop('disabled', false);
    });

    $('#daypower-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        power_data();
        $el.niftyOverlay('hide');
        $('#daypower-panel-network-refresh').prop('disabled', false);
    });

    $('#weekpower-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_power_data();
        $el.niftyOverlay('hide');
        $('#weekpower-panel-network-refresh').prop('disabled', false);
    });

    $('#weekpower-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_power_data();
        $el.niftyOverlay('hide');
        $('#weekpower-panel-network-update').prop('disabled', false);
    });

    $('#dayenergy-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_energy_data();
        $el.niftyOverlay('hide');
    });


    $('#dayenergy-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#weekenergy-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#weekenergy-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#monthenergy-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#monthenergy-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#yearenergy-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        year_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#yearenergy-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        year_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#yearenergy-panel-network-summary-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        year_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#yearenergy-panel-network-summary-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        year_energy_data();
        $el.niftyOverlay('hide');
    });

    $('#dayperformance_ratio-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_performance_ratio_data();
        $el.niftyOverlay('hide');
    });


    $('#dayperformance_ratio-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_performance_ratio_data();
        $el.niftyOverlay('hide');
    });

    $('#weekperformance_ratio-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_performance_ratio_data();
        $el.niftyOverlay('hide');
    });

    $('#weekperformance_ratio-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_performance_ratio_data();
        $el.niftyOverlay('hide');
    });

    $('#monthperformance_ratio-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_performance_ratio_data();
        $el.niftyOverlay('hide');
    });

    $('#monthperformance_ratio-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_performance_ratio_data();
        $el.niftyOverlay('hide');
    });

    $('#daycuf-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_cuf_data();
        $el.niftyOverlay('hide');
    });


    $('#daycuf-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        day_cuf_data();
        $el.niftyOverlay('hide');
    });

    $('#weekcuf-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_cuf_data();
        $el.niftyOverlay('hide');
    });

    $('#weekcuf-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        week_cuf_data();
        $el.niftyOverlay('hide');
    });

    $('#monthcuf-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_cuf_data();
        $el.niftyOverlay('hide');
    });

    $('#monthcuf-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        month_cuf_data();
        $el.niftyOverlay('hide');
    });

    /*$('#inverterpower-panel-network-plot').niftyOverlay().on('click', function(){

        var $el = $(this), relTime;

        $el.niftyOverlay('show');
        console.log("spinner on");
        plant_inverters();
        $el.niftyOverlay('hide');
    });*/

    $('#download-inverters-data').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        plant_inverters();
    });

    $('#download-groups-data').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        groups_chart();
    });

    $('#summary_report-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        summary_for_date();
    });

    $('#summary_client-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        summary_client_date();
    });

    $.noty.defaults = {
        layout: 'topRight',
        theme: 'relax',
        type: 'success',
        text: '', // can be html or string

        dismissQueue: true, // [boolean] If you want to use queue feature set this true
        force: false, // [boolean] adds notification to the beginning of queue when set to true
        maxVisible: 5, // [integer] you can set max visible notification count for dismissQueue true option,

        progressBar: true,
        template: '<div class="noty_message"><span class="noty_text"></span><div class="noty_close"></div></div>',
        closeWith: ['click', 'button', 'backdrop'],
        animation: {
            open: {height: 'toggle'},
            close: {height: 'toggle'},
            easing: 'swing',
            speed: 500 // opening & closing animation speed
        },
        callback: {
            onShow: function() {},
            afterShow: function() {},
            onClose: function() {},
            afterClose: function() {}
        },

    };
    // WEATHER WIDGET
    // =================================================================
    // Require sckycons
    // -----------------------------------------------------------------
    // http://darkskyapp.github.io/skycons/
    // =================================================================

    // on Android, a nasty hack is needed: {"resizeClear": true}
    /*skyconsOptions = {
        "color": "#337ab7",
        "resizeClear": true
    }*/
    /* Main Icon */

});