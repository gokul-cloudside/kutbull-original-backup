$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Plants</a></li>')
    plant_user_add_remove();

});

$("#add_user-button").click(function() {

    var fname = $("#first_name").val();
    var lname = $("#last_name").val();
    var user_email = $("#user_email").val();
    var urole = $("#user_role").val();
    var user_password = $("#user_password").val();
    var confirm_password = $("#confirm_user_password").val();

    var user_info = {
        "first_name": fname,
        "last_name": lname, 
        "email": user_email, 
        "password": user_password, 
        "confirm_password": confirm_password, 
        "user_role": urole
    }

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: "/api/v1/solar/users/",
        data: JSON.stringify(user_info),
        success: function(data){
            
            console.log(data);

            noty_message("User Created Successfully!", 'success', 5000)
            return;

        },
        error: function(error_response){
            console.log(error_response);

            noty_message(error_response.responseJSON + "!", 'error', 5000)
            return;
        }
    });

});

var slug_info = "";

function plant_user_add_remove() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/organization_users/",
        success: function(plants_details){

            console.log(plants_details);

            if(plants_details == "") {
                noty_message("No plants are present!", 'information', 5000)
                return;
            } else {

                $("#plant_users_add_remove").empty();
                $("#plant_users_add_remove").append('<table id="user_table" class="display" cellspacing="0" width="100%"><thead id="filter_users"><tr><th class="text-center" style="width: 10%;">Plant</th><th class="text-center" style="width: 80%;">Users</th><th class="text-center" style="width: 10%;"></th></tr></thead><tbody id="user_row"><tbody></table>');

                for(var plant_info in plants_details) {

                    var plant_user_name = "";

                    for(var plant_user = 0; plant_user < plants_details[plant_info].length; plant_user++) {
                        if(plant_user != 0) {
                            plant_user_name = plant_user_name + "," + plants_details[plant_info][plant_user].user_name + " : " + plants_details[plant_info][plant_user].role;
                        } else {
                            plant_user_name = plant_user_name + plants_details[plant_info][plant_user].user_name + " : " + plants_details[plant_info][plant_user].role;
                        }
                    }

                    $("#user_row").append("<tr><td class='text-center' id='" + plant_info + "'><span>" + plant_info + "</span></td><td><div class='col-lg-12 col-md-12 col-sm-12'><input type='text' class='form-control' id='user_names"+plant_info+"' value='" + plant_user_name + "' data-role='tagsinput'></div></td><td><span class='pull-right'><span class='pad-lft pad-top pad-btm'><button class='btn btn-primary btn-icon btn-circle' id='add_user_to_"+plant_info+"' name='"+plant_info+"' data-placement='top' title='Add User to Plants' data-toggle='modal' data-target='#add_user_modal'><i class='fa fa-plus' aria-hidden='true'></i></button></span></span></td></tr>");
                    /*$("#user_row").append("<tr><td class='text-center' id='" + plant_info + "'><span>" + plant_info + "</span></td><td><div class='col-lg-12 col-md-12 col-sm-12'><input type='text' class='form-control' id='user_names"+plant_info+"' value='" + plant_user_name + "' data-role='tagsinput'></div></td><td><span class='pull-right'><span class='pad-lft pad-top pad-btm'><button class='btn btn-primary btn-icon btn-circle' id='add_user_to_"+plant_info+"' name='"+plant_info+"' data-placement='top' title='Add User to Plants' data-toggle='modal' data-target='#add_user_modal'><i class='fa fa-plus' aria-hidden='true'></i></button></span><span class='pad-top pad-btm pad-lft'><button class='btn btn-danger btn-icon btn-circle' id='delete_user_from_"+plant_info+"' data-toggle='tooltip' data-placement='top' title='Delete User'><i class='fa fa-floppy-o' aria-hidden='true'></i></button></span></span></td></tr>");*/

                    $("#add_user_to_"+plant_info).click(function() {

                        console.log("add button clicked");

                        var slug = $(this).attr('name');
                        console.log(slug);

                        slug_info = slug;

                        $(".modal-body").empty();
                        $(".modal-body").append('<form>' +
                                                    '<div class="form-group">' +
                                                        '<label for="recipient-name" class="control-label">User Email:</label>' +
                                                        '<input type="email" class="form-control" id="recipient-email_'+slug+'" name="recipient-email" placeholder="user@gmail.com" required="required">' +
                                                    '</div>' +
                                                '</form>');

                        $(".modal-footer").empty();
                        $(".modal-footer").append('<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +
                                                '<button type="button" class="btn btn-primary" id="add_user_to_this_plant_'+slug+'" name="'+slug+'" onClick="add_user_to_this_plant()">Add</button>');

                    });

                    $("#user_names"+plant_info).tagsinput({
                        allowDuplicates: false
                    });

                }

                // DataTable
                var table = $('#user_table').DataTable({
                    "language": {
                        "search": "Search or Filter"
                    },
                    "columns": [
                        {"name": "first", "orderable": true},
                        {"name": "second", "orderable": false},
                        {"name": "third", "orderable": false}
                    ]
                });

                // Apply the search
                table.columns().every( function () {
                    var that = this;
                    
                    console.log(this);

                    $( 'input', this.footer() ).on( 'keyup change', function () {
                        if ( that.search() === this.value ) {
                            that
                                .search( this.value )
                                .draw();
                        }
                    } );
                });

            }

        },
        error: function(data){
            console.log("no data");

            console.log(data);

            noty_message("No plants are present!", 'error', 5000)
            return;
        }
    });

}

function add_user_to_this_plant() {

    console.log("add user");

    var slug_name = slug_info;
    var user_email = $("#recipient-email_"+slug_info).val();

    console.log(user_email);
    console.log(slug_name);

    var user = {
        "email": user_email,
        "plant_slug": slug_name
    }

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: "/api/v1/solar/organization_users/",
        data: JSON.stringify(user),
        success: function(data){
            
            console.log(data);

        },
        error: function(data){
            console.log(data);

            noty_message(data + "!", 'error', 5000)
            return;
        }
    });

    $("#add_user_modal").modal('hide');
    plant_user_add_remove();

}

$(".bootstrap-tagsinput").on("change", function() {

    var user_present = $("#user_names").val();
    console.log(user_present);

})

function plant_preferences_add_remove() {

	$("#plant_preferences_add_remove").empty();
	$("#plant_preferences_add_remove").append('<table id="preference_table" class="display" cellspacing="0" width="100%"><thead id="filter_preferences"><tr><th class="text-center" style="width: 30%;">Plant</th><th style="width: 50%;">Preference</th><th style="width: 20%;"></th></tr></thead><tbody id="ticket_list_row"><tbody></table>');

}