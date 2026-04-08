(function($) {
    'use strict';

    // Helper to find the container of a field (handles different Django versions)
    function getFieldContainer(fieldName, isInline) {
        if (isInline) {
            return $('.field-' + fieldName);
        }
        // Try standard form-row first, then generic field class
        let $row = $('.form-row.field-' + fieldName).not('.inline-related .form-row');
        if (!$row.length) {
            $row = $('.field-' + fieldName).not('.inline-related .field-' + fieldName);
        }
        return $row;
    }

    function toggleFields() {
        console.log("Payment Logic: Toggling fields...");
        
        // 1. Main Form Logic
        const $mainMethod = $('#id_payment_method, #id_refund_method');
        const $isConditional = $('#id_is_conditional');

        if ($mainMethod.length || $isConditional.length) {
            const method = $mainMethod.val() || 'cash';
            const isConditional = $isConditional.is(':checked');

            const fieldVisibility = {
                'bank_name': ['bank_check', 'bank_transaction'],
                'mobile_banking_type': ['mobile_banking'],
                'cheque_number': ['bank_check'],
                'cheque_date': ['bank_check'],
                'clearance_date': ['bank_check'],
                'status': ['bank_check'],
            };

            for (const [fieldName, allowedMethods] of Object.entries(fieldVisibility)) {
                const $container = getFieldContainer(fieldName, false);
                if ($container.length) {
                    const shouldShow = !isConditional && allowedMethods.includes(method);
                    if (shouldShow) {
                        $container.show().css('display', 'flex');
                    } else {
                        $container.hide();
                    }
                }
            }

            // Special handling for Conditional Sale
            const $methodRow = getFieldContainer('payment_method', false);
            if ($isConditional.length) {
                if (isConditional) {
                    $methodRow.hide();
                    $('#id_amount_paid').val(0);
                } else {
                    $methodRow.show().css('display', 'flex');
                }
            }

            // Auto-set status for non-cheques
            if (method !== 'bank_check') {
                const $status = $('#id_status');
                if ($status.length) $status.val('CLEARED');
            }
        }

        // 2. Tabular Inlines Logic
        $('.inline-group').each(function() {
            const $rows = $(this).find('tr.form-row, .inline-related');
            
            $rows.each(function() {
                const $row = $(this);
                const $methodSel = $row.find('select[id$="-payment_method"], select[id$="-refund_method"]');
                if ($methodSel.length) {
                    const method = $methodSel.val() || 'cash';
                    const fieldVisibility = {
                        'bank_name': ['bank_check', 'bank_transaction'],
                        'mobile_banking_type': ['mobile_banking'],
                        'cheque_number': ['bank_check'],
                        'cheque_date': ['bank_check'],
                        'clearance_date': ['bank_check'],
                        'status': ['bank_check'],
                    };

                    for (const [fieldName, allowedMethods] of Object.entries(fieldVisibility)) {
                        const $cell = $row.find('.field-' + fieldName);
                        if ($cell.length) {
                            if (allowedMethods.includes(method)) {
                                $cell.show();
                            } else {
                                $cell.hide();
                            }
                        }
                    }
                    
                    if (method !== 'bank_check') {
                        const $status = $row.find('select[id$="-status"]');
                        if ($status.length) $status.val('CLEARED');
                    }
                }
            });
        });
    }

    $(document).ready(function() {
        // Initial run
        toggleFields();

        // Listen for changes
        $(document).on('change', 'select[id$="payment_method"], #id_payment_method, select[id$="refund_method"], #id_refund_method, #id_is_conditional', function() {
            toggleFields();
        });

        // Listen for newly added inline rows
        $(document).on('formset:added', function() {
            setTimeout(toggleFields, 50);
        });
    });

})(django.jQuery);
