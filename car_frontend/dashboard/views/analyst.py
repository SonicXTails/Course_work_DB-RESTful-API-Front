from .decorators import token_required
from django.shortcuts import render

@token_required
def analyst_profile_view(request):
    return render(request, "dashboard/profile_analitic.html")
