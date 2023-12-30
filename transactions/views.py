# Import necessary modules and classes from Django
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView
from django.views import View
from transactions.models import Transaction
from transactions.forms import DepositForm, LoanRequestForm, WithdrawForm, TransferRequestForm
from .constants import DEPOSIT, LOAN, LOAN_PAID, WITHDRAWAL, TRANSFER
from accounts.models import UserBankAccount
from django.http import HttpResponse
from datetime import datetime
from django.db.models import Sum
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# Create your views here.
def send_transaction_email(user, amount, subject, template):
    message = render_to_string(template, {
        'user': user,
        'amount': amount,
    })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()

# Define a mixin class for creating transactions with common functionality


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    # Override get_form_kwargs to pass additional keyword arguments to the form
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    # Override get_context_data to add 'title' to the context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'title': self.title})
        return context


# Create a view for depositing money
class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit Form'

    # Override get_initial to set initial values for the form
    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    # Override form_valid to handle form submission for deposit
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(update_fields=['balance'])

        messages.success(
            self.request, f'{"{:,.2f}".format(float(amount))} $ was deposited to your account successfully.'
        )
        send_transaction_email(self.request.user, amount,
                               "Deposite Message", "transactions/deposite_email.html")

        return super().form_valid(form)


# Create a view for withdrawing money
class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    # Override get_initial to set initial values for the form
    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    # Override form_valid to handle form submission for withdrawal
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= amount
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        send_transaction_email(self.request.user, amount,
                               "Withdrawl Message", "transactions/withdrawal_email.html")
        return super().form_valid(form)


# Create a view for requesting a loan
class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    # Override get_initial to set initial values for the form
    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    # Override form_valid to handle form submission for loan request
    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account, transaction_type=3, loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have crossed the loan limit")
        messages.success(
            self.request, f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully')
        send_transaction_email(self.request.user, amount,
                               "Loan Request Message", "transactions/loan_request.html")
        return super().form_valid(form)


# Create a view for displaying transaction reports
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0  # to store the balance to be displayed in the template

    # Override get_queryset to filter and customize the queryset
    def get_queryset(self):
        queryset = super().get_queryset().filter(account=self.request.user.account)
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Filter transactions based on start and end date
            queryset = queryset.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date)

            # Calculate the total balance for the specified date range
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date).aggregate(Sum('amount'))['amount__sum']
        else:
            # Use the account balance if no date range is specified
            self.balance = self.request.user.account.balance

        return queryset.distinct()

    # Override get_context_data to add additional context variables
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'account': self.request.user.account, 'balance': self.balance})

        return context


# Create a view for paying off a loan
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        if loan.loan_approve:
            user_account = loan.account

            # Check if the user has sufficient balance to pay off the loan
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transactions = user_account.balance
                user_account.save()
                loan.loan_approve = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
                    self.request, f'Loan amount is greater than available balance')
        return redirect('loan_list')


# Create a view for displaying a list of loans
class LoanListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    # loan list will be available as 'loans' in the template
    context_object_name = 'loans'

    # Override get_queryset to filter loans for the current user
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(
            account=user_account, transaction_type=3)
        return queryset


# Create a view for transferring money between accounts
class TransferMoneyView(TransactionCreateMixin):
    form_class = TransferRequestForm
    title = 'Transfer Money'

    def get_initial(self):
        # Set the initial value for the 'transaction_type' field in the form to TRANSFER.
        initial = {'transaction_type': TRANSFER}
        return initial

    def form_valid(self, form):
        # Retrieve the amount and receiver's account number from the form.
        amount = form.cleaned_data.get('amount')
        receiver_account = UserBankAccount.objects.get(
            account_no=form.cleaned_data.get('account_no'))
        # Update the balances of the sender and receiver accounts.
        self.request.user.account.balance -= amount
        receiver_account.balance += amount
        print(receiver_account.account_no)
        # Save the updated balances to the database.
        receiver_account.save(update_fields=['balance'])
        self.request.user.account.save(update_fields=['balance'])

        # Send email to sender
        send_transaction_email(
            self.request.user, amount, "Transaction Confirmation", "transactions/sender_email.html")

        # Send email to receiver
        send_transaction_email(receiver_account.user, amount,
                               "Transaction Received", "transactions/receiver_email.html")

        messages.success(
            self.request,
            f'Successfully Transfered {"{:,.2f}".format(float(amount))}$ from your account'
        )

        return super().form_valid(form)
