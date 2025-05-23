# Generated by Django 5.2 on 2025-05-01 20:23

from django.db import migrations

def remove_email_uniqueness(apps, schema_editor):
    # We can't import the User model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    cursor = schema_editor.connection.cursor()
    
    # For SQLite
    try:
        # Get all indexes on auth_user
        cursor.execute("PRAGMA index_list('auth_user')")
        indexes = cursor.fetchall()
        print(f"Indexes on auth_user: {indexes}")
        
        # Find and drop any unique email index
        for idx in indexes:
            idx_name = idx[1]
            if 'email' in idx_name and idx[2] == 1:  # idx[2] == 1 means unique
                print(f"Dropping unique email index: {idx_name}")
                cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
                print("Email uniqueness constraint removed")
    except Exception as e:
        print(f"Error removing email uniqueness: {str(e)}")

class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0003_alter_candidate_linkedin_profile_and_more'),
    ]

    operations = [
        migrations.RunPython(remove_email_uniqueness),
    ]
