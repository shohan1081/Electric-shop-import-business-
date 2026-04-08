document.addEventListener('DOMContentLoaded', function() {
    const unitOfMeasureSelect = document.getElementById('id_unit_of_measure');
    const quantityInput = document.getElementById('id_quantity');
    const quantityField = quantityInput ? quantityInput.closest('.form-row') : null;

    function updateQuantityField() {
        if (!unitOfMeasureSelect || !quantityInput || !quantityField) return;

        const selectedUnit = unitOfMeasureSelect.value;
        let helpText = '';

        if (selectedUnit === 'unit') {
            helpText = 'Enter a whole number for the quantity (e.g., 5, 10).';
            // Optionally add a class for styling or further validation
            quantityInput.classList.add('quantity-unit');
            quantityInput.classList.remove('quantity-meter');
        } else if (selectedUnit === 'meter') {
            helpText = 'Enter a decimal number for the quantity (e.g., 5.5, 10.25).';
            // Optionally add a class for styling or further validation
            quantityInput.classList.add('quantity-meter');
            quantityInput.classList.remove('quantity-unit');
        }

        // Find or create the help text element
        let pElement = quantityField.querySelector('.help');
        if (!pElement) {
            pElement = document.createElement('p');
            pElement.classList.add('help');
            quantityField.appendChild(pElement);
        }
        pElement.textContent = helpText;
    }

    // Initial update on page load
    updateQuantityField();

    // Update when unit of measure changes
    if (unitOfMeasureSelect) {
        unitOfMeasureSelect.addEventListener('change', updateQuantityField);
    }
});
