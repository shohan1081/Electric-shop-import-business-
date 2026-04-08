document.addEventListener('DOMContentLoaded', function() {
    const filterSidebar = document.getElementById('changelist-filter');
    const changelist = document.getElementById('changelist');
    
    if (filterSidebar && changelist) {

        // 🔥 Remove Django default layout spacing immediately
        changelist.classList.remove('filtered');

        // 1. Create toggle button
        const toggleBtn = document.createElement('a');
        toggleBtn.href = 'javascript:void(0);';
        toggleBtn.id = 'filter-toggle-btn';
        toggleBtn.className = 'button';
        toggleBtn.innerHTML = '<i class="fas fa-filter"></i> Filters';
        
        // Place button in toolbar
        const toolbar = document.getElementById('toolbar');
        if (toolbar) {
            const searchForm = toolbar.querySelector('form');
            if (searchForm) {
                searchForm.style.display = 'flex';
                searchForm.style.alignItems = 'center';
                searchForm.style.gap = '10px';
                searchForm.appendChild(toggleBtn);
            } else {
                toolbar.appendChild(toggleBtn);
            }
        }

        // 2. Add close button to filter header
        const filterHeader = filterSidebar.querySelector('h2');
        if (filterHeader) {
            const closeBtn = document.createElement('span');
            closeBtn.innerHTML = '&times;';
            closeBtn.style.cursor = 'pointer';
            closeBtn.style.fontSize = '24px';
            closeBtn.style.lineHeight = '1';
            closeBtn.style.padding = '0 5px';

            closeBtn.onclick = function() {
                hideFilters();
            };

            filterHeader.appendChild(closeBtn);
        }

        // Toggle button click
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (filterSidebar.classList.contains('filter-visible')) {
                hideFilters();
            } else {
                showFilters();
            }
        });

        // ✅ SHOW FILTER
        function showFilters() {
            filterSidebar.classList.add('filter-visible');
            toggleBtn.classList.add('active');

            // 🔥 Ensure no layout space is reserved
            changelist.classList.remove('filtered');
        }

        // ✅ HIDE FILTER
        function hideFilters() {
            filterSidebar.classList.remove('filter-visible');
            toggleBtn.classList.remove('active');

            // 🔥 Keep layout clean
            changelist.classList.remove('filtered');
        }

        // Close when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInside = filterSidebar.contains(event.target) || toggleBtn.contains(event.target);

            if (!isClickInside && filterSidebar.classList.contains('filter-visible')) {
                hideFilters();
            }
        });

        // Prevent closing when interacting with date filter
        const dateRangeForm = filterSidebar.querySelector('#date-range-form');
        if (dateRangeForm) {
            dateRangeForm.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }

        // Auto open if filters are active in URL
        const urlParams = new URLSearchParams(window.location.search);
        if (
            urlParams.has('sold_date') ||
            urlParams.has('customer__id__exact') ||
            urlParams.has('product__id__exact')
        ) {
            showFilters();
        }

        // 🔥 EXTRA SAFETY (after full page load)
        window.addEventListener('load', function() {
            changelist.classList.remove('filtered');
        });
    }
});