from .models import User, QuestionSet, Question, EnumRole, EnumPermission


def can_create_question(user: User):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return True


def can_get_question(user: User, question: Question):
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_get_question_set(user,
                                                               question.belongs.filter(QuestionSet.id != 1).first())


def can_modify_question(user: User, question: Question):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_modify_question_set(user,
                                                                  question.belongs.filter(QuestionSet.id != 1).first())


def can_delete_question(user: User, question: Question):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return question.created_by == user or can_modify_question_set(user,
                                                                  question.belongs.filter(QuestionSet.id != 1).first())


def can_create_question_set(user: User):
    if not user:
        return False
    if user.role == EnumRole.admin:
        return True
    return True


def can_get_question_set(user: User, question_set: QuestionSet):  # 和 can_query 是否要区分开？
    if question_set.permission == EnumPermission.public:
        return True
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
    if question_set.id == 1:
        return False
    if user.role == EnumRole.admin:
        return True
    if user in question_set.maintainer:
        return True
    return False


def can_delete_question_set(user: User, question_set: QuestionSet):
    if not user:
        return False
    if question_set.id == 1:
        return False
    if user.role == EnumRole.admin:
        return True
    if user in question_set.maintainer:
        return True
    return False
