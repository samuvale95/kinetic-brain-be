from sqlalchemy import Column, String, Text, ARRAY, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    aliases = Column(ARRAY(Text), nullable=True)
    primary_muscles = Column(ARRAY(SQLEnum('muscle', name='muscle')), nullable=True)
    secondary_muscles = Column(ARRAY(SQLEnum('muscle', name='muscle')), nullable=True)
    force = Column(SQLEnum('forceType', name='forcetype'), nullable=True)
    level = Column(SQLEnum('levelType', name='leveltype'), nullable=False)
    mechanic = Column(SQLEnum('mechanicType', name='mechanictype'), nullable=True)
    equipment = Column(SQLEnum('equipmentType', name='equipmenttype'), nullable=True)
    category = Column(SQLEnum('categoryType', name='categorytype'), nullable=False)
    instructions = Column(ARRAY(Text), nullable=True)
    description = Column(Text, nullable=True)
    tips = Column(ARRAY(Text), nullable=True)
    date_created = Column(Text, nullable=True)  # Using Text for now, can be converted to timestamptz if needed
    date_updated = Column(Text, nullable=True)


