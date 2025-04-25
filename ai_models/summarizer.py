import google.generativeai as genai
from config import Config
import json

genai.configure(api_key=Config.GEMINI_API_KEY)

def summarize_and_quiz(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    summary_prompt = f"Summarize the following text in 100 words or less:\n\n{text}"
    summary_response = model.generate_content(summary_prompt)
    summary = summary_response.text

    quiz_prompt = f"""
    Generate 5 quiz questions based on the following summary:\n\n{summary}
    Include a mix of MCQs, True/False, and Fill-in-the-blanks.
    For each question, provide:
    - Question text (key: text)
    - Type (MCQ, True/False, Fill-in-the-blank) (key: type)
    - Options (for MCQs, list 4 options as a list) (key: options)
    - Correct answer (key: correct_answer)
    - Explanation (key: explanation)
    Return the response as a JSON list.
    """
    quiz_response = model.generate_content(quiz_prompt)
    questions = json.loads(quiz_response.text.strip('```json\n').strip('```'))
    return summary, questions