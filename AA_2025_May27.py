import streamlit as st
import requests
import pandas as pd
import time
import json
from io import StringIO

# Constants
API_KEY = 'qRehVBgtaNIhjLnddQ3UmQ'
headers = {
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json',
    'X-Api-Key': API_KEY
}
search_url = 'https://api.apollo.io/v1/mixed_people/search'
enrich_url = "https://api.apollo.io/api/v1/people/bulk_match"

# UI
st.title("Database Creation App 💻")

org_name = st.text_input("Organization Name", value="Agilisium")
titles_input = st.text_input("Person Titles (comma-separated)", value="Director")
max_pages = st.number_input("Max Pages to Scrape", min_value=1, max_value=100, value=10)

if st.button("Run Enrichment"):
    titles = [title.strip() for title in titles_input.split(",") if title.strip()]
    bulk_details = []
    leads = []
    page = 1

    with st.spinner("Scraping people data..."):
        while page <= max_pages:
            body = {
                'q_organization_name': org_name,
                'person_titles': titles,
                'page': page
            }
            response = requests.post(search_url, headers=headers, json=body)
            if response.status_code == 200:
                data = response.json()
                people = data.get('people', [])

                if not people:
                    st.warning(f"No more people found on page {page}.")
                    break

                for person in people:
                    first_name = person.get("first_name")
                    last_name = person.get("last_name")
                    org = person.get("organization", {})
                    org_name = org.get("name")
                    domain = org.get("website_url")

                    if first_name and last_name and org_name and domain:
                        bulk_details.append({
                            "first_name": first_name,
                            "last_name": last_name,
                            "organization_name": org_name,
                            "domain": domain
                        })

                page += 1
                time.sleep(1)
            else:
                st.error(f"Error {response.status_code} on page {page}: {response.text}")
                break

    # Enrichment
    def chunk_list(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    with st.spinner("Enriching people data..."):
        for i, chunk in enumerate(chunk_list(bulk_details, 10), start=1):
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

                    name = person.get("name")
                    title = person.get("title")
                    organization = person.get("organization", {})
                    org_name = organization.get("name")
                    domain = organization.get("website_url")
                    linkedin_url = person.get('linkedin_url')
                    phone = organization.get('phone')
                    email = person.get("email")

                    leads.append({
                        "name": name,
                        "title": title,
                        "organization_name": org_name,
                        "LinkedIn_URL": linkedin_url,
                        "Phone": phone,
                        "email": email
                    })
            else:
                st.error(f"Enrichment failed for batch {i}: {enrich_response.text}")

    if leads:
        df = pd.DataFrame(leads)
        st.success(f"✅ Scraping done. {len(leads)} leads enriched.")
        st.dataframe(df)

        # Download CSV
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f'apollo_data_{org_name}.csv',
            mime='text/csv'
        )
    else:
        st.warning("No leads enriched.")
