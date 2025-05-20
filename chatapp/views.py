import os
import json
import logging
from datetime import date, timedelta, datetime, time

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import make_aware
from django.conf import settings

from PyPDF2 import PdfReader
from dotenv import load_dotenv

from .forms import UserForm
from .models import QuestionAnswer

import openai
from llama_cpp import Llama
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from langchain.text_splitter import CharacterTextSplitter
from chromadb.config import Settings
from django.views.decorators.cache import never_cache

# Load environment variables
load_dotenv()
openai.api_key = settings.API_KEY

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize LLaMA model
model_path = os.path.join(settings.BASE_DIR, "models", "Llama-2-7b-chat-hf-GGUF-Q4_K_M.gguf")
llm = Llama(model_path=model_path, n_ctx=2048)

# Initialize ChromaDB
chroma_client = PersistentClient(settings=Settings(
    persist_directory=os.path.join(settings.BASE_DIR, 'chroma_storage')
))
collection = chroma_client.get_or_create_collection(name="pdf_documents")
embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


# ===================== VIEWS =====================

@login_required(login_url='signin')
def index(request):
    """
    Displays the user's question history for today, yesterday, and the past 7 days.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    seven_days_ago = today - timedelta(days=7)

    start_today = make_aware(datetime.combine(today, time.min))
    end_today = make_aware(datetime.combine(today, time.max))
    start_yesterday = make_aware(datetime.combine(yesterday, time.min))
    end_yesterday = make_aware(datetime.combine(yesterday, time.max))

    questions = QuestionAnswer.objects.filter(user=request.user)
    t_questions = questions.filter(created__range=(start_today, end_today)).order_by('-created')
    y_questions = questions.filter(created__range=(start_yesterday, end_yesterday)).order_by('-created')
    s_questions = questions.filter(created__gte=seven_days_ago, created__lte=today).order_by('-created')

    context = {"t_questions": t_questions, "y_questions": y_questions, "s_questions": s_questions}
    return render(request, "chatapp/index.html", context)

@never_cache
def signup(request):
    """
    Handles user signup by creating a new account and logging the user in.
    """
    if request.user.is_authenticated:
        return redirect("index")

    form = UserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        user = authenticate(request,
                            username=request.POST["username"],
                            password=request.POST["password1"])
        if user:
            login(request, user)
            return redirect("index")

    return render(request, "chatapp/signup.html", {"form": form})

@never_cache
def signin(request):
    """
    Handles user login by authenticating the user credentials.
    """
    if request.user.is_authenticated:
        return redirect("index")

    err = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST["username"],
                            password=request.POST["password"])
        if user:
            login(request, user)
            return redirect("index")
        err = "Invalid Credentials"

    return render(request, "chatapp/signin.html", {"error": err})


def signout(request):
    """
    Logs out the user and redirects to the sign-in page.
    """
    logout(request)
    return redirect("signin")


def ask_openai(message):
    """
    Sends a request to OpenAI's API to get a response for the provided message.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}],
            max_tokens=50
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        return f"OpenAI Error: {e}"


def ask_llama(message):
    """
    Sends a request to the LLaMA model to get a response for the provided message.
    """
    try:
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": message}],
            max_tokens=100
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"LLaMA Error: {e}")
        return f"LLaMA Error: {e}"


@csrf_exempt
@login_required
def get_value(request):
    """
    Handles receiving a prompt from the frontend, querying ChromaDB, and generating a response
    using either OpenAI or LLaMA.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method, only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        prompt = data.get("msg", "")
        model = data.get("model", "openai")
        logger.info("Prompt: %s | Model: %s", prompt, model)

        results = collection.query(query_texts=[prompt], n_results=3)
        if not results.get('documents'):
            logger.warning("No documents found.")
            return JsonResponse({"error": "No relevant documents found in ChromaDB"}, status=404)

        context = "\n".join([str(doc) for doc in results['documents']])
        logger.info("Context (preview): %s", context[:100])

        if model == "llama":
            res_text = ask_llama(f"{prompt}\n{context}")
        elif model == "openai":
            res_text = ask_openai(f"{prompt}\n{context}")
        else:
            res_text = "Unknown model selected."

        QuestionAnswer.objects.create(user=request.user, question=prompt, answer=res_text)
        return JsonResponse({"msg": prompt, "res": res_text, "model": model})

    except json.JSONDecodeError as e:
        logger.error("JSON Error: %s", e)
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error("Error: %s", e)
        return JsonResponse({"error": f"An error occurred: {e}"}, status=500)


@csrf_exempt
@login_required
@csrf_exempt
@login_required

def upload_pdf(request):
    if request.method != "POST":
        return HttpResponse("Invalid request method", status=405)

    uploaded_file = request.FILES.get('pdf_file')
    if not uploaded_file:
        return HttpResponse("No file received", status=400)

    try:
        logger.info("PDF Uploaded: %s", uploaded_file.name)
        reader = PdfReader(uploaded_file)
        full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        logger.info("Extracted text (preview): %s", full_text[:500])

        splitter = CharacterTextSplitter(separator="\n", chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(full_text)

        chunk_ids = [f"{uploaded_file.name}_chunk_{i}" for i in range(len(chunks))]
        metadata = [{"source": uploaded_file.name} for _ in chunks]

        # Check for duplicates
        existing_data = collection.get(ids=chunk_ids)
        existing_ids = existing_data.get('ids', [])  # FIXED LINE

        # Filter new chunks
        new_chunks = [chunk for i, chunk in enumerate(chunks) if chunk_ids[i] not in existing_ids]
        new_chunk_ids = [chunk_ids[i] for i in range(len(chunks)) if chunk_ids[i] not in existing_ids]
        new_metadata = [metadata[i] for i in range(len(chunks)) if chunk_ids[i] not in existing_ids]

        if new_chunks:
            collection.add(documents=new_chunks, ids=new_chunk_ids, metadatas=new_metadata)
            logger.info(f"Stored {len(new_chunks)} new chunks")
        else:
            logger.info("No new chunks to add, all chunks already exist.")

        return HttpResponse(status=204)
    except Exception as e:
        logger.error("PDF Processing Error: %s", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)