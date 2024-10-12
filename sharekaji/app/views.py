from django.shortcuts import render, redirect
from django.views import View
from app.forms import SignupForm
from django.contrib.auth import login

# Create your views here.
class TopView(View):
    def get(self, request):
        return render(request, "top.html")

class SignUpView(View):
    def get(self, request):
         form = SignupForm()
         return render(request, "signup.html", context={
             "form":form
         })
    def post(self, request):
        print(request.POST)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("login")
        return render(request, "signup.html", context={
             "form":form
         })


class LoginView(View):
    def get(self, request):
         return render(request, "login.html")

class HomeView(View):
    def get(self, request):
         return render(request, "home.html")

