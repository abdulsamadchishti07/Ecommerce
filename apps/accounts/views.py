from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Profile

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    addresses = request.user.addresses.all()
    context = {
        'profile': profile,
        'addresses': addresses,
    }
    return render(request, 'account/profile.html', context)

