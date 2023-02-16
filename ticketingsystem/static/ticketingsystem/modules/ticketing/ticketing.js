'use strict';

angular.module('modules.ticketing', ['ngRoute'])

.config(['$routeProvider', function($routeProvider) {
  $routeProvider.when('/tickets', {
    templateUrl: 'ticketing.html',
    controller: 'TicketingCtrl'
  });
}])

.controller('TicketingCtrl', [function() {

}]);