import enum
from datetime import datetime

from sqlalchemy import Column, Enum, ForeignKey, Integer, Table, String, PrimaryKeyConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship, backref

from ..database import Base


class EnumRole(enum.Enum):
    user = 'user'
    admin = 'admin'


class EnumPermission(enum.Enum):
    public = 'public'
    protected = 'protected'
    private = 'private'


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    institution = Column(String(255))
    role = Column(Enum(EnumRole), server_default='user')


set2user = Table('set2user',
                 Base.metadata,
                 Column('set_id', Integer, ForeignKey('question_set.id')),
                 Column('user_id', Integer, ForeignKey('user.id')),
                 PrimaryKeyConstraint('set_id', 'user_id'))

set2question = Table('set2question',
                     Base.metadata,
                     Column('set_id', Integer, ForeignKey('question_set.id')),
                     Column('question_id', Integer, ForeignKey('question.id')),
                     PrimaryKeyConstraint('set_id', 'question_id'))


class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(String(3000), nullable=False)
    embedding = Column(JSON, nullable=False)  # 好像实际上存的是 String?
    modified_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    modified_by_id = Column(Integer, ForeignKey('user.id'))
    modified_by = relationship('User', backref=backref('modified_question', lazy='dynamic'),
                               uselist=False, foreign_keys=[modified_by_id])
    belongs = relationship('QuestionSet', secondary=set2question, back_populates='questions', lazy='dynamic')
    created_at = Column(DateTime, default=datetime.now)
    created_by_id = Column(Integer, ForeignKey('user.id'))
    created_by = relationship('User', backref=backref('created_question', lazy='dynamic'),
                              uselist=False, foreign_keys=[created_by_id])


class QuestionSet(Base):
    __tablename__ = 'question_set'
    # 预计大公共库占用 id=1
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    questions = relationship('Question', secondary=set2question, back_populates='belongs', lazy='dynamic')
    owner_id = Column(Integer, ForeignKey('user.id'))
    owner = relationship('User', backref=backref('own', lazy='dynamic'),
                         uselist=False, foreign_keys=[owner_id])
    maintainer = relationship('User', secondary=set2user, backref=backref('maintain', lazy='dynamic'), lazy='dynamic')
    modified_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    modified_by_id = Column(Integer, ForeignKey('user.id'))
    modified_by = relationship('User', backref=backref('modified_set', lazy='dynamic'),
                               uselist=False, foreign_keys=[modified_by_id])
    created_at = Column(DateTime, default=datetime.now)
    created_by_id = Column(Integer, ForeignKey('user.id'))
    created_by = relationship('User', backref=backref('created_set', lazy='dynamic'),
                              uselist=False, foreign_keys=[created_by_id])
    permission = Column(Enum(EnumPermission), server_default='private')
    # passwd
