from sqlalchemy import Table, TEXT, Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

def prepare_db(engine, checkfirst=True):
    Base.metadata.create_all(engine, checkfirst=checkfirst)

class DBVersion(Base):
    __tablename__ = "db_version"

    version = Column(Integer, primary_key=True)

class Experiment(Base):
    __tablename__ = "experiment"

    id = Column(Integer, primary_key=True, autoincrement="auto", nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    autosubmit_version = Column(String)

class Details(Base):
    __tablename__ = "details"

    exp_id = Column(Integer, ForeignKey('experiment.id'), primary_key=True)
    user = Column(TEXT, nullable=False)
    created = Column(TEXT, nullable=False)
    model = Column(TEXT, nullable=False)
    branch = Column(TEXT, nullable=False)
    hpc = Column(TEXT, nullable=False)


if __name__ == "__main__":
    SQLALCHEMY_DATABASE_URL = "sqlite:///./autosubmit_api/test_cases/ecearth.db"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()

    raw_query = db.query(Details, Experiment).join(Experiment)
    print(raw_query.statement)
    result = raw_query.all()
    
    print([x for x in result])
    # prepare_db(engine)