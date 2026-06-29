document.addEventListener('DOMContentLoaded', function() {
    const searchBar = document.getElementById('searchbar');
    if (searchBar) {
        const storageKey = 'admin_search_q_' + window.location.pathname;
        const urlParams = new URLSearchParams(window.location.search);
        const currentQ = urlParams.get('q') || '';
        const savedQ = sessionStorage.getItem(storageKey);
        
        let timeout = null;
        let lastValue = searchBar.value;

        // Function to submit the search form
        function submitSearch() {
            searchBar.closest('form').submit();
        }

        // Restore saved search value if it differs from the loaded query parameter
        // (e.g. if the user typed more characters while the page was reloading)
        if (savedQ !== null && savedQ !== currentQ) {
            searchBar.value = savedQ;
            lastValue = savedQ;
            searchBar.focus();
            searchBar.setSelectionRange(savedQ.length, savedQ.length);
            
            // Trigger automatic submit after restored value
            timeout = setTimeout(submitSearch, 700);
        } else {
            // Keep storage in sync with URL if empty or matching
            if (!urlParams.has('q')) {
                sessionStorage.removeItem(storageKey);
            } else {
                sessionStorage.setItem(storageKey, currentQ);
            }
            
            // Put cursor at the end of text after refresh
            const val = searchBar.value;
            searchBar.value = '';
            searchBar.focus();
            searchBar.value = val;
        }

        searchBar.addEventListener('keyup', function(e) {
            // Ignore helper and navigation keys
            const ignoredKeys = [
                'Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 
                'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 
                'Home', 'End', 'PageUp', 'PageDown', 'Escape'
            ];
            if (ignoredKeys.includes(e.key)) {
                return;
            }

            // Only act if the query actually changed
            if (searchBar.value === lastValue) {
                return;
            }
            lastValue = searchBar.value;
            
            // Save current typed value to handle reload race conditions
            sessionStorage.setItem(storageKey, searchBar.value);

            clearTimeout(timeout);
            timeout = setTimeout(submitSearch, 700); // 700ms debounce
        });
    }
});
