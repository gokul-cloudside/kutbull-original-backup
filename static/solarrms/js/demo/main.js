var app = angular.module("ticketingApp", ["ngRoute", "ngCookies", "ngSanitize", "ngCsv", "nvd3", "ui.bootstrap", "datatables", "ngResource", "ngToast", "angular-spinkit"]);

/*app.run(['$rootScope', '$location', 'Auth', '$cookies', function ($rootScope, $location, Auth, $cookies) {
    $rootScope.$on('$routeChangeStart', function (event) {

    	var admin = $cookies.get('user_is_admin');

    	var location = $location.url();

        if (!Auth.isLoggedIn()) {
            $location.path('/');
        } else {
            if(admin == "false" && location == "/metadata") {
            	$location.path('/home');
            }
        }
    });

}]);

app.factory('Auth', function($window) {
	var token;

	return {
	    setToken : function(aToken) {
	    	$window.localStorage.setItem('curToken', JSON.stringify(aToken));
			this.currentToken = $window.localStorage.getItem('curToken');

	        token = this.currentToken;
	    },
	    isLoggedIn : function() {
	    	token = $window.localStorage.getItem('curToken');

	        return(token)? token : false;
	    }
	}
})*/

app.config(function ($routeProvider, $locationProvider) {
	$routeProvider
		.when('/', {
			controller: 'LoginController',
			templateUrl: '/static/app/app/login.html'
		})
		.when('/metadata', {
			controller: 'TableController',
			templateUrl: '/static/app/app/table.html',
			isAdmin: true
		})
		.when('/home', {
			controller: 'HomeController',
			templateUrl: '/static/app/app/home.html'
		})
		.when('/lab', {
			controller: 'LabController',
			templateUrl: '/static/app/app/lab.html'
		})
		.otherwise({
			redirectTo: '/'
		});
});
