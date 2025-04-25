import google.generativeai as genai
from config import Config
import json

genai.configure(api_key=Config.GEMINI_API_KEY)

def generate_questions(topic, num_questions, difficulty):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Generate {num_questions} quiz questions on the topic '{topic}' with {difficulty} difficulty.
    Include a mix of MCQs, True/False, and Fill-in-the-blanks.
    For each question, provide:
    - Question text (key: text)
    - Type (MCQ, True/False, Fill-in-the-blank) (key: type)
    - Options (for MCQs, list 4 options as a list) (key: options)
    - Correct answer (key: correct_answer)
    - Explanation (key: explanation)
    Return the response as a JSON list.
    """
    response = model.generate_content(prompt)
    return json.loads(response.text.strip('```json\n').strip('```'))