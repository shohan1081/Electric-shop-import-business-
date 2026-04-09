(function($) {
    'use strict';

    // Helper to find the container of a field
    function getFieldContainer(fieldName) {
        let $row = $('.form-row.field-' + fieldName).not('.inline-related .form-row');
        if (!$row.length) {
            $row = $('.field-' + fieldName).not('.inline-related .field-' + fieldName);
        }
        return $row;
    }

    function toggleFields() {
        console.log("Payment Logic: Updating for Account System...");
        
        // 1. Main Form Logic (Sale, Payment, Refund)
        const $paymentMethod = $('#id_payment_method, #id_refund_method');
        const $accountField = $('#id_account');
        const $isConditional = $('#id_is_conditional');

        if ($paymentMethod.length) {
            const method = $paymentMethod.val() || 'cash';
            const isConditional = $isConditional.is(':checked');

            // Fields to show only for Bank Checks
            const chequeFields = ['cheque_number', 'cheque_date', 'clearance_date', 'status'];
            
            chequeFields.forEach(fieldName => {
                const $container = getFieldContainer(fieldName);
                if ($container.length) {
                    if (method === 'bank_check' && !isConditional) {
                        $container.show().css('display', 'flex');
                    } else {
                        $container.hide();
                    }
                }
            });

            // Handle Account Field visibility and Smart Selection
            const $accountRow = getFieldContainer('account');
            if ($accountRow.length) {
                if (isConditional) {
                    $accountRow.hide();
                } else {
                    $accountRow.show().css('display', 'flex');
                    
                    // Smart Auto-Selection Logic
                    if ($accountField.val() === "" || $accountField.data('auto-selected') === method) {
                        $accountField.find('option').each(function() {
                            const text = $(this).text().toLowerCase();
                            let shouldSelect = false;

                            if (method === 'cash' && text.includes('cash')) shouldSelect = true;
                            else if ((method === 'bank_transaction' || method === 'bank_check') && (text.includes('bank') || text.includes('pubali') || text.includes('brack'))) shouldSelect = true;
                            else if (method === 'mobile_banking' && (text.includes('bkash') || text.includes('nagad') || text.includes('mobile'))) shouldSelect = true;

                            if (shouldSelect) {
                                $accountField.val($(this).val()).trigger('change');
                                $accountField.data('auto-selected', method); // Mark as auto-selected
                                return false; // Exit loop
                            }
                        });
                    }
                }
            }

            // Hide method and account if Conditional Sale is checked
            const $methodRow = getFieldContainer('payment_method');
            if ($isConditional.length) {
                if (isConditional) {
                    $methodRow.hide();
                    if ($accountRow.length) $accountRow.hide();
                    $('#id_amount_paid').val(0);
                } else {
                    $methodRow.show().css('display', 'flex');
                }
            }
        }

        // 2. Tabular Inlines Logic
        $('.inline-group').each(function() {
            const $rows = $(this).find('tr.form-row, .inline-related');
            
            $rows.each(function() {
                const $row = $(this);
                const $methodSel = $row.find('select[id$="-payment_method"], select[id$="-refund_method"]');
                const $accSel = $row.find('select[id$="-account"]');

                if ($methodSel.length) {
                    const method = $methodSel.val() || 'cash';
                    
                    // Cheque fields visibility in inline
                    ['cheque_number', 'cheque_date', 'clearance_date', 'status'].forEach(field => {
                        const $cell = $row.find('.field-' + field);
                        if ($cell.length) {
                            if (method === 'bank_check') $cell.show();
                            else $cell.hide();
                        }
                    });

                    // Inline Smart Selection
                    if ($accSel.length && ($accSel.val() === "" || $accSel.data('auto-selected') === method)) {
                        $accSel.find('option').each(function() {
                            const text = $(this).text().toLowerCase();
                            let match = false;
                            if (method === 'cash' && text.includes('cash')) match = true;
                            else if ((method === 'bank_transaction' || method === 'bank_check') && (text.includes('bank'))) match = true;
                            else if (method === 'mobile_banking' && (text.includes('mobile') || text.includes('bkash'))) match = true;

                            if (match) {
                                $accSel.val($(this).val()).trigger('change');
                                $accSel.data('auto-selected', method);
                                return false;
                            }
                        });
                    }
                }
            });
        });
    }

    $(document).ready(function() {
        toggleFields();
        $(document).on('change', 'select[id$="payment_method"], #id_payment_method, select[id$="refund_method"], #id_refund_method, #id_is_conditional', toggleFields);
        $(document).on('formset:added', () => setTimeout(toggleFields, 50));
    });

})(django.jQuery);
