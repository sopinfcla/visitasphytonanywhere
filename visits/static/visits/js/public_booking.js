document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('booking-app');
    if (!app) return;

    const stages = window.SCHOOL_STAGES;

    if (!Array.isArray(stages)) {
        console.error("SCHOOL_STAGES no es un array válido:", stages);
        app.innerHTML = '<p class="text-danger">No se encontraron etapas educativas disponibles.</p>';
        return;
    }

    const getStageIcon = (icon) => {
        const icons = {
            '👶': '<i class="fas fa-baby fa-lg"></i>',
            '🎨': '<i class="fas fa-paint-brush fa-lg"></i>', 
            '📚': '<i class="fas fa-book-open fa-lg"></i>',
            '🔬': '<i class="fas fa-microscope fa-lg"></i>',
            '🎓': '<i class="fas fa-graduation-cap fa-lg"></i>'
        };
        return icons[icon] || icons['📚'];
    };

    const content = `
        <div class="container py-5">
            <!-- Grid de Etapas -->
            <div class="row g-4">
                ${stages.map(stage => `
                    <div class="col-12 col-md-6 col-lg-4">
                        <div class="card h-100 border-0 shadow-sm hover-shadow rounded-3 overflow-hidden">
                            <div class="bg-primary text-white text-center p-4">
                                <div class="stage-icon display-4 mb-2">
                                    ${getStageIcon(stage.icon || '📚')}
                                </div>
                                <h3 class="h4 mb-1">${stage.name || 'Etapa Desconocida'}</h3>
                                <p class="text-white-50 small mb-0">${stage.subtitle || ''}</p>
                            </div>
                            <div class="card-body p-4 d-flex flex-column">
                                <p class="text-muted mb-4 fs-6">
                                    ${(stage.description || 'Descripción no disponible.').charAt(0).toUpperCase() + (stage.description || 'Descripción no disponible.').slice(1)}
                                </p>
                                <ul class="list-unstyled mb-4 flex-grow-1">
                                    ${(stage.features || []).map(feature => `
                                        <li class="d-flex align-items-center mb-2">
                                            <i class="fas fa-check-circle text-primary me-2"></i>
                                            ${feature}
                                        </li>
                                    `).join('')}
                                </ul>
                                <a href="/reservar/${stage.id}/" 
                                   class="btn btn-primary py-2 fw-semibold d-flex align-items-center justify-content-center gap-2 mt-auto">
                                    <i class="fas fa-calendar-alt me-1"></i>
                                    Reservar Visita
                                </a>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    app.innerHTML = content;
});
