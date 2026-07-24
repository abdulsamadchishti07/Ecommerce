from django import forms
from .models import Payment


class BankTransferForm(forms.ModelForm):
    bank_reference = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "e.g., TRX-987654321 or Bank Deposit Ref #",
                "required": True,
            }
        ),
        required=True,
    )

    class Meta:
        model = Payment
        fields = ["bank_reference", "bank_receipt", "notes"]
        widgets = {
            "bank_receipt": forms.FileInput(
                attrs={
                    "class": "form-input file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100",
                    "accept": "image/*,.pdf",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Optional notes regarding your payment transfer...",
                }
            ),
        }