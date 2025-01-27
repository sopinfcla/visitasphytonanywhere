document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('booking-app');
    if (!app) return;
 
    const stages = window.SCHOOL_STAGES;
 
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
            <!-- Info Boxes -->
            <div class="row justify-content-center mb-5">
                <div class="col-12 col-xl-10">
                    <!-- Primera Alerta -->
                    <div class="card border-0 shadow-sm mb-4 rounded-3" style="background-color: #e8f3ff;">
                        <div class="card-body p-4">
                            <div class="d-flex align-items-center mb-2">
                                <i class="fas fa-info-circle text-primary fs-4 me-3"></i>
                                <h5 class="card-title mb-0 text-primary">Si te interesa una única etapa educativa:</h5>
                            </div>
                            <p class="card-text mb-0 ms-5">Selecciona la etapa correspondiente abajo y reserva directamente tu cita online eligiendo el día y hora que mejor te convenga.</p>
                        </div>
                    </div>
 
                    <!-- Segunda Alerta -->
                    <div class="card border-0 shadow-sm rounded-3" style="background-color: #e8f3ff;">
                        <div class="card-body p-4">
                            <div class="d-flex align-items-center mb-2">
                                <i class="fas fa-users text-primary fs-4 me-3"></i>
                                <h5 class="card-title mb-0 text-primary">Si tienes hijos en diferentes etapas educativas:</h5>
                            </div>
                            <div class="ms-5">
                                <p class="card-text mb-3">Para organizar una visita que cubra múltiples etapas, por favor contacta directamente con el centro:</p>
                                <div class="d-flex flex-column gap-2">
                                    <a href="tel:+34921420300" class="text-decoration-none">
                                        <i class="fas fa-phone text-primary me-2"></i>
                                        <span class="text-primary fw-semibold">921 42 03 00</span>
                                    </a>
                                    <a href="mailto:colegio@claretsegovia.es" class="text-decoration-none">
                                        <i class="fas fa-envelope text-primary me-2"></i>
                                        <span class="text-primary fw-semibold">colegio@claretsegovia.es</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
 
            <!-- Grid de Etapas -->
            <div class="row g-4">
                ${stages.map(stage => `
                    <div class="col-12 col-md-6 col-lg-4">
                        <div class="card h-100 border-0 shadow-sm hover-shadow rounded-3 overflow-hidden">
                            <!-- Cabecera con color e icono -->
                            <div class="bg-primary text-white text-center p-4">
                                <div class="stage-icon display-4 mb-2">
                                    ${getStageIcon(stage.icon)}
                                </div>
                                <h3 class="h4 mb-1">${stage.name}</h3>
                                <p class="text-white-50 small mb-0">${stage.subtitle}</p>
                            </div>
                            
                            <!-- Cuerpo de la tarjeta -->
                            <div class="card-body p-4 d-flex flex-column">
                                <p class="text-muted mb-4 fs-6">
                                    ${stage.description.charAt(0).toUpperCase() + stage.description.slice(1)}
                                </p>
                                
                                <!-- Lista de características -->
                                <ul class="list-unstyled mb-4 flex-grow-1">
                                    ${stage.features.map(feature => `
                                        <li class="d-flex align-items-center mb-2">
                                            <i class="fas fa-check-circle text-primary me-2"></i>
                                            ${feature}
                                        </li>
                                    `).join('')}
                                </ul>
 
                                <!-- Botón de reserva -->
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