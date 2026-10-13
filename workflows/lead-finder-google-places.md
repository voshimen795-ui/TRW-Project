# Lean Mean Lead Finder Machine (course version)

Same steps as the course: Edit Fields → Get Coordinates → Get Places →
Split Out → Append row in sheet → Aggregate → Insert row → If → Wait →
Get row(s) → Get Places1 → Split Out1 → back to Append row in sheet.
It loops through up to 3 pages (60 businesses max, Google's limit).

One difference: the course video uses the old "Places API". Google no
longer lets new projects turn that on, so this uses **Places API (New)**.
The results are the same.

## 1. Get your Google Maps API key (no business needed)

1. Go to https://console.cloud.google.com and sign in with your Gmail.
2. Create a new project (any name, e.g. "lead-finder").
3. Go to **Billing** and add a card. If it asks for account type, choose
   **Individual**. You don't need a company. Google gives a free monthly
   allowance, so practice runs cost nothing. Tip: set a budget alert of $5.
4. Go to **APIs & Services → Library** and enable:
   - **Geocoding API**
   - **Places API (New)**
5. Go to **APIs & Services → Credentials → Create credentials → API key**.
   Copy the key. Never post it anywhere public.

## 2. Set up n8n (at http://localhost:5678)

1. **Google key:** create a credential of type **Query Auth**.
   Name: `key`, Value: your API key. Select it in **Get Coordinates**,
   **Get Places** and **Get Places1**.
2. **Data table:** go to Overview → **Data tables**, create a table named
   `next_page` with one text column named `token`.
3. **Google Sheet:** create a sheet with these headers in row 1:
   `Name, Address, Phone, Website, Rating, Reviews, Google Maps`.
   In **Append row in sheet**, pick your Google credential and that sheet.
4. Change what to search in **Edit Fields** (query, location, radius in
   meters), then click **Execute workflow**.
