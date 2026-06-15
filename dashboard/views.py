import io
from django.core.management import call_command
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

@user_passes_test(lambda u: u.is_superuser)
def download_backup(request):
    """
    Exports the entire database to a JSON file and returns it as a download.
    Only accessible by superusers.
    """
    output = io.StringIO()
    # Excluding contenttypes and permissions to avoid issues during potential re-import
    # to a new database where these might already exist with different IDs.
    call_command('dumpdata', indent=2, stdout=output, exclude=['contenttypes', 'auth.permission'])
    
    response = HttpResponse(output.getvalue(), content_type='application/json')
    filename = f"full_backup_{timezone.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
