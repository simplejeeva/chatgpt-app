import json
import pytest
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from .models import QuestionAnswer

class ChatAppViewsTests(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for the views.
        """
        cls.user_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        cls.user = User.objects.create_user(**cls.user_data)
        
        cls.signup_url = reverse('signup')
        cls.signin_url = reverse('signin')
        cls.index_url = reverse('index')
        cls.upload_pdf_url = reverse('upload_pdf')
        cls.get_value_url = reverse('get_value')
    
    def test_signup_view(self):
        """
        Test the signup functionality.
        """
        response = self.client.post(self.signup_url, data={
            'username': 'newuser',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        })
        self.assertRedirects(response, self.index_url)
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)

    def test_signin_view(self):
        """
        Test the signin functionality with valid credentials.
        """
        response = self.client.post(self.signin_url, data=self.user_data)
        self.assertRedirects(response, self.index_url)
    
    def test_signin_invalid(self):
        """
        Test the signin functionality with invalid credentials.
        """
        response = self.client.post(self.signin_url, data={
            'username': 'wronguser',
            'password': 'wrongpassword'
        })
        self.assertContains(response, "Invalid Credentials")
    
    def test_signout_view(self):
        """
        Test the signout functionality.
        """
        self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        response = self.client.get(reverse('signout'))
        self.assertRedirects(response, self.signin_url)

    @patch('chatapp.views.ask_openai')
    @patch('chatapp.views.ask_llama')
    def test_get_value_view(self, mock_ask_llama, mock_ask_openai):
        """
        Test the get_value view, mocking external API calls.
        """
        mock_ask_openai.return_value = 'OpenAI response'
        mock_ask_llama.return_value = 'LLaMA response'

        # Test OpenAI model
        response = self.client.post(self.get_value_url, data=json.dumps({
            'msg': 'What is Django?',
            'model': 'openai'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('res', response.json())
        self.assertEqual(response.json()['res'], 'OpenAI response')

        # Test LLaMA model
        response = self.client.post(self.get_value_url, data=json.dumps({
            'msg': 'What is Python?',
            'model': 'llama'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('res', response.json())
        self.assertEqual(response.json()['res'], 'LLaMA response')

    @patch('chatapp.views.collection.add')
    @patch('chatapp.views.PdfReader')
    def test_upload_pdf_view(self, mock_PdfReader, mock_add):
        """
        Test the upload_pdf view with a mock PDF file.
        """
        mock_pdf_file = MagicMock()
        mock_PdfReader.return_value.pages = [MagicMock(extract_text=MagicMock(return_value='Sample text'))]
        
        self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        response = self.client.post(self.upload_pdf_url, data={
            'pdf_file': mock_pdf_file
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PDF uploaded and stored in ChromaDB successfully")
        mock_add.assert_called()

    def test_index_view(self):
        """
        Test the index view to ensure the user is redirected if not authenticated.
        """
        response = self.client.get(self.index_url)
        self.assertRedirects(response, self.signin_url)

        # After signing in
        self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)

    def test_question_answer_creation(self):
        """
        Test that the question-answer is created in the database when using the get_value view.
        """
        self.client.login(username=self.user_data['username'], password=self.user_data['password'])
        response = self.client.post(self.get_value_url, data=json.dumps({
            'msg': 'What is Django?',
            'model': 'openai'
        }), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(QuestionAnswer.objects.filter(user=self.user).exists())
        question_answer = QuestionAnswer.objects.first()
        self.assertEqual(question_answer.question, 'What is Django?')
        self.assertEqual(question_answer.answer, 'OpenAI response')


# Run the tests
if __name__ == '__main__':
    pytest.main()
