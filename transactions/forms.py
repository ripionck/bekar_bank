# Import necessary modules and classes from Django
from django import forms
from .models import Transaction
from accounts.models import UserBankAccount

# Define a base form for creating transactions


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type']

    def __init__(self, *args, **kwargs):
        # Pop 'account' value from keyword arguments
        self.user_account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        # Disable the 'transaction_type' field
        self.fields['transaction_type'].disabled = True
        # Hide the 'transaction_type' field in the form
        self.fields['transaction_type'].widget = forms.HiddenInput()

    def save(self, commit=True):
        # Set the 'account' and 'balance_after_transaction' fields before saving
        self.instance.account = self.user_account
        self.instance.balance_after_transaction = self.user_account.balance
        return super().save()


# Create a form for deposit transactions, inheriting from the base TransactionForm
class DepositForm(TransactionForm):
    def clean_amount(self):
        min_deposit_amount = 100
        # Retrieve the value of the 'amount' field from the user-filled form
        amount = self.cleaned_data.get('amount')
        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $')
        return amount


# Create a form for withdrawal transactions, inheriting from the base TransactionForm
class WithdrawForm(TransactionForm):
    def clean_amount(self):
        account = self.user_account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance
        amount = self.cleaned_data.get('amount')
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $')
        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $')
        if amount > balance:
            raise forms.ValidationError(
                f'You have {balance} $ in your account. You cannot withdraw more than your account balance.')
        return amount


# Create a form for loan request transactions, inheriting from the base TransactionForm
class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return amount


# Create a form for money transfer transactions, inheriting from the base TransactionForm
class TransferRequestForm(TransactionForm):
    account_no = forms.IntegerField()

    def clean_account_no(self):
        receiver_account = self.cleaned_data.get('account_no')
        data_exist = UserBankAccount.objects.filter(
            account_no=receiver_account).exists()
        if not data_exist:
            raise forms.ValidationError(
                f'Account does not exist'
            )
        return receiver_account

    def clean_amount(self):
        account = self.user_account
        min_transfer_amount = 500
        max_transfer_amount = 20000
        balance = account.balance  # 1000
        amount = self.cleaned_data.get('amount')
        if amount < min_transfer_amount:
            raise forms.ValidationError(
                f'You can transfer at least {min_transfer_amount} $'
            )

        if amount > max_transfer_amount:
            raise forms.ValidationError(
                f'You can transfer at most {max_transfer_amount} $'
            )

        if amount > balance:  # amount = 5000, tar balance ache 200
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not transfer more than your account balance'
            )

        return amount
