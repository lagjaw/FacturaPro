from database import engine, Base
from Models import Invoice, PaymentTransaction , Alert, Category ,Check , CheckDivision , Client , InvoiceProduct ,Product , Supplier

# Création des tables après import des modèles
Base.metadata.create_all(engine)

print("Base de données initialisée avec succès !")
