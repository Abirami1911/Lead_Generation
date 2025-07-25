import streamlit as st
import pandas as pd
import requests
import time

# -------------------
# 🔐 Authentication (optional)
# -------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["authenticated"] = True
        else:
            st.error("❌ Incorrect password")

    if "authenticated" not in st.session_state:
        st.text_input("Enter password", type="password", on_change=password_entered, key="password")
        return False
    elif st.session_state["authenticated"]:
        return True

# Enable auth only if desired
if not check_password():
    st.stop()

# -------------------
# 🌐 Apollo API Setup
# -------------------
API_KEY = st.secrets["default"]["API_KEY"]
headers = {
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json',
    'X-Api-Key': API_KEY
}
search_url = 'https://api.apollo.io/v1/mixed_people/search'
enrich_url = "https://api.apollo.io/api/v1/people/bulk_match"

# -------------------
# 🔎 UI Inputs
# -------------------
st.title("Database Creation App 💻")
org_name = st.text_input("Enter Organization Name", value="Agilisium")
titles = st.text_input("Enter Titles (comma-separated)", value="Director,IT")
max_pages = st.slider("Select Max Pages", 1, 100, 5)

if st.button("Fetch Leads"):
    st.info("Fetching leads from Apollo...")
    bulk_details = []
    leads = []
    page = 1

    while page <= max_pages:
        body = {
            'q_organization_name': org_name,
            'person_titles': [title.strip() for title in titles.split(",")],
            'page': page
        }
        response = requests.post(search_url, headers=headers, json=body)
        if response.status_code == 200:
            data = response.json()
            people = data.get('people', [])
            if not people:
                st.warning(f"No more people found on page {page}. Stopping early.")
                break
            for person in people:
                first_name = person.get("first_name")
                last_name = person.get("last_name")
                organization = person.get("organization", {})
                organization_name = organization.get("name")
                domain = organization.get("website_url")

                if first_name and last_name and organization_name and domain:
                    bulk_details.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization_name": organization_name,
                        "domain": domain
                    })
        else:
            st.error(f"API error on page {page}: {response.status_code}")
            break
        page += 1
        time.sleep(1)

    # Enrichment
    def chunk_list(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    for chunk in chunk_list(bulk_details, 10):
        enrich_payload = {
            "details": chunk,
            "reveal_personal_emails": False,
            "reveal_phone_number": False,
        }
        enrich_response = requests.post(enrich_url, headers=headers, json=enrich_payload)
        if enrich_response.status_code == 200:
            enrichment_data = enrich_response.json()
            for person in enrichment_data.get('matches', []):
                if not person:
                    continue
                leads.append({
                    "name": person.get("name"),
                    "title": person.get("title"),
                    "Location": person.get("Location"),
                    "city": person.get("city"),
                    "state": person.get("state"),
                    "organization_name": person.get("organization", {}).get("name"),
                    "LinkedIn_URL": person.get("linkedin_url"),
                    "Phone": person.get("organization", {}).get("phone"),
                    "email": person.get("email")
                })
        else:
            st.error("Enrichment failed. Please check API limits.")

    # Display results
    if leads:
        df = pd.DataFrame(leads)
        st.success(f"✅ {len(leads)} leads retrieved and enriched.")
        st.dataframe(df)

        # Download option
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f'apollo_leads_{org_name.lower()}.csv',
            mime='text/csv'
        )
    else:
        st.warning("No leads found or enriched.")
