from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .meta import Base


class Item(Base):
    """ The SQLAlchemy declarative model class for an Item object. """
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(ForeignKey('scenarios.id'), nullable=False)
    name = Column(Text, nullable=False, unique=False)
    data = Column(Text, nullable=False)

    next = Column(ForeignKey('items.id'), nullable=True)
    previous = Column(ForeignKey('items.id'), nullable=True)

    creator_id = Column(ForeignKey('users.id'), nullable=False)
    creator = relationship('User', backref='created_items')