from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import User

class QuestionAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q: {self.question} | A: {self.answer}"
    
from django.db import models

class YourModel(models.Model):
    pdf_file = models.FileField(upload_to='pdfs/')


created_at = models.DateTimeField(auto_now_add=True)