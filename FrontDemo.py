import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
import time

from pygments.lexers import go
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import json
from datetime import datetime, timedelta

API_URL = "http://127.0.0.1:8000/api"

# Route prefixes based on backend structure
INVOICE_PROCESSING_PREFIX = "/invoice-processing"
PAYMENTS_PREFIX = "/payments/advanced"  # Updated to match FastAPI route
CLIENTS_PREFIX = "/clients"
STOCK_PREFIX = "/stock"
COMMUNICATIONS_PREFIX = "/communications"

ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
MAX_RETRIES = 3

# Initialize session state
if 'upload_history' not in st.session_state:
    st.session_state.upload_history = []
if 'last_search' not in st.session_state:
    st.session_state.last_search = None

# Configure requests session with retry mechanism
session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


def validate_file_extension(filename: str) -> bool:
    """Validate if the file has an allowed extension."""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    if amount is None:
        return "N/A"
    return f"{amount:,.2f} €"


def format_api_response(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format API response into a pandas DataFrame."""
    if not data:
        return pd.DataFrame()

    # Create DataFrame from the data
    df = pd.DataFrame(data)

    # Format currency columns if they exist
    currency_columns = ['total', 'subtotal', 'tax', 'discount']
    for col in currency_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: format_currency(float(x)) if x not in [None, 'Not found'] else 'N/A')

    # Format items column if it exists
    if 'items' in df.columns:
        df['items'] = df['items'].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if x not in [None, 'Not found'] else '[]')

    return df


def upload_invoices(files: List[Any]) -> Dict:
    """Upload and process invoice files."""
    if not files:
        st.error("Aucun fichier sélectionné.")
        return {}

    invalid_files = [f.name for f in files if not validate_file_extension(f.name)]
    if invalid_files:
        st.error(f"Types de fichiers non supportés: {', '.join(invalid_files)}")
        return {}

        # Updated URL with correct prefix
    url = f"{API_URL}{INVOICE_PROCESSING_PREFIX}/process-invoice/"
    files_data = [("files", (file.name, file)) for file in files]

    try:
        with st.spinner(f"Traitement de {len(files)} fichier(s)..."):
            response = session.post(url, files=files_data, timeout=30)
            response.raise_for_status()
            result = response.json()

            st.session_state.upload_history.extend([f.name for f in files])
            return result
    except requests.exceptions.HTTPError as e:
        st.error(f"🚫 Erreur HTTP ({e.response.status_code}): {e.response.text}")
    except requests.exceptions.ConnectionError:
        st.error("🔌 Impossible de se connecter au serveur. Vérifiez que l'API est en cours d'exécution.")
    except requests.exceptions.Timeout:
        st.error("⏰ Le serveur met trop de temps à répondre. Réessayez plus tard.")
    except Exception as e:
        st.error(f"❌ Une erreur inattendue s'est produite: {str(e)}")
    return {}


def search_invoices(
        invoice_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        status: Optional[str] = None
) -> Dict:
    """Search for invoices with various criteria."""
    url = f"{API_URL}{INVOICE_PROCESSING_PREFIX}/search-invoices/"

    # Clean and prepare parameters
    params = {}

    if invoice_number:
        # Remove any leading/trailing whitespace and convert to string
        params["invoice_number"] = str(invoice_number).strip()

    if date_from:
        params["date_from"] = date_from

    if date_to:
        params["date_to"] = date_to

    if min_amount is not None and min_amount > 0:
        params["min_amount"] = min_amount

    if max_amount is not None and max_amount > 0:
        params["max_amount"] = max_amount

    if status:
        params["status"] = status

    try:
        with st.spinner("Recherche en cours..."):
            # Debug information
            st.write("Paramètres de recherche:", params)

            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            # Debug information
            st.write("Réponse de l'API:", result)

            st.session_state.last_search = result
            return result
    except requests.exceptions.HTTPError as e:
        st.error(f"🚫 Erreur HTTP ({e.response.status_code}): {e.response.text}")
        # Debug information
        st.write("Réponse d'erreur:", e.response.text)
    except Exception as e:
        st.error(f"❌ Erreur lors de la recherche: {str(e)}")
    return {}

def format_currency(amount: float) -> str:
    """Format amount as currency."""
    if amount is None:
        return "N/A"
    return f"{amount:,.2f} €"

def generate_bilan(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict:
    """Generate a summary report of invoices."""
    url = f"{API_URL}{INVOICE_PROCESSING_PREFIX}/generate_bilan/"

    params = {
        "date_from": date_from,
        "date_to": date_to
    }
    params = {k: v for k, v in params.items() if v is not None}

    try:
        with st.spinner("Génération du rapport en cours..."):
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"🚫 Erreur HTTP ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération du bilan: {str(e)}")
    return {}


# UI Layout
st.set_page_config(
    page_title="Système de Traitement des Factures",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Système de Traitement des Factures")

# Sidebar with statistics
with st.sidebar:
    st.header("📈 Statistiques")
    st.write(f"Fichiers traités: {len(st.session_state.upload_history)}")
    if st.session_state.upload_history:
        st.write("Derniers fichiers traités:")
        for file in st.session_state.upload_history[-5:]:
            st.write(f"- {file}")

# Main content in tabs
tab1, tab2, tab3, tab4 , tab5 , tab6= st.tabs(["📤 Upload", "🔍 Recherche", "📊 Bilan", "💰 Paiements Avancés", "👥 Clients", "📦 Stocks"])

with tab1:
    st.header("Télécharger des Factures")
    st.write("Types de fichiers acceptés: " + ", ".join(ALLOWED_EXTENSIONS))

    uploaded_files = st.file_uploader(
        "Glissez-déposez vos factures ici",
        accept_multiple_files=True,
        type=[ext[1:] for ext in ALLOWED_EXTENSIONS]
    )

    if uploaded_files:
        st.write("📁 Fichiers sélectionnés:")
        for file in uploaded_files:
            st.write(f"- {file.name}")

        if st.button("🚀 Traiter les Factures", key="process_button"):
            result = upload_invoices(uploaded_files)
            if result:
                st.success(f"✅ {len(result)} facture(s) traitée(s)!")

                # Process results into two arrays
                valid_results = []
                invalid_results = []

                try:
                    # Handle both single result and list of results
                    results_list = result.get('results', []) if isinstance(result, dict) else result
                    if isinstance(results_list, dict):
                        results_list = [results_list]

                    for r in results_list:
                        if isinstance(r, dict):
                            if r.get('status') == 'success':
                                data = r.get('data', {})
                                valid_results.append({
                                    'Fichier': r.get('filename', 'N/A'),
                                    'N° Facture': data.get('invoice_number', 'N/A'),
                                    'Date': data.get('date', 'N/A'),
                                    'Date Échéance': data.get('due_date', 'N/A'),
                                    'Client': data.get('bill_to', 'N/A'),
                                    'Montant Total': format_currency(data.get('total', 0)),
                                    'Montant HT': format_currency(data.get('subtotal', 0)),
                                    'TVA': format_currency(data.get('tax', 0)),
                                    'Remise': format_currency(data.get('discount', 0)),
                                    'GSTIN': data.get('gstin', 'N/A'),
                                    'Statut': data.get('status', 'pending')
                                })
                            elif r.get('status') == 'error':
                                invalid_results.append({
                                    'Fichier': r.get('filename', 'N/A'),
                                    'N° Facture': r.get('data', {}).get('invoice_number', 'N/A'),
                                    'Date': r.get('data', {}).get('date', 'N/A'),
                                    'Montant': format_currency(r.get('data', {}).get('total', 0)),
                                    'TVA': format_currency(r.get('data', {}).get('tax', 0)),
                                    'Erreur': r.get('error', 'Erreur inconnue')
                                })

                    # Display valid invoices table
                    st.subheader("✅ Factures Valides")
                    if valid_results:
                        df_valid = pd.DataFrame(valid_results)
                        st.dataframe(
                            df_valid,
                            use_container_width=True,
                            hide_index=True
                        )

                        # Download button
                        csv_valid = df_valid.to_csv(index=False)
                        st.download_button(
                            "📥 Télécharger les factures valides (CSV)",
                            csv_valid,
                            "factures_valides.csv",
                            "text/csv",
                            key='download-valid-csv'
                        )
                    else:
                        st.info("Aucune facture valide")

                    # Display invalid invoices table
                    st.subheader("❌ Factures Invalides")
                    if invalid_results:
                        df_invalid = pd.DataFrame(invalid_results)
                        st.dataframe(
                            df_invalid,
                            use_container_width=True,
                            hide_index=True
                        )

                        # Download button
                        csv_invalid = df_invalid.to_csv(index=False)
                        st.download_button(
                            "📥 Télécharger les factures invalides (CSV)",
                            csv_invalid,
                            "factures_invalides.csv",
                            "text/csv",
                            key='download-invalid-csv'
                        )
                    else:
                        st.info("Aucune facture invalide")

                except Exception as e:
                    st.error(f"Error processing results: {str(e)}")
                    st.write("Debug - Result structure:", result)  # Debug line to see the structure

with tab2:
    st.header("Rechercher des Factures")

    col1, col2, col3 = st.columns(3)

    with col1:
        invoice_number = st.text_input("🔍 Numéro de Facture")
        status = st.selectbox("Statut", ["", "pending", "paid"])

    with col2:
        # Initialize date_from with None
        date_from = st.date_input(
            "Date de début",
            value=None,  # Start with no date selected
            min_value=datetime(2000, 1, 1),  # Allow dates from year 2000
            max_value=datetime.now(),  # Up to current date
            key="date_from"
        )
        min_amount = st.number_input("Montant minimum", min_value=0.0, step=100.0)

    with col3:
        # Initialize date_to with None
        date_to = st.date_input(
            "Date de fin",
            value=None,  # Start with no date selected
            min_value=datetime(2000, 1, 1),  # Allow dates from year 2000
            max_value=datetime.now(),  # Up to current date
            key="date_to"
        )
        max_amount = st.number_input("Montant maximum", min_value=0.0, step=100.0)

    if st.button("🔍 Rechercher", key="search_button"):
        # Debug information
        st.write("Valeurs saisies:")
        st.write(f"- Numéro de facture: {invoice_number}")
        st.write(f"- Dates: {date_from} - {date_to}")
        st.write(f"- Montants: {min_amount} - {max_amount}")
        st.write(f"- Statut: {status}")

        # Convert dates to string format only if they are selected
        date_from_str = date_from.strftime("%Y-%m-%d") if date_from else None
        date_to_str = date_to.strftime("%Y-%m-%d") if date_to else None

        result = search_invoices(
            invoice_number=invoice_number if invoice_number else None,
            date_from=date_from_str,
            date_to=date_to_str,
            min_amount=min_amount if min_amount > 0 else None,
            max_amount=max_amount if max_amount > 0 else None,
            status=status if status else None
        )

        if result and "invoices" in result:
            if result['invoices']:
                st.success(f"✅ {result['count']} facture(s) trouvée(s)!")

                # Create two columns for the arrays
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📄 Informations Principales")
                    data = []
                    for invoice in result['invoices']:
                        data.append({
                            'N° Facture': invoice.get('invoice_number', 'N/A'),
                            'Date': invoice.get('date', 'N/A'),
                            'Client': invoice.get('bill_to', 'N/A'),
                            'Montant Total': format_currency(invoice.get('total', 0)),
                            'TVA': format_currency(invoice.get('tax', 0)),
                            'Statut': invoice.get('status', 'pending')
                        })
                    df_main = pd.DataFrame(data)
                    st.dataframe(
                        df_main,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "N° Facture": st.column_config.TextColumn("N° Facture", width="medium"),
                            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                            "Montant Total": st.column_config.TextColumn("Montant Total", width="medium"),
                            "TVA": st.column_config.TextColumn("TVA", width="medium"),
                            "Statut": st.column_config.SelectboxColumn(
                                "Statut",
                                options=["pending", "paid"],
                                width="small"
                            )
                        }
                    )

                with col2:
                    st.subheader("🏦 Informations Bancaires")
                    data = []
                    for invoice in result['invoices']:
                        data.append({
                            'N° Facture': invoice.get('invoice_number', 'N/A'),
                            'Banque': invoice.get('bank_name', 'N/A'),
                            'N° Compte': invoice.get('bank_account_number', 'N/A'),
                            'GSTIN': invoice.get('gstin', 'N/A'),
                            'Date Création': invoice.get('created_at', 'N/A')
                        })
                    df_bank = pd.DataFrame(data)
                    st.dataframe(
                        df_bank,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "N° Facture": st.column_config.TextColumn("N° Facture", width="medium"),
                            "Banque": st.column_config.TextColumn("Banque", width="large"),
                            "N° Compte": st.column_config.TextColumn("N° Compte", width="medium"),
                            "GSTIN": st.column_config.TextColumn("GSTIN", width="medium"),
                            "Date Création": st.column_config.DateColumn("Date Création", format="DD/MM/YYYY HH:mm")
                        }
                    )

                # Download buttons
                st.subheader("📥 Téléchargements")
                col1, col2 = st.columns(2)
                with col1:
                    csv_main = df_main.to_csv(index=False)
                    st.download_button(
                        "📄 Télécharger Informations Principales (CSV)",
                        csv_main,
                        "factures_principales.csv",
                        "text/csv",
                        key='download-main'
                    )
                with col2:
                    csv_bank = df_bank.to_csv(index=False)
                    st.download_button(
                        "🏦 Télécharger Informations Bancaires (CSV)",
                        csv_bank,
                        "factures_bancaires.csv",
                        "text/csv",
                        key='download-bank'
                    )
            else:
                st.info("Aucune facture ne correspond aux critères de recherche.")
        else:
            st.error("❌ Erreur lors de la recherche ou aucun résultat trouvé.")
with tab3:
    st.header("Générer un Bilan Comptable")

    col1, col2 = st.columns(2)
    with col1:
        bilan_date_from = st.date_input("Période du", key="bilan_date_from")
    with col2:
        bilan_date_to = st.date_input("au", key="bilan_date_to")

    if st.button("📊 Générer le Bilan", key="bilan_button"):
        result = generate_bilan(
            date_from=bilan_date_from.strftime("%Y-%m-%d"),
            date_to=bilan_date_to.strftime("%Y-%m-%d")
        )

        if result:
            st.success("✅ Bilan comptable généré avec succès!")

            # Display invoice statistics
            st.subheader("📈 Statistiques des Factures")
            stats = result.get("statistiques_factures", {})

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Factures", stats.get("total_factures", 0))
                st.metric("Montant Total", format_currency(stats.get("montant_total", 0)))
            with col2:
                st.metric("En Attente", stats.get("factures_en_attente", 0))
                st.metric("Total HT", format_currency(stats.get("total_ht", 0)))
            with col3:
                st.metric("Payées", stats.get("factures_payées", 0))
                st.metric("Total TVA", format_currency(stats.get("total_tva", 0)))

            # Display error statistics
            st.subheader("❌ Statistiques des Erreurs")
            error_stats = result.get("statistiques_erreurs", {})

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Factures Invalides", error_stats.get("total_factures_invalides", 0))
            with col2:
                st.metric("Types d'Erreurs", error_stats.get("types_erreurs_uniques", 0))

            # Display common errors
            if error_stats.get("erreurs_fréquentes"):
                st.write("Erreurs les plus fréquentes:")
                for error in error_stats["erreurs_fréquentes"]:
                    st.write(f"- {error['message']} ({error['occurrences']} occurrences)")

            # Download button for the report
            st.download_button(
                "📥 Télécharger le bilan complet (JSON)",
                json.dumps(result, indent=2, ensure_ascii=False),
                f"bilan_comptable_{time.strftime('%Y%m%d')}.json",
                "application/json",
                key='download-bilan'
            )

with tab4:
    st.header("💰 Gestion des Paiements Avancés")

    payment_tab1, payment_tab2, payment_tab3 = st.tabs([
        "✂️ Division Chèques",
        "🔄 Remplacement Chèques",
        "📊 Suivi Impayés"
    ])

    
    with payment_tab1:

        st.subheader("Division de Chèques")


        with st.form("divide_check_form"):

            check_id = st.text_input("ID du Chèque")

            amounts = st.text_input("Montants de la division (séparés par des virgules)")


            if st.form_submit_button("✂️ Diviser le Chèque"):

                if check_id and amounts:

                    try:

                        amounts_list = [float(amount.strip()) for amount in amounts.split(",")]

                        division_request = {"amounts": amounts_list}

                        response = session.post(f"{API_URL}{PAYMENTS_PREFIX}/divide/{check_id}", json=division_request)


                        if response.status_code == 200:

                            st.success("✅ Chèque divisé avec succès!")

                            st.json(response.json())

                        else:

                            st.error(f"❌ Erreur: {response.text}")

                    except ValueError as e:

                        st.error(f"Erreur de format: {str(e)}")

                    except Exception as e:

                        st.error(f"Une erreur s'est produite: {str(e)}")


    with payment_tab2:
        st.subheader("Remplacement de Chèques")

        with st.form("replace_check_form"):
            old_check_id = st.text_input("ID du Chèque à Remplacer")

            col1, col2 = st.columns(2)
            with col1:
                new_check_number = st.text_input("Nouveau Numéro de Chèque")
                new_amount = st.number_input("Montant", min_value=0.0, step=100.0)
                new_bank_name = st.text_input("Banque")
            with col2:
                new_bank_branch = st.text_input("Agence")
                new_bank_account = st.text_input("Numéro de Compte")
                new_swift_code = st.text_input("Code SWIFT")

            if st.form_submit_button("🔄 Remplacer le Chèque"):
                try:
                    new_check_info = {
                        "check_number": new_check_number,
                        "amount": new_amount,
                        "bank_name": new_bank_name,
                        "bank_branch": new_bank_branch,
                        "bank_account": new_bank_account,
                        "swift_code": new_swift_code
                    }

                    response = session.post(
                        f"{API_URL}{PAYMENTS_PREFIX}/replace/{old_check_id}",
                        json=new_check_info
                    )

                    if response.status_code == 200:
                        st.success("✅ Chèque remplacé avec succès!")
                        result = response.json()

                        if "data" in result:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("Ancien Chèque:")
                                st.json(result["data"].get("old_check", {}))
                            with col2:
                                st.write("Nouveau Chèque:")
                                st.json(result["data"].get("new_check", {}))
                    else:
                        st.error(f"❌ Erreur: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

    with payment_tab3:
        st.subheader("Suivi des Impayés")

        # Filtres
        col1, col2 = st.columns(2)
        with col1:
            client_id = st.text_input("ID Client (optionnel)")
        with col2:
            check_number = st.text_input("Numéro de Chèque (optionnel)")

        if st.button("🔍 Rechercher les Impayés"):
            try:
                params = {"client_id": client_id} if client_id else {}
                response = session.get(
                    f"{API_URL}{PAYMENTS_PREFIX}/unpaid",
                    params=params
                )

                if response.status_code == 200:
                    result = response.json()
                    unpaid_checks = result.get("data", [])
                    if unpaid_checks:
                        df = pd.DataFrame(unpaid_checks)

                        # Format dates and amounts
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
                        if 'amount' in df.columns:
                            df['amount'] = df['amount'].apply(format_currency)
                        if 'days_overdue' in df.columns:
                            df['days_overdue'] = df['days_overdue'].astype(str) + " jours"

                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "check_number": "N° Chèque",
                                "amount": "Montant",
                                "date": "Date",
                                "bank_name": "Banque",
                                "invoice_number": "N° Facture",
                                "days_overdue": "Retard"
                            }
                        )

                        # Download button
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "📥 Télécharger le rapport (CSV)",
                            csv,
                            "cheques_impayes.csv",
                            "text/csv",
                            key='download-unpaid'
                        )
                    else:
                        st.info("Aucun chèque impayé trouvé")
                else:
                    st.error(f"❌ Erreur: {response.text}")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

        # Check History
        st.subheader("Historique des Chèques")
        check_number_history = st.text_input("Numéro de Chèque", key="history_check_number")

        if st.button("📋 Voir l'historique"):
            try:
                response = session.get(
                    f"{API_URL}{PAYMENTS_PREFIX}/history/{check_number_history}"
                )

                if response.status_code == 200:
                    result = response.json()
                    history = result.get("data", {})

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("📝 Informations du Chèque")
                        check_info = history.get("check_info", {})
                        st.write(f"Numéro: {check_info.get('number', 'N/A')}")
                        st.write(f"Montant: {format_currency(check_info.get('amount', 0))}")
                        st.write(f"Statut: {check_info.get('status', 'N/A')}")
                        st.write(f"Banque: {check_info.get('bank_name', 'N/A')}")
                        st.write(f"Date de création: {check_info.get('creation_date', 'N/A')}")

                        divisions = history.get("divisions", [])
                        if divisions:
                            st.write("✂️ Divisions")
                            df_divisions = pd.DataFrame(divisions)
                            if 'date' in df_divisions.columns:
                                df_divisions['date'] = pd.to_datetime(df_divisions['date']).dt.strftime('%d/%m/%Y')
                            if 'amount' in df_divisions.columns:
                                df_divisions['amount'] = df_divisions['amount'].apply(format_currency)
                            st.dataframe(df_divisions, hide_index=True)

                    with col2:
                        transaction_info = history.get("transaction_info", {})
                        if transaction_info:
                            st.write("💳 Information de Transaction")
                            st.write(f"ID: {transaction_info.get('id', 'N/A')}")
                            st.write(f"Statut: {transaction_info.get('status', 'N/A')}")
                            st.write(f"Date: {transaction_info.get('date', 'N/A')}")
                else:
                    st.error(f"❌ Erreur: {response.text}")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

# Rest of the tabs remain unchanged


with tab5:
    st.header("👥 Gestion des Clients")

    # Sous-onglets pour les différentes fonctionnalités clients
    client_tab1, client_tab2, client_tab3, client_tab4 = st.tabs([
        "📋 Liste des Clients",
        "➕ Nouveau Client",
        "💼 Grands Comptes",
        "📊 Tableau de Bord"
    ])

    with client_tab1:
        st.subheader("Liste des Clients")
        try:
            response = session.get(f"{API_URL}/clients/")
            if response.status_code == 200:
                clients = response.json()

                # Filtres
                col1, col2 = st.columns(2)
                with col1:
                    search = st.text_input("🔍 Rechercher par nom")
                with col2:
                    status_filter = st.multiselect(
                        "Statut",
                        ["standard", "key_account", "inactive"]
                    )

                # Filtrer les clients
                filtered_clients = clients
                if search:
                    filtered_clients = [c for c in filtered_clients
                                        if search.lower() in c['name'].lower()]
                if status_filter:
                    filtered_clients = [c for c in filtered_clients
                                        if c['status'] in status_filter]

                if filtered_clients:
                    df = pd.DataFrame(filtered_clients)
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": "Nom",
                            "email": "Email",
                            "status": st.column_config.SelectboxColumn(
                                "Statut",
                                options=["standard", "key_account", "inactive"]
                            ),
                            "revenue": st.column_config.NumberColumn(
                                "Chiffre d'Affaires",
                                format="%.2f €"
                            )
                        }
                    )

                    # Export
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Exporter la liste (CSV)",
                        csv,
                        "clients.csv",
                        "text/csv"
                    )
                else:
                    st.info("Aucun client trouvé")
        except Exception as e:
            st.error(f"Erreur lors de la récupération des clients: {str(e)}")

    with client_tab2:
        st.subheader("Ajouter un Nouveau Client")
        with st.form("new_client_form"):
            name = st.text_input("Nom*")
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Email*")
                phone = st.text_input("Téléphone")
            with col2:
                status = st.selectbox(
                    "Statut",
                    ["standard", "key_account", "inactive"]
                )
                address = st.text_area("Adresse")

            if st.form_submit_button("✅ Créer le Client"):
                if not name or not email:
                    st.error("Le nom et l'email sont obligatoires")
                else:
                    try:
                        client_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "address": address,
                            "status": status
                        }
                        response = session.post(
                            f"{API_URL}/clients/",
                            json=client_data
                        )
                        if response.status_code == 200:
                            st.success("✅ Client créé avec succès!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Erreur: {response.text}")
                    except Exception as e:
                        st.error(f"Erreur lors de la création: {str(e)}")

    with client_tab3:
        st.subheader("Grands Comptes")
        try:
            response = session.get(f"{API_URL}/clients/key-accounts")
            if response.status_code == 200:
                key_accounts = response.json()

                if key_accounts:
                    for account in key_accounts:
                        with st.expander(f"🏢 {account['client_info']['name']}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write("📋 Informations")
                                st.json(account["client_info"])

                            with col2:
                                st.write("📊 Métriques")
                                metrics = account["metrics"]
                                st.metric(
                                    "Total Factures",
                                    metrics["invoices"]["total"]
                                )
                                st.metric(
                                    "Ratio de Paiement",
                                    f"{metrics['invoices']['payment_ratio']:.1%}"
                                )
                                st.metric(
                                    "Montant Total",
                                    format_currency(metrics["amounts"]["total"])
                                )
                else:
                    st.info("Aucun grand compte trouvé")

        except Exception as e:
                 st.error(f"Erreur: {str(e)}")

with client_tab4:
    st.subheader("📊 Tableau de Bord Client")

    try:
        # Sélection du client
        response = session.get(f"{API_URL}/clients/")
        if response.status_code != 200:
            st.error("❌ Erreur de connexion au serveur")
            st.stop()

        clients = response.json()
        if not clients:
            st.info("ℹ️ Aucun client disponible")
            st.stop()

        # Sélection du client avec statut
        selected_client = st.selectbox(
            "🔍 Sélectionner un client",
            options=[c["id"] for c in clients],
            format_func=lambda x: next((f"{c['name']} - {c['status'].upper()}"
                                        for c in clients if c["id"] == x), x)
        )

        if selected_client:
            # Récupération des données client
            dashboard_response = session.get(f"{API_URL}/clients/{selected_client}/dashboard")
            if dashboard_response.status_code != 200:
                st.error("❌ Erreur lors de la récupération des données")
                st.stop()

            data = dashboard_response.json()
            client_info = data["client_info"]
            metrics = data["metrics"]

            # Informations Client
            st.markdown("### 📋 Informations Client")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.info(f"**Status**: {client_info['status'].upper()}")
            with col2:
                st.info(f"**Email**: {client_info.get('email', 'N/A')}")
            with col3:
                st.info(f"**Téléphone**: {client_info.get('phone', 'N/A')}")

            # Métriques Financières
            st.markdown("### 💰 Métriques Financières")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Chiffre d'Affaires",
                    format_currency(client_info['revenue'])
                )
            with col2:
                st.metric(
                    "Factures Payées",
                    f"{metrics['invoices']['paid']}/{metrics['invoices']['total']}"
                )
            with col3:
                payment_ratio = metrics['invoices']['payment_ratio']
                st.metric(
                    "Taux de Paiement",
                    f"{payment_ratio:.1%}"
                )
            with col4:
                st.metric(
                    "Montant Impayé",
                    format_currency(metrics['amounts']['remaining'])
                )

            # Historique des Paiements
            st.markdown("### 📅 Historique des Paiements")

            # Filtres
            col1, col2 = st.columns(2)
            with col1:
                payment_status = st.multiselect(
                    "Statut",
                    ["completed", "pending", "failed"],
                    default=["completed", "pending"]
                )
            with col2:
                min_amount = st.number_input(
                    "Montant minimum",
                    min_value=0.0,
                    step=100.0
                )

            # Affichage des paiements
            payments = data.get("payment_history", [])
            if payments:
                df = pd.DataFrame(payments)

                # Application des filtres
                if payment_status:
                    df = df[df['status'].isin(payment_status)]
                if min_amount > 0:
                    df = df[df['amount'] >= min_amount]

                # Formatage
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
                df['amount'] = df['amount'].apply(format_currency)
                df.columns = ['ID', 'Montant', 'Méthode', 'Statut', 'Date', 'Facture']

                # Affichage
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # Statistiques
                st.markdown("#### 📊 Statistiques")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Total des paiements",
                        format_currency(sum(float(str(x).replace('€', '').replace(' ', '').replace(',', ''))
                                            for x in df['Montant']))
                    )
                with col2:
                    st.metric("Nombre de paiements", len(df))

            else:
                st.info("ℹ️ Aucun historique de paiement disponible")

            # Export
            st.markdown("### 📥 Export des Données")
            if st.button("💾 Télécharger le Rapport"):
                report = {
                    "client": client_info,
                    "metrics": metrics,
                    "payments": payments
                }
                st.download_button(
                    "📄 Télécharger (JSON)",
                    json.dumps(report, indent=2, ensure_ascii=False),
                    f"rapport_client_{selected_client}_{datetime.now().strftime('%Y%m%d')}.json",
                    "application/json"
                )

    except Exception as e:
        st.error(f"❌ Erreur : {str(e)}")
        if st.button("🔄 Réessayer"):
            st.rerun()

with tab6:
    st.header("📦 Gestion des Stocks")

    # Create sub-tabs for different stock management features
    stock_tab1, stock_tab2, stock_tab3, stock_tab4 = st.tabs([
        "📊 Vue d'ensemble",
        "⚠️ Alertes Stock",
        "🔄 Mise à jour Stock",
        "📈 Analyses"
    ])

    with stock_tab1:
        st.subheader("Vue d'ensemble des Stocks")

        try:
            # Get stock summary
            response = session.get(f"{API_URL}/api/stock/summary")
            if response.status_code == 200:
                summary = response.json()['data']

                # Display metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Produits en Stock Faible", summary['low_stock_count'])
                with col2:
                    st.metric("Produits Expirés", summary['expired_count'])

                # Display low stock items
                if summary['low_stock_items']:
                    st.subheader("⚠️ Produits en Stock Faible")
                    df_low = pd.DataFrame(summary['low_stock_items'])
                    st.dataframe(
                        df_low,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": "Nom du Produit",
                            "current_stock": "Stock Actuel",
                            "threshold": "Seuil d'Alerte"
                        }
                    )

                # Display expired items
                if summary['expired_items']:
                    st.subheader("⚠️ Produits Expirés")
                    df_expired = pd.DataFrame(summary['expired_items'])
                    df_expired['expiration_date'] = pd.to_datetime(df_expired['expiration_date']).dt.strftime(
                        '%d/%m/%Y')
                    st.dataframe(
                        df_expired,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": "Nom du Produit",
                            "expiration_date": "Date d'Expiration"
                        }
                    )
            else:
                st.error("Erreur lors de la récupération du résumé des stocks")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    with stock_tab2:
        st.subheader("Alertes de Stock")

        col1, col2 = st.columns(2)
        with col1:
            # Low stock alerts
            try:
                response = session.get(f"{API_URL}/api/stock/check/low-stock")
                if response.status_code == 200:
                    alerts = response.json()['data']
                    if alerts:
                        st.warning("Produits en Stock Faible")
                        df = pd.DataFrame(alerts)
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.success("Aucun produit en stock faible")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

        with col2:
            # Expired products alerts
            try:
                response = session.get(f"{API_URL}/api/stock/check/expired")
                if response.status_code == 200:
                    expired = response.json()['data']
                    if expired:
                        st.error("Produits Expirés")
                        df = pd.DataFrame(expired)
                        df['expiration_date'] = pd.to_datetime(df['expiration_date']).dt.strftime('%d/%m/%Y')
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.success("Aucun produit expiré")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

    with stock_tab3:
        st.subheader("Mise à jour des Stocks")

        with st.form("update_stock_form"):
            product_id = st.text_input("ID du Produit")
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("Quantité", min_value=1, value=1)
            with col2:
                operation = st.selectbox(
                    "Opération",
                    ["increase", "decrease"],
                    format_func=lambda x: "Augmenter" if x == "increase" else "Diminuer"
                )

            if st.form_submit_button("Mettre à jour"):
                try:
                    response = session.put(
                        f"{API_URL}/api/stock/update/{product_id}",
                        json={
                            "quantity_change": quantity,
                            "operation": operation
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()['data']
                        st.success(f"Stock mis à jour avec succès! Nouveau niveau: {result['new_stock_level']}")
                    else:
                        st.error("Erreur lors de la mise à jour du stock")
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

    with stock_tab4:
        st.subheader("Analyses des Stocks")

        # Product analytics
        product_id = st.text_input("ID du Produit à Analyser")
        if product_id:
            try:
                response = session.get(f"{API_URL}/api/stock/analytics/product/{product_id}")
                if response.status_code == 200:
                    analytics = response.json()['data']

                    # Display product info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Stock Actuel", analytics['stock_info']['current_stock'])
                    with col2:
                        st.metric("Unités Vendues", analytics['sales_metrics']['total_units_sold'])
                    with col3:
                        st.metric(
                            "Chiffre d'Affaires",
                            f"{analytics['sales_metrics']['total_revenue']:,.2f} €"
                        )

                    # Create visualizations
                    if analytics['sales_metrics']['total_units_sold'] > 0:
                        # Sales trend visualization
                        st.subheader("Tendance des Ventes")
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=analytics.get('sales_metrics', {}).get('sales_dates', []),
                            y=analytics.get('sales_metrics', {}).get('sales_quantities', []),
                            mode='lines+markers',
                            name='Unités Vendues'
                        ))
                        st.plotly_chart(fig, use_container_width=True)

                    # Stock level visualization
                    st.subheader("Niveau de Stock")
                    current_stock = analytics['stock_info']['current_stock']
                    threshold = analytics['stock_info']['alert_threshold']

                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=current_stock,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Niveau de Stock Actuel"},
                        gauge={
                            'axis': {'range': [None, max(current_stock * 1.5, threshold * 2)]},
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': threshold
                            }
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)

                    # Display detailed information
                    with st.expander("Voir les détails"):
                        st.json(analytics)
                else:
                    st.error("Erreur lors de la récupération des analyses")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
