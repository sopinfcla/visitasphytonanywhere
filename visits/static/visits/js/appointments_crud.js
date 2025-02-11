// ====================================
// Constants & Config
// ====================================
const ESTADO_LABELS = {
    'pending': { class: 'bg-warning', text: 'Pendiente' },
    'completed': { class: 'bg-success', text: 'Realizada' },
    'cancelled': { class: 'bg-danger', text: 'Cancelada' }
};

let appointmentsTable;
let searchTimeout;
let currentXhr;

// ====================================
// Initialization
// ====================================
$(document).ready(function() {
    console.log('Initializing appointments CRUD...');
    initializeDataTable();
    initializeEventListeners();
    initializeValidation();
    initializeStyles();
});

function initializeStyles() {
    console.log('Initializing custom styles...');
    const style = document.createElement('style');
    style.textContent = `
        .dataTables_processing {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            padding: 1em;
            background: rgba(255,255,255,0.9);
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            z-index: 100;
            transition: opacity 0.3s;
        }
        .dataTables_processing.hidden {
            opacity: 0;
            pointer-events: none;
        }
        .modal-backdrop {
            z-index: 1040;
        }
        .modal {
            z-index: 1050;
        }
    `;
    document.head.appendChild(style);
}

// ====================================
// DataTable Configuration
// ====================================
function initializeDataTable() {
    console.log('Setting up DataTable...');
    
    if ($.fn.DataTable.isDataTable('#appointments-table')) {
        console.log('Destroying existing DataTable...');
        $('#appointments-table').DataTable().destroy();
    }
    
    appointmentsTable = $('#appointments-table').DataTable({
        serverSide: true,
        processing: true,
        responsive: true,
        searching: true,
        search: {
            smart: true
        },
        ajax: {
            url: window.APPOINTMENTS_CONFIG.apiUrl,
            type: 'GET',
            beforeSend: function(jqXHR) {
                if (currentXhr) {
                    currentXhr.abort();
                }
                currentXhr = jqXHR;
            },
            data: function(d) {
                const filters = {
                    draw: d.draw,
                    start: d.start,
                    length: d.length,
                    order: [{
                        column: d.order[0].column,
                        dir: d.order[0].dir
                    }],
                    search: $('.dataTables_filter input').val(),
                };
                
                const stage = $('#stage-filter').val();
                const date = $('#date-filter').val();
                const status = $('#status-filter').val();
                
                if (stage) filters.stage = stage;
                if (date) filters.date = date;
                if (status) filters.status = status;
                
                console.log('DataTable filter params:', filters);
                return filters;
            }
        },
        columns: [
            { 
                data: 'date',
                orderable: true,
                render: function (data) {
                    return data ? moment(data).format('DD/MM/YYYY') : '';
                }
            },
            { 
                data: 'date',
                orderable: true,
                render: function (data) {
                    return data ? moment(data).format('HH:mm') : '';
                }
            },
            { 
                data: 'visitor_name',
                orderable: true,
                render: function (data, type, row) {
                    return `
                        <div>
                            <div class="fw-bold">${data || ''}</div>
                            <small class="text-muted">${row.visitor_email || ''}</small>
                        </div>
                    `;
                }
            },
            { data: 'stage_name', orderable: true },
            { 
                data: 'status',
                orderable: true,
                render: function (data) {
                    const status = ESTADO_LABELS[data] || { class: 'bg-secondary', text: data || 'N/A' };
                    return `<span class="badge ${status.class}">${status.text}</span>`;
                }
            },
            { 
                data: 'id',
                orderable: false,
                render: function (data) {
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary edit-appointment" data-id="${data}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-danger delete-appointment" data-id="${data}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    `;
                }
            }
        ],
        language: {
            processing: "Procesando...",
            search: "Buscar:",
            lengthMenu: "Mostrar _MENU_ registros",
            info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
            infoEmpty: "Mostrando 0 a 0 de 0 registros",
            infoFiltered: "(filtrado de _MAX_ registros totales)",
            infoPostFix: "",
            loadingRecords: "Cargando...",
            zeroRecords: "No se encontraron registros",
            emptyTable: "No hay citas disponibles",
            paginate: {
                first: "Primero",
                previous: "Anterior",
                next: "Siguiente",
                last: "Último"
            },
            aria: {
                sortAscending: ": activar para ordenar columna ascendente",
                sortDescending: ": activar para ordenar columna descendente"
            }
        },
        order: [[0, 'desc'], [1, 'desc']]
    });

    $('.dataTables_filter input').off().on('input', function() {
        console.log('Search input changed:', this.value);
        appointmentsTable.search(this.value).draw();
    });

    let processingTimeout;
    appointmentsTable.on('processing.dt', function(e, settings, processing) {
        clearTimeout(processingTimeout);
        
        if (processing) {
            processingTimeout = setTimeout(() => {
                $('.dataTables_processing').removeClass('hidden');
            }, 300);
        } else {
            $('.dataTables_processing').addClass('hidden');
        }
    });
}

// ====================================
// Event Listeners
// ====================================
function initializeEventListeners() {
    console.log('Initializing event listeners...');

    $('#stage-filter, #date-filter, #status-filter').on('change', function() {
        console.log(`Filter changed: ${this.id} = ${this.value}`);
        appointmentsTable.ajax.reload();
    });

    $('#reset-filters').on('click', function() {
        console.log('Resetting filters...');
        $('#stage-filter, #status-filter').val('');
        $('#date-filter').val('');
        appointmentsTable.ajax.reload();
    });

    $(document).on('click', '.edit-appointment', function() {
        const id = $(this).data('id');
        console.log('Edit appointment clicked:', id);
        loadAppointment(id);
    });

    $(document).on('click', '.delete-appointment', function() {
        const id = $(this).data('id');
        console.log('Delete appointment clicked:', id);
        confirmDelete(id);
    });

    $('#saveAppointment').on('click', function(e) {
        console.log('Save appointment button clicked');
        e.preventDefault();
        saveAppointment();
    });

    $('#appointmentForm').on('submit', function(e) {
        console.log('Form submit prevented');
        e.preventDefault();
    });
    
    $('#appointmentModal').on('hidden.bs.modal', function (e) {
        console.log('Modal hidden event triggered');
        cleanupModal();
    });

    $('#appointmentModal').on('shown.bs.modal', function () {
        console.log('Modal shown event triggered');
    });
}

// ====================================
// Form Validation
// ====================================
function initializeValidation() {
    console.log('Initializing form validation...');
    
    $('#appointmentForm').validate({
        rules: {
            visitor_name: "required",
            visitor_email: {
                required: true,
                email: true
            },
            visitor_phone: {
                required: true,
                digits: true,
                minlength: 9,
                maxlength: 9
            },
            stage: "required",
            date: "required",
            time: "required",
            status: "required",
            duration: "required"
        },
        messages: {
            visitor_name: "Por favor, ingrese el nombre del visitante",
            visitor_email: {
                required: "Por favor, ingrese un email",
                email: "Por favor, ingrese un email válido"
            },
            visitor_phone: {
                required: "Por favor, ingrese un teléfono",
                digits: "Solo se permiten números",
                minlength: "El teléfono debe tener 9 dígitos",
                maxlength: "El teléfono debe tener 9 dígitos"
            },
            stage: "Por favor, seleccione una etapa",
            date: "Por favor, seleccione una fecha",
            time: "Por favor, seleccione una hora",
            status: "Por favor, seleccione un estado",
            duration: "Por favor, seleccione una duración"
        },
        errorElement: 'span',
        errorPlacement: function (error, element) {
            error.addClass('invalid-feedback');
            element.closest('.mb-3').append(error);
        },
        highlight: function (element) {
            $(element).addClass('is-invalid');
        },
        unhighlight: function (element) {
            $(element).removeClass('is-invalid');
        }
    });
}

// ====================================
// CRUD Operations
// ====================================
function loadAppointment(id) {
    console.log('Loading appointment:', id);
    
    $.ajax({
        url: `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/`,
        type: 'GET',
        success: function(response) {
            console.log('Loaded appointment data:', response);
            populateForm(response);
            $('#appointmentModal').modal('show');
        },
        error: handleAjaxError
    });
}

function saveAppointment() {
    console.log('Starting saveAppointment...');
    
    const form = $('#appointmentForm');
    if (!form.valid()) {
        console.log('Form validation failed');
        return;
    }

    const formData = {};
    const id = $('#appointment_id').val();
    console.log('Appointment ID:', id);
     
    const dateValue = $('#date').val();
    const timeValue = $('#time').val();
    if (dateValue && timeValue) {
        formData.date = `${dateValue}T${timeValue}`;
    }
    console.log('Date value:', formData.date);
    
    // Capturar todos los campos incluyendo duración y comentarios
    ['visitor_name', 'visitor_email', 'visitor_phone', 'stage', 'status', 'duration', 'comments'].forEach(field => {
        const value = $(`#${field}`).val();
        if (value !== undefined && value !== null) {
            formData[field] = (field === 'duration') ? parseInt(value) : value;
        }
        console.log(`Field ${field}:`, value);
    });

    // Validación de duración (solo 30, 45 y 60 permitidos)
    const allowedDurations = [30, 45, 60];
    if (isNaN(formData.duration) || !allowedDurations.includes(formData.duration)) {
        console.log('Invalid duration:', formData.duration);
        showToast('Por favor, seleccione una duración válida (30, 45 o 60 minutos)', 'error');
        return;
    }

    if (!formData.date || !formData.visitor_name || !formData.visitor_email || 
        !formData.visitor_phone || !formData.stage || !formData.duration) {
        console.log('Missing required fields:', formData);
        showToast('Por favor, complete todos los campos requeridos', 'error');
        return;
    }

    const saveBtn = $('#saveAppointment');
    const modal = $('#appointmentModal');
    
    console.log('Sending data to server:', formData);
    
    $.ajax({
        url: id ? `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/` : window.APPOINTMENTS_CONFIG.apiUrl,
        type: id ? 'PUT' : 'POST',
        data: JSON.stringify(formData),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
        },
        beforeSend: function() {
            console.log('Disabling save button');
            saveBtn.prop('disabled', true);
        },
        success: function(response) {
            console.log('Server response:', response);
            appointmentsTable.ajax.reload();
            showToast('Cita guardada correctamente');
            console.log('Attempting to close modal...');
            modal.modal('hide');
            cleanupModal();
            saveBtn.prop('disabled', false);  
        },
        error: function(xhr) {
            console.error('Server error:', xhr);
            const errorMessage = xhr.responseJSON?.error || 'Error al guardar la cita';
            showToast(errorMessage, 'error');
            saveBtn.prop('disabled', false);
        }
    });
}

function confirmDelete(id) {
    if (confirm('¿Está seguro de que desea eliminar esta cita?')) {
        console.log('Deleting appointment:', id);
        
        $.ajax({
            url: `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/`,
            type: 'DELETE',
            headers: {
                'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
            },
            success: function() {
                console.log('Appointment deleted successfully');
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
    console.log(`Showing toast: ${message} (${type})`);
    Toastify({
        text: message,
        duration: 3000,
        gravity: "top",
        position: "right",
        style: { background: type === 'success' ? '#198754' : '#dc3545' },
        stopOnFocus: true
    }).showToast();
}

function cleanupModal() {
    console.log('Cleaning up modal...');
    $('#appointmentForm')[0].reset();
    $('#appointment_id').val('');
    $('#appointmentForm').validate().resetForm();
    $('.is-invalid').removeClass('is-invalid');
    $('body').removeClass('modal-open');
    $('.modal-backdrop').remove();
    $('html').removeClass('modal-open');
    $('body').css('padding-right', '');
}

function populateForm(data) {
    console.log('Populating form with data:', data);
    
    $('#appointmentForm')[0].reset();
    $('#appointment_id').val(data.id);
    
    if (data.date) {
        const datetime = moment(data.date);
        $('#date').val(datetime.format('YYYY-MM-DD'));
        $('#time').val(datetime.format('HH:mm'));
        console.log('Date/Time set to:', datetime.format('YYYY-MM-DD HH:mm'));
    }
    
    ['visitor_name', 'visitor_email', 'visitor_phone', 'stage', 'status', 'duration', 'comments'].forEach(field => {
        const value = data[field];
        if (value !== undefined && value !== null) {
            console.log(`Setting ${field} to:`, value);
            $(`#${field}`).val(field === 'duration' ? value.toString() : value);
        } else {
            console.log(`No value for ${field}`);
        }
    });
}