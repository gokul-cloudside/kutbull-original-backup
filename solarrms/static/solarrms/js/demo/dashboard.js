
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
    skyconsOptions = {
        "color": "#3bb5e8",
        "resizeClear": true
    };

    /* Main Icon */
    var skycons = new Skycons(skyconsOptions);
    skycons.add("demo-weather-xs-icon", Skycons.WIND);
    skycons.play();


    // PANEL OVERLAY
    // =================================================================
    // Require Nifty js
    // -----------------------------------------------------------------
    // http://www.themeon.net
    // =================================================================


    $('#power-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');

        relTime = setInterval(function(){
            $el.niftyOverlay('hide');
            clearInterval(relTime);
        },2000);
    });

    $('#weekpower-panel-network-refresh').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');

        relTime = setInterval(function(){
            $el.niftyOverlay('hide');
            clearInterval(relTime);
        },2000);
    });

    $('#weekpower-panel-network-update').niftyOverlay().on('click', function(){
        var $el = $(this), relTime;

        $el.niftyOverlay('show');

        relTime = setInterval(function(){
            $el.niftyOverlay('hide');
            clearInterval(relTime);
        },2000);
    });

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
    var skycons = new Skycons(
    {
        color : '#fff',
        resizeClear : true
    });
    skycons.add("demo-weather-md-icon-1", Skycons.PARTLY_CLOUDY_DAY);
    skycons.play();



    /* Small Icons*/
    var skycons2 = new Skycons(skyconsOptions);
    skycons2.add("demo-weather-md-icon-2", Skycons.CLOUDY);
    skycons2.play();



    var skycons3 = new Skycons(skyconsOptions);
    skycons3.add("demo-weather-md-icon-3", Skycons.WIND);
    skycons3.play();



    var skycons4 = new Skycons(skyconsOptions);
    skycons4.add("demo-weather-md-icon-4", Skycons.RAIN);
    skycons4.play();



    var skycons5 = new Skycons(skyconsOptions);
    skycons5.add("demo-weather-md-icon-5", Skycons.PARTLY_CLOUDY_DAY);
    skycons5.play();
});