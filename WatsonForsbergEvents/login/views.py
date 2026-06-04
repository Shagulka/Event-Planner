from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "/events/"
    if request.user.is_authenticated:
        return redirect(next_url)

    error = None
    username = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url)
        error = "Invalid username or password."

    return render(request, "login.html", {"error": error, "username": username, "next": next_url})

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect("/login/")
