/*jslint
 white: true,
 browser: true,
 devel: false,
 forin: true,
 vars: true,
 nomen: true,
 plusplus: true,
 bitwise: false,
 regexp: true,
 sloppy: true,
 stupid: false,
 indent: 4,
 maxerr: 25,
 todo: true
 */
/*global
 $,
 alert
 */
function update_instance(elem) {
    elem.load(elem.data('url'));
}

function genFlash(msg) {
    var d = '<div class="alert alert-danger">';
    d += msg;
    d += '<button type="button" class="close" aria-label="Close">\
                  <span aria-hidden="true">&times;</span>\
              </button>';
    d += '</div>';

    return d;
}

function flash(msg) {
    $('.content').prepend(genFlash(msg));
}

function genAlert(msg) {
    var d = '<div class="alert alert-danger">';
    d += msg;
    d += '<button type="button" class="close" aria-label="Close">\
                  <span aria-hidden="true">&times;</span>\
              </button>';
    d += '</div>';

    return d;
}

function render_loading_template() {
    var html = '<div class="d-block text-center"> \
                    <h5>Working  <i class="fa fa-spinner fa-pulse fa-fw"></i></h5> \
                </div>';
    return html;
}

$(function () {

    $(document).on('click', '.instance-button', function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        var e = $(this);
        var d = e.parents('.instance-box');
        var action = $(this).data('type');

        // Close all tooltips
        $('[data-tooltip="tooltip"]').tooltip('hide');

        var instance_id = $(this).parents('.instance-box').data('id');
        var lab_id = $(this).parents('.instance-box').data('lab-id');
        var url = '/api/instance/' + action;
        var data = {instance_id: instance_id, lab_id: lab_id};

        if (action !== 'get_vnc') {
            e.parents('.instance-box').html(render_loading_template());
        }

        $.post(url, data, function (data) {
                if (data.success) {
                    if (action === 'get_vnc') {
                        window.open(data.vnc);
                    }
                } else {
                    alert(data.feedback);
                }

                if (action !== 'get_vnc') {
                    update_instance(d);
                }
            }
        );
    });

    // Redirect on button click
    $(document).on('click', 'button[data-url]', function () {
        window.location.href = $(this).data('url');
    });

    // Hide parent when close button is pressed
    $(document).on('click', 'button.close', function () {
        $(this).parent().slideUp();
    });

    // Enable tooltips
    $('[data-toggle="tooltip"]').tooltip();
    // Enable tooltips
    $('[data-tooltip="tooltip"]').tooltip();

});