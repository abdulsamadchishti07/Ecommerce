from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from .models import Profile
from .forms import ProfileUpdateForm

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    context = {
        'profile': profile,
    }
    return render(request, 'account/profile.html', context)

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been successfully deleted.")
        return redirect('/')
    return redirect('profile')

@login_required
def profile_update_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)
    
    return render(request, 'account/profile_form.html', {'form': form})

@login_required
def settings_view(request):
    return render(request, 'account/settings.html')

@login_required
def shop_setup_view(request):
    from .forms import ShopSetupForm
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ShopSetupForm(request.POST, instance=profile)
        if form.is_valid():
            # Update role to Seller
            profile = form.save(commit=False)
            profile.role = 'S'
            profile.save()
            messages.success(request, "Your shop has been set up successfully! You are now a Seller.")
            return redirect('account_settings')
    else:
        form = ShopSetupForm(instance=profile)
        
    return render(request, 'account/shop_setup.html', {'form': form})
