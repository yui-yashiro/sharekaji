from django.shortcuts import render
from django.views import View

# Create your views here.
class TopView(View):
    def get(self, request):
        return render(request, "top.html")