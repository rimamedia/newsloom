from django.shortcuts import render


def home(request):
    return render(request, "newsloom/home.html")
