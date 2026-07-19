from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_update_view, name='profile_edit'),
    path('settings/', views.settings_view, name='account_settings'),
    path('shop-setup/', views.shop_setup_view, name='shop_setup'),
    path('delete/', views.delete_account_view, name='account_delete'),
]
