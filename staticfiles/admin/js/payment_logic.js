(function($) {
    'use strict';
    $(function() {
        const paymentMethodSelect = $('#id_payment_method');
        
        function togglePaymentFields() {
            const method = paymentMethodSelect.val();
            
            // Rows in Django admin are usually div.form-row
            const checkRow = $('.field-check_is_withdrawn');
            const bankRow = $('.field-bank_name');
            const mobileRow = $('.field-mobile_banking_type');

            // Hide all initially
            checkRow.hide();
            bankRow.hide();
            mobileRow.hide();

            if (method === 'bank_check') {
                checkRow.show();
            } else if (method === 'bank_transaction') {
                bankRow.show();
            } else if (method === 'mobile_banking') {
                mobileRow.show();
            }
        }

        if (paymentMethodSelect.length) {
            togglePaymentFields();
            paymentMethodSelect.on('change', togglePaymentFields);
        }

        // Handle Inlines
        $(document).on('formset:added', function(event, $row, formsetName) {
            if (formsetName === 'payments') {
                const inlineMethodSelect = $row.find('select[id$="-payment_method"]');
                function toggleInlineFields() {
                    const method = inlineMethodSelect.val();
                    $row.find('.field-check_is_withdrawn').toggle(method === 'bank_check');
                    $row.find('.field-bank_name').toggle(method === 'bank_transaction');
                    $row.find('.field-mobile_banking_type').toggle(method === 'mobile_banking');
                }
                toggleInlineFields();
                inlineMethodSelect.on('change', toggleInlineFields);
            }
        });

        // Initialize existing inlines
        $('.dynamic-payments').each(function() {
            const $row = $(this);
            const inlineMethodSelect = $row.find('select[id$="-payment_method"]');
            if (inlineMethodSelect.length) {
                function toggleInlineFields() {
                    const method = inlineMethodSelect.val();
                    $row.find('.field-check_is_withdrawn').toggle(method === 'bank_check');
                    $row.find('.field-bank_name').toggle(method === 'bank_transaction');
                    $row.find('.field-mobile_banking_type').toggle(method === 'mobile_banking');
                }
                toggleInlineFields();
                inlineMethodSelect.on('change', toggleInlineFields);
            }
        });
    });
})(django.jQuery);
