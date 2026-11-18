
from django.contrib import admin
from .models import Phone


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'brand',
        'price',
        'stock',
        'created_at',
    )

    search_fields = (
        'name',
        'brand',
    )

    list_filter = (
        'brand',
        'created_at',
    )

    ordering = ('name',)
