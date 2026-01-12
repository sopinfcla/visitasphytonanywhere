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
    
    // Solo inicializar DataTable si estamos en la página de CRUD
    if ($('#appointments-table').length) {
        initializeDataTable();
    }
    
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
        #course-container {
            transition: all 0.3s ease;
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
            smart: true,
            regex: true,
            caseInsensitive: true
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
                
                return filters;
            }
        },
        columns: [
            { 
                data: 'date',
                orderable: true,
                searchable: true,
                render: function (data) {
                    const formattedDate = moment(data).format('DD/MM/YYYY');
                    return `<span data-search="${formattedDate}">${formattedDate}</span>`;
                }
            },
            { 
                data: 'date',
                orderable: true,
                searchable: true,
                render: function (data) {
                    const formattedTime = moment(data).format('HH:mm');
                    return `<span data-search="${formattedTime}">${formattedTime}</span>`;
                }
            },
            { 
                data: 'visitor_name',
                orderable: true,
                searchable: true,
                render: function (data, type, row) {
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
                orderable: true,
                searchable: true,
                render: function (data, type, row) {
                    let html = `<div><strong>${data}</strong>`;
                    if (row.course_name) {
                        html += `<br><small class="text-muted">${row.course_name}</small>`;
                    }
                    html += '</div>';
                    return html;
                }
            },
            { 
                data: 'status',
                orderable: true,
                searchable: true,
                render: function (data) {
                    const status = ESTADO_LABELS[data] || { class: 'bg-secondary', text: data || 'N/A' };
                    return `<span class="badge ${status.class}" data-search="${status.text}">${status.text}</span>`;
                }
            },
            { 
                data: 'id',
                orderable: false,
                searchable: false,
                render: function (data) {
                    return `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary edit-appointment" data-id="${data}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-outline-info download-pdf" data-id="${data}" title="Descargar PDF">
                                <i class="bi bi-file-pdf"></i>
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

    // Mejorar búsqueda para incluir fecha y estado
    $('.dataTables_filter input').off().on('input', function() {
        const searchValue = this.value;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            appointmentsTable.search(searchValue).draw();
        }, 500);
    });
}

// ====================================
// Event Listeners
// ====================================
function initializeEventListeners() {
    console.log('Initializing event listeners...');

    // Filtros (solo si existen)
    $('#stage-filter, #date-filter, #status-filter').on('change', function() {
        console.log(`Filter changed: ${this.id} = ${this.value}`);
        if (appointmentsTable) {
            appointmentsTable.ajax.reload();
        }
    });

    $('#reset-filters').on('click', function() {
        console.log('Resetting filters...');
        $('#stage-filter, #status-filter').val('');
        $('#date-filter').val('');
        if (appointmentsTable) {
            appointmentsTable.ajax.reload();
        }
    });

    // Manejar cambio de etapa para cargar cursos
    $('#stage').on('change', function() {
        const stageId = $(this).val();
        loadCoursesForStage(stageId);
    });

    // Botones de exportación (solo si existen)
    $('#exportPDF').on('click', function() {
        const exportUrl = `${window.APPOINTMENTS_CONFIG.apiUrl}export/?type=pdf`;
        window.location.href = exportUrl;
    });
    
    $('#exportExcel').on('click', function() {
        const exportUrl = `${window.APPOINTMENTS_CONFIG.apiUrl}export/?type=excel`;
        window.location.href = exportUrl;
    });
    
    // PDF individual
    $(document).on('click', '.download-pdf', function() {
        const id = $(this).data('id');
        window.location.href = `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/export/?type=pdf`;
    });

    // CRUD Operations
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
    
    $('#appointmentModal').on('hidden.bs.modal', function () {
        console.log('Modal hidden event triggered');
        cleanupModal();
    });

    // Preparar el modal según el contexto
    $('#appointmentModal').on('show.bs.modal', function () {
        // Mostrar campos avanzados si estamos en modo avanzado
        if (window.APPOINTMENTS_CONFIG.isAdvancedMode) {
            $('.advanced-fields').show();
        } else {
            $('.advanced-fields').hide();
        }
    });
}

// ====================================
// Course Management
// ====================================
function loadCoursesForStage(stageId) {
    console.log('Loading courses for stage:', stageId);
    
    const courseSelect = $('#course');
    const courseContainer = $('#course-container');
    
    // Ocultar el contenedor de cursos por defecto
    courseContainer.hide();
    courseSelect.html('<option value="">Cargando cursos...</option>');
    courseSelect.removeAttr('required');
    
    if (!stageId) {
        courseSelect.html('<option value="">Seleccione primero una etapa</option>');
        return;
    }

    // CORRECCIÓN: URL correcta sin prefijo /visits/
    const coursesUrl = `/api/stage/${stageId}/courses/`;
    
    $.ajax({
        url: coursesUrl,
        type: 'GET',
        success: function(courses) {
            console.log('Loaded courses:', courses);
            
            if (courses.length === 0) {
                // Si no hay cursos, mantener el campo oculto
                courseContainer.hide();
                courseSelect.html('<option value="">No hay cursos específicos para esta etapa</option>');
                courseSelect.removeAttr('required');
            } else {
                // Si hay cursos, mostrar el campo
                courseContainer.show();
                let options = '<option value="">Seleccione un curso</option>';
                courses.forEach(course => {
                    options += `<option value="${course.id}">${course.name}</option>`;
                });
                courseSelect.html(options);
                courseSelect.attr('required', 'required');
            }
        },
        error: function(xhr) {
            console.error('Error loading courses:', xhr);
            console.error('URL attempted:', coursesUrl);
            courseContainer.show();
            courseSelect.html('<option value="">Error cargando cursos</option>');
        }
    });
}

function loadCoursesForStageWithCallback(stageId, courseValue) {
    console.log('Loading courses for stage with callback:', stageId, courseValue);
    
    const courseSelect = $('#course');
    const courseContainer = $('#course-container');
    
    // Ocultar el contenedor de cursos por defecto
    courseContainer.hide();
    courseSelect.html('<option value="">Cargando cursos...</option>');
    courseSelect.removeAttr('required');
    
    if (!stageId) {
        courseSelect.html('<option value="">Seleccione primero una etapa</option>');
        return;
    }

    // CORRECCIÓN: URL correcta sin prefijo /visits/
    const coursesUrl = `/api/stage/${stageId}/courses/`;
    
    $.ajax({
        url: coursesUrl,
        type: 'GET',
        success: function(courses) {
            console.log('Loaded courses with callback:', courses);
            
            if (courses.length === 0) {
                // Si no hay cursos, mantener el campo oculto
                courseContainer.hide();
                courseSelect.html('<option value="">No hay cursos específicos para esta etapa</option>');
                courseSelect.removeAttr('required');
            } else {
                // Si hay cursos, mostrar el campo
                courseContainer.show();
                let options = '<option value="">Seleccione un curso</option>';
                courses.forEach(course => {
                    const selected = (courseValue && courseValue == course.id) ? 'selected' : '';
                    options += `<option value="${course.id}" ${selected}>${course.name}</option>`;
                });
                courseSelect.html(options);
                courseSelect.attr('required', 'required');
                
                // Establecer el valor si se proporcionó
                if (courseValue) {
                    courseSelect.val(courseValue);
                    console.log('Course field populated with value:', courseValue);
                }
            }
        },
        error: function(xhr) {
            console.error('Error loading courses with callback:', xhr);
            console.error('URL attempted:', coursesUrl);
            courseContainer.show();
            courseSelect.html('<option value="">Error cargando cursos</option>');
        }
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
            course: {
                required: function() {
                    // El curso es requerido solo si el contenedor es visible y hay opciones
                    return $('#course-container').is(':visible') && $('#course option').length > 1;
                }
            },
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
            course: "Por favor, seleccione un curso",
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
function loadAppointment(id, staffId = null) {
    console.log('Loading appointment:', id, 'staffId:', staffId);
    
    $.ajax({
        url: `${window.APPOINTMENTS_CONFIG.apiUrl}${id}/`,
        type: 'GET',
        success: function(response) {
            console.log('Loaded appointment data:', response);
            populateForm(response, staffId);
            $('#appointmentModal').modal('show');
        },
        error: handleAjaxError
    });
}

// CORRECCIÓN MEJORADA: Función saveAppointment completamente reescrita
function saveAppointment() {
    console.log('Starting saveAppointment...');
    
    const form = $('#appointmentForm');
    if (!form.valid()) {
        console.log('Form validation failed');
        return;
    }

    const formData = {};
    const id = $('#appointment_id').val();
    const staffId = $('#appointment_staff_id').val();
    console.log('Appointment ID:', id, 'Staff ID:', staffId);
     
    const dateValue = $('#date').val();
    const timeValue = $('#time').val();
    if (dateValue && timeValue) {
        formData.date = `${dateValue}T${timeValue}`;
    }
    
    // Campos principales
    ['visitor_name', 'visitor_email', 'visitor_phone', 'stage', 'status', 
     'duration', 'comments'].forEach(field => {
        let value = $(`#${field}`).val();
        
        if (value !== undefined && value !== null && value !== '') {
            if (field === 'duration') {
                formData[field] = parseInt(value);
            } else if (field === 'stage') {
                formData[field] = parseInt(value);
            } else {
                formData[field] = value;
            }
        }
    });

    // Manejar el campo course
    const courseValue = $('#course').val();
    if ($('#course-container').is(':visible') && courseValue) {
        formData.course = parseInt(courseValue);
    }

    // Campos avanzados (solo si están visibles)
    if ($('.advanced-fields').is(':visible')) {
        ['notes', 'follow_up_date'].forEach(field => {
            let value = $(`#${field}`).val();
            if (value !== undefined && value !== null && value !== '') {
                formData[field] = value;
            }
        });
    }

    // Incluir staff_id si lo tenemos
    if (staffId) {
        formData.staff = parseInt(staffId);
    }

    // Validaciones básicas
    if (!formData.date || !formData.visitor_name || !formData.visitor_email || 
        !formData.visitor_phone || !formData.stage || !formData.duration) {
        showToast('Por favor, complete todos los campos requeridos', 'error');
        return;
    }

    // Validar curso si es obligatorio
    const courseSelect = $('#course');
    if ($('#course-container').is(':visible') && courseSelect.attr('required') && !formData.course) {
        showToast('Por favor, seleccione un curso', 'error');
        return;
    }

    const saveBtn = $('#saveAppointment');
    const modal = $('#appointmentModal');
    
    console.log('Sending data:', formData);
    
    // CORRECCIÓN: Construir URLs correctamente
    let apiUrl;
    if (id) {
        // Para editar: /api/appointments/ID/
        apiUrl = `/api/appointments/${id}/`;
    } else {
        // Para crear: /api/appointments/
        apiUrl = '/api/appointments/';
    }
    
    console.log('Using API URL:', apiUrl);
    
    $.ajax({
        url: apiUrl,
        type: id ? 'PUT' : 'POST',
        data: JSON.stringify(formData),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
        },
        beforeSend: function() {
            saveBtn.prop('disabled', true).text('Guardando...');
        },
        success: function(response) {
            console.log('Save successful:', response);
            
            // Recargar tabla si existe
            if (appointmentsTable) {
                appointmentsTable.ajax.reload();
            }
            
            // CORRECCIÓN MEJORADA: Refrescar calendario de forma más robusta
            try {
                // Método 1: Variable global del calendario
                if (typeof window.calendar !== 'undefined' && window.calendar && typeof window.calendar.refetchEvents === 'function') {
                    window.calendar.refetchEvents();
                    console.log('Calendar refreshed via global variable');
                } 
                // Método 2: Buscar en el DOM
                else {
                    const calendarEl = document.getElementById('calendar');
                    if (calendarEl) {
                        // Buscar instancia del calendario
                        const possibleCalendars = [
                            calendarEl.calendar,
                            calendarEl._calendar,
                            window.calendar
                        ];
                        
                        let calendarFound = false;
                        for (let cal of possibleCalendars) {
                            if (cal && typeof cal.refetchEvents === 'function') {
                                cal.refetchEvents();
                                console.log('Calendar refreshed via DOM search');
                                calendarFound = true;
                                break;
                            }
                        }
                        
                        // Método 3: Forzar recarga si es necesario
                        if (!calendarFound && window.location.pathname.includes('/dashboard/')) {
                            console.log('Forcing calendar refresh via page reload');
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                        }
                    }
                }
            } catch (e) {
                console.log('Calendar refresh error:', e.message);
            }
            
            // CORRECCIÓN MEJORADA: Refrescar estadísticas del dashboard
            try {
                if (window.location.pathname.includes('/dashboard/')) {
                    const viewSelector = document.getElementById('viewSelector');
                    const currentView = viewSelector ? viewSelector.value : '';
                    
                    const params = new URLSearchParams();
                    if (currentView) {
                        params.append('staff_id', currentView);
                    }
                    
                    fetch(`/dashboard/stats/?${params.toString()}`)
                        .then(response => response.json())
                        .then(data => {
                            // Actualizar contadores principales
                            const stats = {
                                'todayCount': data.today_count || '-',
                                'confirmedCount': data.confirmed_count || '-',
                                'pendingCount': data.pending_count || '-',
                                'stagesCount': data.stages_count || '-'
                            };
                            
                            Object.entries(stats).forEach(([id, value]) => {
                                const el = document.getElementById(id);
                                if (el) {
                                    el.textContent = value;
                                    console.log(`Updated ${id} to ${value}`);
                                }
                            });
                            
                            // Actualizar próximas citas
                            if (data.upcoming_appointments && typeof window.updateUpcomingAppointments === 'function') {
                                window.updateUpcomingAppointments(data.upcoming_appointments);
                                console.log('Updated upcoming appointments');
                            }
                        })
                        .catch(err => console.log('Dashboard stats refresh failed:', err));
                }
            } catch (e) {
                console.log('Dashboard refresh error:', e.message);
            }
            
            showToast(id ? 'Cita actualizada correctamente' : 'Cita creada correctamente');
            modal.modal('hide');
            cleanupModal();
        },
        error: function(xhr) {
            console.error('Save error:', xhr);
            console.error('Response text:', xhr.responseText);
            console.error('Status:', xhr.status);
            
            let errorMessage = 'Error al guardar la cita';
            
            if (xhr.responseJSON) {
                if (xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                } else if (xhr.responseJSON.visitor_name) {
                    errorMessage = xhr.responseJSON.visitor_name[0];
                } else if (xhr.responseJSON.visitor_email) {
                    errorMessage = xhr.responseJSON.visitor_email[0];
                }
            } else if (xhr.responseText) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    errorMessage = `Error ${xhr.status}: ${xhr.statusText}`;
                }
            }
            
            showToast(errorMessage, 'error');
        },
        complete: function() {
            saveBtn.prop('disabled', false).text('Guardar');
        }
    });
}

