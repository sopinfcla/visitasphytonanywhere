// static/admin/js/staff_filter.js
document.addEventListener('DOMContentLoaded', function() {
    const stageSelect = document.getElementById('id_stage');
    const staffSelect = document.getElementById('id_staff');

    if (stageSelect && staffSelect) {
        stageSelect.addEventListener('change', function() {
            const stageId = this.value;
            staffSelect.innerHTML = '<option value="">---------</option>';
            
            if (stageId) {
                fetch(`/api/staff-by-stage/${stageId}/`)
                    .then(response => response.json())
                    .then(staff => {
                        staff.forEach(item => {
                            staffSelect.add(new Option(item.name, item.id));
                        });
                    });
            }
        });
    }
});
Ahora la vista API: