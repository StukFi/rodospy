from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .meta import Base


class Scenario(Base):
    """ The SQLAlchemy declarative model class for a Page object. """
    __tablename__ = 'scenarios'
    id = Column(Integer, primary_key=True)
    project = Column(Text, nullable=False, unique=False)
    name = Column(Text, nullable=False, unique=False)
    data = Column(Text, nullable=False)

    creator_id = Column(ForeignKey('users.id'), nullable=False)
    creator = relationship('User', backref='created_pages')