function confirmDelete(id) {
    if (confirm('¿Está seguro de que desea eliminar esta cita?')) {
        console.log('Deleting appointment:', id);
        
        $.ajax({
            url: `/api/appointments/${id}/`,
            type: 'DELETE',
            headers: {
                'X-CSRFToken': window.APPOINTMENTS_CONFIG.csrfToken
            },
            success: function() {
                console.log('Appointment deleted successfully');
                
                if (appointmentsTable) {
                    appointmentsTable.ajax.reload();
                }
                
                // Refrescar calendario si existe
                if (typeof window.calendar !== 'undefined' && window.calendar) {
                    window.calendar.refetchEvents();
                }
                
                // Refrescar datos del dashboard si existe
                if (typeof window.updateUpcomingAppointments === 'function') {
                    // Recargar estadísticas del dashboard
                    if (window.location.pathname.includes('/dashboard/')) {
                        fetch('/dashboard/stats/')
                            .then(response => response.json())
                            .then(data => {
                                // Actualizar contadores
                                const stats = {
                                    'todayCount': data.today_count || '-',
                                    'confirmedCount': data.confirmed_count || '-',
                                    'pendingCount': data.pending_count || '-',
                                    'stagesCount': data.stages_count || '-'
                                };
                                
                                Object.entries(stats).forEach(([id, value]) => {
                                    const el = document.getElementById(id);
                                    if (el) el.textContent = value;
                                });
                                
                                // Actualizar próximas citas
                                if (data.upcoming_appointments) {
                                    window.updateUpcomingAppointments(data.upcoming_appointments);
                                }
                            })
                            .catch(err => console.log('Dashboard refresh failed:', err));
                    }
                }
                
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
    let message = 'Ha ocurrido un error';
    
    if (xhr.responseJSON?.error) {
        message = xhr.responseJSON.error;
    } else if (xhr.status === 404) {
        message = 'Recurso no encontrado';
    } else if (xhr.status === 403) {
        message = 'No tienes permisos para realizar esta acción';
    }
    
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
    $('#appointment_staff_id').val('');
    
    // Limpiar validaciones
    $('#appointmentForm').validate().resetForm();
    $('.is-invalid').removeClass('is-invalid');
    
    // Ocultar contenedor de cursos
    $('#course-container').hide();
    $('#course').html('<option value="">Seleccione primero una etapa</option>');
    $('#course').removeAttr('required');
    
    // Limpiar backdrop
    $('body').removeClass('modal-open');
    $('.modal-backdrop').remove();
    $('html').removeClass('modal-open');
    $('body').css('padding-right', '');
}

function populateForm(data, staffId = null) {
    console.log('Populating form with data:', data, 'staffId:', staffId);
    
    $('#appointmentForm')[0].reset();
    $('#appointment_id').val(data.id);
    
    // Establecer staff_id si se proporciona
    if (staffId) {
        $('#appointment_staff_id').val(staffId);
    }
    
    // Manejar fecha y hora
    if (data.date) {
        const datetime = moment(data.date);
        $('#date').val(datetime.format('YYYY-MM-DD'));
        $('#time').val(datetime.format('HH:mm'));
        console.log('Date/Time set to:', datetime.format('YYYY-MM-DD HH:mm'));
    }
    
    // Campos principales
    ['visitor_name', 'visitor_email', 'visitor_phone', 'stage', 
     'status', 'duration', 'comments'].forEach(field => {
        const value = data[field];
        if (value !== undefined && value !== null) {
            console.log(`Setting ${field} to:`, value);
            $(`#${field}`).val(field === 'duration' ? value.toString() : value);
        }
    });
    
    // Campos avanzados
    if ($('.advanced-fields').is(':visible')) {
        ['notes', 'follow_up_date'].forEach(field => {
            const value = data[field];
            if (value !== undefined && value !== null) {
                if (field === 'follow_up_date' && value) {
                    $('#follow_up_date').val(moment(value).format('YYYY-MM-DD'));
                } else {
                    $(`#${field}`).val(value);
                }
            }
        });
    }
    
    // Manejar el curso después de cargar la etapa
    if (data.stage) {
        // Esperar un poco para que se establezca la etapa y luego cargar cursos
        setTimeout(() => {
            loadCoursesForStageWithCallback(data.stage, data.course);
        }, 100);
    }
}

// CORRECCIÓN: Función auxiliar para actualizar próximas citas en el dashboard
function updateUpcomingAppointments(appointments) {
    const container = document.getElementById('upcomingAppointments');
    if (!container) return;

    if (!appointments?.length) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-calendar-times mb-3 h2"></i>
                <p class="mb-0">No hay citas próximas</p>
            </div>
        `;
        return;
    }

    // Función para obtener clase de estado
    function getStatusClass(status) {
        return {
            'pending': 'warning',
            'completed': 'success',
            'cancelled': 'danger'
        }[status] || 'secondary';
    }

    // Función para obtener texto de estado
    function getStatusText(status) {
        return {
            'pending': 'Pendiente',
            'completed': 'Completada',
            'cancelled': 'Cancelada'
        }[status] || status;
    }

    // Función para formatear fecha
    function formatDate(dateStr) {
        return new Intl.DateTimeFormat('es', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        }).format(new Date(dateStr));
    }

    container.innerHTML = appointments.map(apt => {
        const canEdit = true; // Siempre permitir editar desde el dashboard
        return `
            <div class="appointment-card" ${canEdit ? `onclick="loadAppointment(${apt.id}, ${apt.staff_id})"` : ''} 
                 style="cursor: ${canEdit ? 'pointer' : 'default'}">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        <h6 class="mb-1">${apt.visitor_name}</h6>
                        <div class="stage-badge">
                            <i class="fas fa-graduation-cap me-1"></i>${apt.stage}
                        </div>
                    </div>
                    <span class="badge bg-${getStatusClass(apt.status)}">
                        ${getStatusText(apt.status)}
                    </span>
                </div>
                <div class="d-flex align-items-center gap-2 mt-2">
                    <div class="time-badge">
                        <i class="fas fa-clock me-1"></i>${apt.time}
                    </div>
                    <div class="text-muted small">
                        <i class="fas fa-calendar me-1"></i>${formatDate(apt.date)}
                    </div>
                </div>
                <div class="text-muted small mt-2">
                    <i class="fas fa-user me-1"></i>${apt.staff_name}
                </div>
            </div>
        `;
    }).join('');
}

// Hacer funciones disponibles globalmente para el dashboard
window.loadAppointment = loadAppointment;
window.cleanupModal = cleanupModal;
window.updateUpcomingAppointments = updateUpcomingAppointments;