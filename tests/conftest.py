import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from Models.Category import Base
  # Assure-toi que c'est la bonne importation

# Configuration de la base de données en mémoire pour les tests
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
Session = scoped_session(sessionmaker(bind=engine))

@pytest.fixture(scope="function")
def db_session():
    """Fixture pour gérer une session de base de données isolée pour chaque test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session()

    Base.metadata.create_all(bind=engine)  # Création des tables

    yield session  # Passe la session au test

    session.close()
    transaction.rollback()  # Annule les modifications après chaque test
    connection.close()
