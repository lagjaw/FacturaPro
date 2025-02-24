import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

API_URL = "http://127.0.0.1:8000"


def format_currency(amount: float) -> str:
    """Formater un montant en devise"""
    return f"{amount:,.2f} €"


def display_client_management():
    st.header("👥 Gestion des Clients")

    # Onglets principaux
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tableau de Bord",
        "➕ Gestion Clients",
        "💼 Grands Comptes",
        "📈 Analyses"
    ])

    with tab1:
        st.subheader("Tableau de Bord Clients")

        try:
            # Récupérer tous les clients
            response = requests.get(f"{API_URL}/clients/")
            if response.status_code == 200:
                clients = response.json()

                # Métriques globales
                total_clients = len(clients)
                key_accounts = len([c for c in clients if c["status"] == "key_account"])
                total_revenue = sum(c.get("revenue", 0) for c in clients)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Clients", total_clients)
                with col2:
                    st.metric("Grands Comptes", key_accounts)
                with col3:
                    st.metric("CA Total", format_currency(total_revenue))

                # Tableau des clients
                if clients:
                    df = pd.DataFrame(clients)
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "revenue": st.column_config.NumberColumn(
                                "Chiffre d'Affaires",
                                format="%.2f €"
                            )
                        }
                    )
            else:
                st.error("Erreur lors de la récupération des clients")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    with tab2:
        st.subheader("Gestion des Clients")

        # Création de client
        with st.expander("➕ Créer un Nouveau Client"):
            with st.form("create_client_form"):
                name = st.text_input("Nom")
                email = st.text_input("Email")
                phone = st.text_input("Téléphone")
                address = st.text_area("Adresse")
                status = st.selectbox(
                    "Statut",
                    ["standard", "key_account", "inactive"]
                )

                if st.form_submit_button("Créer"):
                    try:
                        client_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "address": address,
                            "status": status
                        }

                        response = requests.post(
                            f"{API_URL}/clients/",
                            json=client_data
                        )

                        if response.status_code == 200:
                            st.success("✅ Client créé avec succès!")
                        else:
                            st.error(f"❌ Erreur: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")

        # Modification de client
        with st.expander("✏️ Modifier un Client"):
            # Sélection du client
            response = requests.get(f"{API_URL}/clients/")
            if response.status_code == 200:
                clients = response.json()
                client_names = {c["id"]: c["name"] for c in clients}

                selected_client = st.selectbox(
                    "Sélectionner un client",
                    options=list(client_names.keys()),
                    format_func=lambda x: client_names[x]
                )

                if selected_client:
                    client_response = requests.get(f"{API_URL}/clients/{selected_client}")
                    if client_response.status_code == 200:
                        client = client_response.json()

                        with st.form("update_client_form"):
                            new_name = st.text_input("Nom", value=client["name"])
                            new_email = st.text_input("Email", value=client["email"])
                            new_phone = st.text_input("Téléphone", value=client["phone"])
                            new_address = st.text_area("Adresse", value=client["address"])
                            new_status = st.selectbox(
                                "Statut",
                                ["standard", "key_account", "inactive"],
                                index=["standard", "key_account", "inactive"].index(client["status"])
                            )

                            if st.form_submit_button("Mettre à jour"):
                                try:
                                    update_data = {
                                        "name": new_name,
                                        "email": new_email,
                                        "phone": new_phone,
                                        "address": new_address,
                                        "status": new_status
                                    }

                                    response = requests.put(
                                        f"{API_URL}/clients/{selected_client}",
                                        json=update_data
                                    )

                                    if response.status_code == 200:
                                        st.success("✅ Client mis à jour avec succès!")
                                    else:
                                        st.error(f"❌ Erreur: {response.text}")
                                except Exception as e:
                                    st.error(f"❌ Erreur: {str(e)}")

    with tab3:
        st.subheader("Grands Comptes")

        try:
            response = requests.get(f"{API_URL}/clients/key-accounts")
            if response.status_code == 200:
                key_accounts = response.json()

                if key_accounts:
                    for account in key_accounts:
                        with st.expander(f"🏢 {account['client_info']['name']}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write("📋 Informations Client")
                                st.json(account["client_info"])

                            with col2:
                                st.write("📊 Métriques")
                                metrics = account["metrics"]

                                # Créer un graphique circulaire pour le ratio de paiement
                                fig = go.Figure(data=[go.Pie(
                                    labels=['Payées', 'En attente'],
                                    values=[
                                        metrics["invoices"]["paid"],
                                        metrics["invoices"]["total"] - metrics["invoices"]["paid"]
                                    ],
                                    hole=.3
                                )])
                                st.plotly_chart(fig)

                                st.metric(
                                    "Montant Total",
                                    format_currency(metrics["amounts"]["total"])
                                )
                else:
                    st.info("Aucun grand compte trouvé")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    with tab4:
        st.subheader("Analyses Clients")

        # Sélection du client
        response = requests.get(f"{API_URL}/clients/")
        if response.status_code == 200:
            clients = response.json()
            client_names = {c["id"]: c["name"] for c in clients}

            selected_client = st.selectbox(
                "Sélectionner un client pour l'analyse",
                options=list(client_names.keys()),
                format_func=lambda x: client_names[x],
                key="analysis_client_select"
            )

            if selected_client:
                # Récupérer le tableau de bord
                dashboard_response = requests.get(
                    f"{API_URL}/clients/{selected_client}/dashboard"
                )

                if dashboard_response.status_code == 200:
                    dashboard = dashboard_response.json()

                    # Afficher les informations principales
                    st.write("📊 Métriques Principales")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Total Factures",
                            dashboard["metrics"]["invoices"]["total"]
                        )
                    with col2:
                        st.metric(
                            "Factures Payées",
                            dashboard["metrics"]["invoices"]["paid"]
                        )
                    with col3:
                        st.metric(
                            "Ratio de Paiement",
                            f"{dashboard['metrics']['invoices']['payment_ratio']:.2%}"
                        )

                    # Graphique des paiements
                    st.write("💰 Historique des Paiements")
                    payment_history = dashboard["payment_history"]
                    if payment_history:
                        df_payments = pd.DataFrame(payment_history)
                        df_payments["date"] = pd.to_datetime(df_payments["date"])

                        fig = px.line(
                            df_payments,
                            x="date",
                            y="amount",
                            title="Évolution des Paiements"
                        )
                        st.plotly_chart(fig)

                    # Analyse des retards
                    st.write("⏰ Analyse des Retards")
                    delay_analysis = dashboard["delay_analysis"]

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Factures en Retard",
                            delay_analysis["total_delayed_invoices"]
                        )
                    with col2:
                        st.metric(
                            "Retard Moyen (jours)",
                            f"{delay_analysis['average_delay_days']:.1f}"
                        )


if __name__ == "__main__":
    st.set_page_config(
        page_title="Gestion des Clients",
        page_icon="👥",
        layout="wide"
    )
    display_client_management()
