# Generated by Django 5.1.3 on 2024-12-02 22:17

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0003_watchlistalert"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="newuserprofile",
            managers=[],
        ),
        migrations.AddIndex(
            model_name="apartmentwatchlist",
            index=models.Index(
                fields=["created_at"], name="buildings_a_created_88f306_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="apartmentwatchlist",
            index=models.Index(
                fields=["last_notified"], name="buildings_a_last_no_8b6881_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="buildingwatchlist",
            index=models.Index(
                fields=["created_at"], name="buildings_b_created_aaafe0_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="buildingwatchlist",
            index=models.Index(
                fields=["last_notified"], name="buildings_b_last_no_2b4675_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="buildingwatchlist",
            index=models.Index(
                fields=["unit_type_preference"], name="buildings_b_unit_ty_10c5b1_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="newuserprofile",
            index=models.Index(
                fields=["created_at"], name="buildings_n_created_e02036_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="newuserprofile",
            index=models.Index(
                fields=["phone_number"], name="buildings_n_phone_n_227888_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="watchlistalert",
            index=models.Index(
                fields=["created_at"], name="buildings_w_created_a0485e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="watchlistalert",
            index=models.Index(fields=["read"], name="buildings_w_read_6d1a8b_idx"),
        ),
        migrations.AddIndex(
            model_name="watchlistalert",
            index=models.Index(
                fields=["alert_type"], name="buildings_w_alert_t_3c870e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="watchlistalert",
            index=models.Index(
                fields=["user", "read"], name="buildings_w_user_id_bae76b_idx"
            ),
        ),
    ]