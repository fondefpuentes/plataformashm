$.fn.datetimepicker.Constructor.Default = $.extend({}, $.fn.datetimepicker.Constructor.Default, {
	            icons: {
	                time: 'far fa-clock',
	                date: 'far fa-calendar-alt',
	                up: 'fas fa-arrow-up',
	                down: 'fas fa-arrow-down',
	                previous: 'fas fa-chevron-left',
	                next: 'fas fa-chevron-right',
	                today: 'far fa-calendar-check',
	                clear: 'fas fa-trash',
	                close: 'fas fa-times'
	            } });

$(function () {
    $('#datetimepicker4').datetimepicker({
        format: 'YYYY-MM-DD',
        useCurrent: false
    });
});

        $(function () {
    $('#datetimepicker2').datetimepicker({
        format: 'YYYY-MM-DD',

    });
});

$(function () {
    $('#datetimepicker3').datetimepicker({
        format: 'HH:mm',
    });
});

        $(function () {
    $('#datetimepicker1').datetimepicker({
        format: 'HH:mm',
    });
});


$(function () {
    $('#datetimepicker2').datetimepicker();
    $('#datetimepicker4').datetimepicker({
        useCurrent: false
    });
    $("#datetimepicker2").on("change.datetimepicker", function (e) {
        $('#datetimepicker4').datetimepicker('minDate', e.date);
    });
    $("#datetimepicker4").on("change.datetimepicker", function (e) {
        $('#datetimepicker2').datetimepicker('maxDate', e.date);
    });
});