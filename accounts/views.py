# Import necessary modules and classes from Django
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.views.generic import FormView
from .forms import UserRegistrationForm, UserUpdateForm
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views import View

# View for user registration, inherits from FormView


class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        # Print cleaned data for debugging purposes
        print(form.cleaned_data)
        # Save the user instance and log in the user
        user = form.save()
        login(self.request, user)
        # Redirect to the success URL (user's profile page)
        return super().form_valid(form)

# View for user login, inherits from LoginView


class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'

    def get_success_url(self):
        # Redirect to the home page on successful login
        return reverse_lazy('home')

# View for user logout, inherits from LogoutView


class UserLogoutView(LogoutView):
    def get_success_url(self):
        # Logout the user and redirect to the home page
        if self.request.user.is_authenticated:
            logout(self.request)
        return reverse_lazy('home')

# View for updating user bank account information, inherits from View


class UserBankAccountUpdateView(View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        # Retrieve the UserUpdateForm instance with the user's data
        form = UserUpdateForm(instance=request.user)
        # Render the form in the template
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        # Process the form submission with user data in POST
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            # Save the updated form and redirect to the user's profile page
            form.save()
            return redirect('profile')
        # If the form is not valid, render the form in the template with errors
        return render(request, self.template_name, {'form': form})
