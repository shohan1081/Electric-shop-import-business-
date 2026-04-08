document.addEventListener('DOMContentLoaded', function() {
    const searchBar = document.getElementById('searchbar');
    if (searchBar) {
        let timeout = null;
        searchBar.addEventListener('keyup', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                searchBar.closest('form').submit();
            }, 500); // Wait 500ms after typing stops before searching
        });

        // Put cursor at the end of text after refresh
        const val = searchBar.value;
        searchBar.value = '';
        searchBar.focus();
        searchBar.value = val;
    }
});
