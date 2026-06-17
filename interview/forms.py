from django import forms


class ResumeUploadForm(forms.Form):

    resume = forms.FileField()

    question_count = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        label="Number of Questions"
    )

