from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_user_and_associate_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    InstagramAccount = apps.get_model('scheduler', 'InstagramAccount')
    YouTubeAccount = apps.get_model('scheduler', 'YouTubeAccount')
    ScheduledPost = apps.get_model('scheduler', 'ScheduledPost')
    
    # Check if the user exists
    admin_user, created = User.objects.get_or_create(
        email='admin@gmail.com',
        defaults={
            'username': 'admin@gmail.com',
            'password': make_password('1234'),
            'is_staff': True,
            'is_superuser': True,
        }
    )
    
    # Associate all existing records without user to the admin user
    InstagramAccount.objects.filter(user__isnull=True).update(user=admin_user)
    YouTubeAccount.objects.filter(user__isnull=True).update(user=admin_user)
    ScheduledPost.objects.filter(user__isnull=True).update(user=admin_user)

def reverse_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0006_instagramaccount_user_scheduledpost_user_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_user_and_associate_data, reverse_func),
    ]
