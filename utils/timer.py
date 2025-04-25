def get_timer(difficulty):
    if difficulty == 'easy':
        return 600  # 10 minutes
    elif difficulty == 'medium':
        return 300  # 5 minutes
    elif difficulty == 'hard':
        return 180  # 3 minutes
    else:
        return 300  # Default for custom quizzes