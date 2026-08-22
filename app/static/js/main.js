document.addEventListener('DOMContentLoaded', function() {
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('show');
            if (overlay) overlay.classList.toggle('show', sidebar.classList.contains('show'));
        });
    }
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        });
    }

    // Desktop collapse (persisted)
    const collapseBtn = document.getElementById('sidebarCollapse');
    if (collapseBtn) {
        if (localStorage.getItem('nySidebarCollapsed') === '1') {
            document.body.classList.add('sidebar-collapsed');
        }
        collapseBtn.addEventListener('click', function() {
            const collapsed = document.body.classList.toggle('sidebar-collapsed');
            localStorage.setItem('nySidebarCollapsed', collapsed ? '1' : '0');
        });
    }

    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(function(alert) {
        setTimeout(function() {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 200);
        }, 5000);
    });

    // Delete / action confirmations
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) e.preventDefault();
        });
    });

    // Generic client-side table search
    const searchInput = document.querySelector('[data-search]');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const term = this.value.toLowerCase();
            const rows = document.querySelectorAll('table tbody tr');
            rows.forEach(function(row) {
                row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
            });
        });
    }
});
