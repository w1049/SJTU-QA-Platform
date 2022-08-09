from .models import User, QuestionSet, Question, EnumRole


def can_create_question(user: User):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return True


def can_get_question(user: User, question: Question):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_get_question_set(user, question.belongs.first())


def can_modify_question(user: User, question: Question):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_modify_question_set(user, question.belongs.first())


def can_delete_question(user: User, question: Question):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_modify_question_set(user, question.belongs.first())


def can_create_question_set(user: User):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return True


def can_get_question_set(user: User, question_set: QuestionSet):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    if user in question_set.maintainer:
        return True
    return False


def can_modify_question_set(user: User, question_set: QuestionSet):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    if user in question_set.maintainer:
        return True
    return False


def can_delete_question_set(user: User, question_set: QuestionSet):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    if user in question_set.maintainer:
        return True
    return False
