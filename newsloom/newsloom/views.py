from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, "newsloom/home.html")


def health_check(request):
    return HttpResponse("OK")
