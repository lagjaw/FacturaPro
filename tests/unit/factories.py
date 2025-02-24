import uuid
from datetime import datetime
import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

# Import correct des modèles
from Models.Client import Client
from Models.Product import Product
from Models.Category import Category
from Models.Supplier import Supplier

fake = Faker()
fake.seed_instance(42)  # Garde une cohérence entre les tests


class BaseFactory(SQLAlchemyModelFactory):
    """ Factory de base avec gestion de la session SQLAlchemy """
    class Meta:
        abstract = True

    id = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(datetime.now)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the _create method to accept session explicitly."""
        session = kwargs.get('session')
        if session:
            cls._meta.sqlalchemy_session = session  # Set session from test
        return super()._create(model_class, *args, **kwargs)


class ClientFactory(BaseFactory):
    """ Factory pour Client """
    class Meta:
        model = Client

    name = factory.Faker('company')
    email = factory.Faker('email')
    address = factory.Faker('address')


class CategoryFactory(BaseFactory):
    """ Factory pour Category """
    class Meta:
        model = Category

    name = factory.Faker('word')


class SupplierFactory(BaseFactory):
    """ Factory pour Supplier """
    class Meta:
        model = Supplier

    name = factory.Faker('company')
    address = factory.Faker('address')


class ProductFactory(BaseFactory):
    """ Factory pour Product """
    class Meta:
        model = Product

    name = factory.LazyFunction(lambda: fake.word().capitalize())
    stock_quantity = factory.Faker('random_int', min=0, max=1000)
    unit_price = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    expiration_date = factory.LazyFunction(lambda: fake.future_date(end_date="+30d"))
    stock_alert_threshold = factory.LazyFunction(lambda: fake.random_int(min=1, max=20))
    expiration_alert_threshold = 30
    description = factory.Faker('sentence', nb_words=6)

    # Associations avec SubFactory
    category = factory.SubFactory(CategoryFactory)
    supplier = factory.SubFactory(SupplierFactory)

    updated_at = factory.LazyFunction(datetime.now)
