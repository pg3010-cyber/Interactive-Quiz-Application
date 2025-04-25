from flask import Flask, render_template, request, redirect, url_for, session
from database.models import db, User, Quiz, Question, Leaderboard, CustomQuiz
from ai_models.generator import generate_questions
from ai_models.summarizer import summarize_and_quiz
from ai_models.image_parser import parse_image
from utils.timer import get_timer
from utils.pdf_reader import extract_text_from_pdf
from utils.difficulty_adjuster import adjust_difficulty
from config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email exists")
        user = User(name=name, email=email, password=password, preferences='{"theme": "light"}')
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    quizzes = Quiz.query.filter_by(user_id=user.id).all()
    leaderboard = Leaderboard.query.order_by(Leaderboard.total_score.desc()).limit(10).all()
    return render_template('dashboard.html', user=user, quizzes=quizzes, leaderboard=leaderboard)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        topic = request.form['topic']
        num_questions = int(request.form['num_questions'])
        difficulty = request.form['difficulty']
        user = User.query.get(session['user_id'])
        adjusted_difficulty = adjust_difficulty(user.id, difficulty)
        questions = generate_questions(topic, num_questions, adjusted_difficulty)
        quiz = Quiz(user_id=user.id, topic=topic, difficulty=adjusted_difficulty,
                   total_questions=num_questions)
        db.session.add(quiz)
        db.session.commit()
        for q in questions:
            question = Question(quiz_id=quiz.id, type=q['type'], question=q['text'],
                              options=q.get('options'), correct_answer=q['correct_answer'],
                              explanation=q['explanation'])
            db.session.add(question)
        db.session.commit()
        return render_template('quiz.html', quiz=quiz, questions=questions,
                             timer=get_timer(adjusted_difficulty))
    return render_template('quiz.html')

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    score = 0
    answers = {}
    for q in questions:
        user_answer = request.form.get(f'question_{q.id}')
        answers[q.id] = user_answer
        if user_answer == q.correct_answer:
            score += 1
    quiz.score = score
    db.session.commit()
    user = User.query.get(session['user_id'])
    leaderboard_entry = Leaderboard.query.filter_by(user_id=user.id).first()
    if not leaderboard_entry:
        leaderboard_entry = Leaderboard(user_id=user.id, total_score=0, fastest_time=0, streaks=0)
        db.session.add(leaderboard_entry)
    leaderboard_entry.total_score += score
    leaderboard_entry.streaks = leaderboard_entry.streaks + 1 if score > 0 else 0
    db.session.commit()
    return render_template('result.html', quiz=quiz, questions=questions, score=score, answers=answers)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    quizzes = Quiz.query.filter_by(user_id=session['user_id']).all()
    return render_template('history.html', quizzes=quizzes)

@app.route('/custom_quiz', methods=['GET', 'POST'])
def custom_quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        questions = []
        for i in range(1, int(request.form['num_questions']) + 1):
            q_text = request.form.get(f'q{i}_text')
            q_type = request.form.get(f'q{i}_type')
            options = [request.form.get(f'q{i}_opt{j}') for j in range(1, 5)] if q_type == 'MCQ' else None
            correct = request.form.get(f'q{i}_correct')
            explanation = request.form.get(f'q{i}_explanation')
            questions.append({
                'text': q_text, 'type': q_type, 'options': options,
                'correct_answer': correct, 'explanation': explanation
            })
        custom_quiz = CustomQuiz(user_id=session['user_id'], title=title, question_data=questions)
        db.session.add(custom_quiz)
        db.session.commit()
        quiz = Quiz(user_id=session['user_id'], topic=title, difficulty='custom',
                   total_questions=len(questions))
        db.session.add(quiz)
        db.session.commit()
        for q in questions:
            question = Question(quiz_id=quiz.id, type=q['type'], question=q['text'],
                              options=q.get('options'), correct_answer=q['correct_answer'],
                              explanation=q['explanation'])
            db.session.add(question)
        db.session.commit()
        return render_template('quiz.html', quiz=quiz, questions=questions, timer=300)
    return render_template('custom_quiz.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            text = extract_text_from_pdf(file_path)
            questions = generate_questions(text, 5, 'medium')
            quiz = Quiz(user_id=session['user_id'], topic='Uploaded PDF', difficulty='medium',
                       total_questions=5)
            db.session.add(quiz)
            db.session.commit()
            for q in questions:
                question = Question(quiz_id=quiz.id, type=q['type'], question=q['text'],
                                  options=q.get('options'), correct_answer=q['correct_answer'],
                                  explanation=q['explanation'])
                db.session.add(question)
            db.session.commit()
            return render_template('quiz.html', quiz=quiz, questions=questions, timer=300)
        elif file and file.filename.endswith(('.png', '.jpg', '.jpeg')):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            text = parse_image(file_path)
            questions = generate_questions(text, 5, 'medium')
            quiz = Quiz(user_id=session['user_id'], topic='Uploaded Image', difficulty='medium',
                       total_questions=5)
            db.session.add(quiz)
            db.session.commit()
            for q in questions:
                question = Question(quiz_id=quiz.id, type=q['type'], question=q['text'],
                                  options=q.get('options'), correct_answer=q['correct_answer'],
                                  explanation=q['explanation'])
                db.session.add(question)
            db.session.commit()
            return render_template('quiz.html', quiz=quiz, questions=questions, timer=300)
    return render_template('upload.html')

@app.route('/summary_quiz', methods=['GET', 'POST'])
def summary_quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        text = request.form['text']
        summary, questions = summarize_and_quiz(text)
        quiz = Quiz(user_id=session['user_id'], topic='Summary Quiz', difficulty='medium',
                   total_questions=len(questions))
        db.session.add(quiz)
        db.session.commit()
        for q in questions:
            question = Question(quiz_id=quiz.id, type=q['type'], question=q['text'],
                              options=q.get('options'), correct_answer=q['correct_answer'],
                              explanation=q['explanation'])
            db.session.add(question)
        db.session.commit()
        return render_template('summary_quiz.html', quiz=quiz, questions=questions,
                             summary=summary, timer=300)
    return render_template('summary_quiz.html')

if __name__ == '__main__':
    app.run(debug=True)