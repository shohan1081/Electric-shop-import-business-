import openpyxl
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
import decimal
from django.contrib import messages

def export_to_excel(modeladmin, request, queryset):
    """
    Final optimized Generic Action to export any queryset to Excel.
    """
    try:
        # 1. Create Workbook
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = 'ExportData'

        # 2. Prepare Headers
        # Get actual field objects to extract verbose names
        fields = modeladmin.model._meta.fields
        headers = [field.verbose_name.upper() for field in fields]
        worksheet.append(headers)

        # 3. Add Data
        for obj in queryset:
            row = []
            for field in fields:
                # Use getattr to get the value dynamically
                value = getattr(obj, field.name)
                
                # Format specific types for Excel
                if isinstance(value, timezone.datetime):
                    if timezone.is_aware(value):
                        value = timezone.make_naive(value)
                    # Convert to string to avoid potential serialization issues
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                
                elif isinstance(value, (decimal.Decimal, float)):
                    value = float(value)
                
                elif value is None:
                    value = ""
                
                # If it's a related object (ForeignKey), get its string representation
                elif hasattr(value, '_meta'):
                    value = str(value)
                
                row.append(value)
            worksheet.append(row)

        # 4. Save to BytesIO stream
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        # 5. Build Response
        filename = f"{modeladmin.model._meta.model_name}_export_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Explicitly set the length to help some browsers
        response['Content-Length'] = len(output.getvalue())
        
        return response

    except Exception as e:
        # Provide feedback in the admin if something fails
        modeladmin.message_user(request, f"Excel Export Failed: {str(e)}", messages.ERROR)
        return None

export_to_excel.short_description = "Export Selected to Excel"
