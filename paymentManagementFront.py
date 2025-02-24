import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

API_URL = "http://127.0.0.1:8000"


def format_currency(amount: float) -> str:
    """Formater un montant en devise"""
    return f"{amount:,.2f} €"


def display_check_management():
    st.header("🏦 Gestion des Chèques")

    # Onglets pour les différentes fonctionnalités
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Traitement Chèque",
        "✂️ Division Chèque",
        "🔄 Remplacement Chèque",
        "📊 Suivi Impayés"
    ])

    with tab1:
        st.subheader("Traiter un Nouveau Chèque")

        # Formulaire de traitement de chèque
        with st.form("process_check_form"):
            invoice_id = st.text_input("ID Facture")
            check_number = st.text_input("Numéro de Chèque")
            amount = st.number_input("Montant", min_value=0.0, step=100.0)
            bank_name = st.text_input("Banque")
            bank_branch = st.text_input("Agence")
            bank_account = st.text_input("Numéro de Compte")
            swift_code = st.text_input("Code SWIFT")

            if st.form_submit_button("🏦 Traiter le Chèque"):
                try:
                    check_info = {
                        "check_number": check_number,
                        "amount": amount,
                        "bank_name": bank_name,
                        "bank_branch": bank_branch,
                        "bank_account": bank_account,
                        "swift_code": swift_code
                    }

                    response = requests.post(
                        f"{API_URL}/payments/check/process/{invoice_id}",
                        json=check_info
                    )

                    if response.status_code == 200:
                        st.success("✅ Chèque traité avec succès!")
                        st.json(response.json())
                    else:
                        st.error(f"❌ Erreur: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

    with tab2:
        st.subheader("Diviser un Chèque")

        # Formulaire de division de chèque
        with st.form("divide_check_form"):
            check_id = st.text_input("ID du Chèque")
            num_divisions = st.number_input("Nombre de Divisions", min_value=2, max_value=10, value=2)

            amounts = []
            for i in range(num_divisions):
                amount = st.number_input(f"Montant {i + 1}", min_value=0.0, step=100.0, key=f"div_{i}")
                amounts.append(amount)

            if st.form_submit_button("✂️ Diviser le Chèque"):
                try:
                    response = requests.post(
                        f"{API_URL}/payments/check/divide/{check_id}",
                        json=amounts
                    )

                    if response.status_code == 200:
                        st.success("✅ Chèque divisé avec succès!")
                        result = response.json()

                        # Afficher les divisions
                        st.write("Divisions créées:")
                        for div in result["divisions"]:
                            st.write(f"- {format_currency(div['amount'])} ({div['status']})")
                    else:
                        st.error(f"❌ Erreur: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

    with tab3:
        st.subheader("Remplacer un Chèque")

        # Formulaire de remplacement de chèque
        with st.form("replace_check_form"):
            old_check_id = st.text_input("ID du Chèque à Remplacer")
            new_check_number = st.text_input("Nouveau Numéro de Chèque")
            new_amount = st.number_input("Montant", min_value=0.0, step=100.0)
            new_bank_name = st.text_input("Banque")
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

                    response = requests.post(
                        f"{API_URL}/payments/check/replace/{old_check_id}",
                        json=new_check_info
                    )

                    if response.status_code == 200:
                        st.success("✅ Chèque remplacé avec succès!")
                        result = response.json()

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("Ancien Chèque:")
                            st.json(result["old_check"])
                        with col2:
                            st.write("Nouveau Chèque:")
                            st.json(result["new_check"])
                    else:
                        st.error(f"❌ Erreur: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

    with tab4:
        st.subheader("Suivi des Chèques Impayés")

        # Filtres
        client_id = st.text_input("ID Client (optionnel)")
        if st.button("🔍 Rechercher"):
            try:
                params = {"client_id": client_id} if client_id else {}
                response = requests.get(
                    f"{API_URL}/payments/check/unpaid/",
                    params=params
                )

                if response.status_code == 200:
                    unpaid_checks = response.json()
                    if unpaid_checks:
                        df = pd.DataFrame(unpaid_checks)

                        # Formater les colonnes
                        df["amount"] = df["amount"].apply(format_currency)
                        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d/%m/%Y")

                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True
                        )

                        # Téléchargement
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "📥 Télécharger le rapport (CSV)",
                            csv,
                            "cheques_impayes.csv",
                            "text/csv"
                        )
                    else:
                        st.info("Aucun chèque impayé trouvé")
                else:
                    st.error(f"❌ Erreur: {response.text}")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

        # Historique d'un chèque
        st.subheader("Historique d'un Chèque")
        check_number = st.text_input("Numéro de Chèque")
        if st.button("📋 Voir l'historique"):
            try:
                response = requests.get(
                    f"{API_URL}/payments/check/history/{check_number}"
                )

                if response.status_code == 200:
                    history = response.json()

                    # Afficher les informations du chèque
                    st.write("📝 Informations du Chèque:")
                    st.json(history["check_info"])

                    # Afficher les divisions si présentes
                    if history["divisions"]:
                        st.write("✂️ Divisions:")
                        for div in history["divisions"]:
                            st.write(f"- {format_currency(div['amount'])} ({div['status']})")

                    # Afficher les informations de transaction
                    if history["transaction_info"]:
                        st.write("💳 Transaction:")
                        st.json(history["transaction_info"])
                else:
                    st.error(f"❌ Erreur: {response.text}")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")


if __name__ == "__main__":
    st.set_page_config(
        page_title="Gestion des Paiements Avancés",
        page_icon="🏦",
        layout="wide"
    )
    display_check_management()
