from database.models import Quiz, db

def adjust_difficulty(user_id, base_difficulty):
    quizzes = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.date.desc()).limit(5).all()
    if not quizzes:
        return base_difficulty
    avg_score = sum(q.score for q in quizzes) / len(quizzes)
    if avg_score > 80:
        return 'hard' if base_difficulty != 'hard' else 'hard'
    elif avg_score < 40:
        return 'easy' if base_difficulty != 'easy' else 'easy'
    return base_difficulty