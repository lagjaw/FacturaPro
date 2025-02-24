from Services.client_service import ClientService  # Ensure correct import
from Services.transaction_service import TransactionService
from Services.invoice_service import InvoiceService
from Services.check_service import CheckService
from Services.checkDivision_service import CheckDivisionService
from Services.alert_service import AlertService
from datetime import datetime  # Ensure datetime is imported


# Define the create_client function
def create_client():
    # Create a new client using the ClientService class
    client_id = ClientService.create_client(
        name="John Doe",
        status="Active",
        revenue=100000.0,
        email="johndoe@example.com",
        address="123 Main Street, Cityville",
        phone="555-1234"
    )
    print(f"Client created with ID: {client_id}")
    return client_id


# Define the create_transaction function
def create_transaction(client_id):
    amount = 5000.0
    payment_method = "Credit Card"
    status = "Pending"
    due_date = "2025-03-01 12:00:00"
    transaction_date = "2025-02-01 12:00:00"
    invoice_id = "some-invoice-id"  # This will be generated later
    remaining_amount = amount  # Remaining amount is assumed to be the same initially
    paid_amount = amount  # Paid amount is equal to the transaction amount

    # Create a new transaction for the client using the TransactionService class
    transaction_id = TransactionService.create_transaction(
        client_id=client_id,
        amount=amount,
        payment_method=payment_method,
        status=status,  # Status passed here
        due_date=due_date,
        invoice_id=invoice_id,
        paid_amount=paid_amount,  # Assuming paid amount is equal to the transaction amount
        remaining_amount=remaining_amount,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        transaction_date=transaction_date  # Transaction date passed here
    )
    print(f"Transaction created with ID: {transaction_id}")
    return transaction_id


# Other functions (create_invoice, create_check, etc.) remain the same

def main():
    # Step-by-step process
    print("Starting end-to-end process...")

    # Create client
    client_id = create_client()

    # Create transaction
    transaction_id = create_transaction(client_id)

    # Continue with the rest of the process...
    # Create invoice, create check, etc.

    print("End-to-end process completed.")


if __name__ == "__main__":
    main()
