// ====================================
// Constants & Config
// ====================================
const ESTADO_LABELS = {
    'pending': { class: 'bg-warning', text: 'Pendiente' },
    'completed': { class: 'bg-success', text: 'Realizada' },
    'cancelled': { class: 'bg-danger', text: 'Cancelada' }
};

let appointmentsTable;

// ====================================
// Initialization
// ====================================
$(document).ready(function() {
    console.log('Initializing appointments CRUD...');
    initializeDataTable();
    initializeEventListeners();
});

function initializeDataTable() {
    console.log('Setting up DataTable...');
    
    if ($.fn.DataTable.isDataTable('#appointments-table')) {
        $('#appointments-table').DataTable().destroy();
    }
    
    appointmentsTable = $('#appointments-table').DataTable({
        serverSide: true,
        processing: true,
        responsive: true,
        ajax: {
            url: window.APPOINTMENTS_CONFIG.apiUrl,
            type: 'GET',
            data: function(d) {
                const params = {
                    draw: d.draw,
                    start: d.start,
                    length: d.length,
                    'order[0][column]': d.order[0].column,
                    'order[0][dir]': d.order[0].dir,
                    stage: $('#stage-filter').val() || '',
                    date: $('#date-filter').val() || '',
                    status: $('#status-filter').val() || ''
                };
                console.log('DataTables request params:', params);
                return params;
            },
            beforeSend: function() {
                console.log('Making AJAX request...');
            },
            success: function(response) {
                console.log('Received response:', response);
            },
            error: function(xhr, error, thrown) {
                console.error('AJAX Error:', {xhr, error, thrown});
                handleAjaxError(xhr);
            }
        },
        columns: [
            {
                data: 'date',
                render: function(data) {
                    return data ? moment(data).format('DD/MM/YYYY') : '';
                }
            },
            {
                data: 'date',
                render: function(data) {
                    return data ? moment(data).format('HH:mm') : '';
                }
            },
            {
                data: 'visitor_name',
                render: function(data, type, row) {
                    return `
                        <div>
                            <div class="fw-bold">${data || ''}</div>
                            <small class="text-muted">${row.visitor_email || ''}</small>
                        </div>
                    `;
                }
            },
            { 
                data: 'stage_name',
                defaultContent: ''
            },
            {
                data: 'status',
                render: function(data) {
                    const status = ESTADO_LABELS[data] || { class: 'bg-secondary', text: data || 'N/A' };
                    return `<span class="badge ${status.class}">${status.text}</span>`;
                }
            },
            {
                data: 'id',
                orderable: false,
                render: function(data) {
                    if (!data) return '';
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary edit-appointment" 
                                    data-id="${data}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger delete-appointment" 
                                    data-id="${data}" title="Eliminar">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    `;
                }
            }
        ],
        drawCallback: function(settings) {
            console.log('Table redrawn:', settings);
        },
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json'
        },
        order: [[0, 'desc']]
    });
}

// ====================================
// Event Listeners
// ====================================
function initializeEventListeners() {
    // Filters
    $('#stage-filter, #date-filter, #status-filter').on('change', function() {
        console.log('Filter changed');
        appointmentsTable.ajax.reload();
    });

    // Reset filters
    $('#reset-filters').on('click', function() {
        $('#stage-filter, #status-filter').val('');
        $('#date-filter').val('');
        appointmentsTable.ajax.reload();
    });

    // CRUD Operations
    $(document).on('click', '.edit-appointment', function() {
        const id = $(this).data('id');
        loadAppointment(id);
    });

    $(document).on('click', '.delete-appointment', function() {
        const id = $(this).data('id');
        confirmDelete(id);
    });

    $('#saveAppointment').on('click', saveAppointment);
}

// ====================================
// CRUD Operations
// ====================================
function loadAppointment(id) {
    $.ajax({
        url: `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/`,
        type: 'GET',
        success: function(response) {
            console.log('Loaded appointment:', response);
            populateForm(response);
            $('#appointmentModal').modal('show');
        },
        error: handleAjaxError
    });
}

function saveAppointment() {
    if (!$('#appointmentForm').valid()) return;

    const formData = new FormData($('#appointmentForm')[0]);
    const id = $('#appointment_id').val();

    $.ajax({
        url: id ? `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/` : window.APPOINTMENTS_CONFIG.apiUrl,
        type: id ? 'PUT' : 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
        },
        success: function(response) {
            console.log('Saved appointment:', response);
            $('#appointmentModal').modal('hide');
            appointmentsTable.ajax.reload();
            showToast('Cita guardada correctamente');
        },
        error: handleAjaxError
    });
}

function confirmDelete(id) {
    if (confirm('¿Está seguro de que desea eliminar esta cita?')) {
        $.ajax({
            url: `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/`,
            type: 'DELETE',
            headers: {
                'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
            },
            success: function() {
                appointmentsTable.ajax.reload();
                showToast('Cita eliminada correctamente');
            },
            error: handleAjaxError
        });
    }
}

// ====================================
// Utility Functions
// ====================================
function handleAjaxError(xhr) {
    console.error('Ajax error:', xhr);
    const message = xhr.responseJSON?.error || 'Ha ocurrido un error';
    showToast(message, 'error');
}

function showToast(message, type = 'success') {
    Toastify({
        text: message,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: type === 'success' ? '#198754' : '#dc3545',
        stopOnFocus: true
    }).showToast();
}

function populateForm(data) {
    $('#appointmentForm')[0].reset();
    $('#appointment_id').val(data.id);

    Object.keys(data).forEach(key => {
        const input = $(`#${key}`);
        if (input.length) {
            if (input.attr('type') === 'date') {
                input.val(moment(data[key]).format('YYYY-MM-DD'));
            } else if (input.attr('type') === 'time') {
                input.val(moment(data[key]).format('HH:mm'));
            } else {
                input.val(data[key]);
            }
        }
    });
}