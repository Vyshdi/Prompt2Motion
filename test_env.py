from dotenv import load_dotenv
import os

load_dotenv()  # load environment variables from .env

api_key = os.getenv('GROQ_API_KEY')  # get the key

if api_key:
    print("API Key loaded successfully!")
else:
    print("API Key NOT found. Check your .env file.")
