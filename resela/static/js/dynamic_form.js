/**
 * Created by jiah on 2017-03-22.
 * Copyright 2017 resesla
 */


$(document).on('submit', 'form', function (e) {
    e.preventDefault();
    e.stopImmediatePropagation();

    var form = $(this);
    var url = form.attr('action');
    var ct = form.attr('enctype') == undefined ?
        'application/x-www-form-urlencoded; charset=UTF-8' :
        false;

    // Reset progress bars
    $('.progress-bar').show();
    $('.progress-bar').css('width', 0 + "%");

    // Disable buttons
    form.find('button').each(function(){
        $(this).attr('disabled', true);
    });

    $.ajax({
        url: url,
        type: 'POST',
        data: ct == false ? new FormData(form[0]) : form.serialize(),
        async: true,
        cache: false,
        contentType: ct,
        processData: !!ct,
        dataType: 'json',
        xhr: function () {
            var xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener('progress', function (evt) {
                if (evt.lengthComputable) {
                    var percentComplete = evt.loaded / evt.total;
                    percentComplete = parseInt(percentComplete * 100);
                    $('.progress-bar').css('width', percentComplete + "%");
                    $('.progress-bar').html(percentComplete + "%");
                    if (percentComplete === 100) {
                        $('.progress-bar').hide();
                        $('.loading').show();
                    }
                }
            }, false);
            return xhr;
        },
        success: function (data) {
            if (data.success) {
                if (data.hasOwnProperty('redirect') && data.redirect !== '')
                    window.location.href = data.redirect;
                else
                    window.location.reload();
            } else {
                form.parents('.modal-body').prepend(genAlert(data.feedback));
            }
            $('.loading').hide();
            // Undisable buttons
            form.find('button').each(function(){
                $(this).attr('disabled', false);
            });
        }
    });
});