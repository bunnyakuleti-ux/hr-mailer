"""Run this script to generate sample_hr_contacts.xlsx"""
import pandas as pd

data = [
    {"Name": "Rahul Sharma",    "Email": "rahul@abc.com",       "Company": "ABC Technologies"},
    {"Name": "Priya Nair",      "Email": "priya@xyz.com",        "Company": "XYZ Solutions"},
    {"Name": "Arun Kumar",      "Email": "arun@pqr.com",         "Company": "PQR Systems"},
    {"Name": "Sneha Reddy",     "Email": "sneha@lmn.com",        "Company": "LMN Infosys"},
    {"Name": "Vikram Singh",    "Email": "vikram@techcorp.in",   "Company": "TechCorp"},
    {"Name": "Ananya Das",      "Email": "ananya@startup.io",    "Company": "StartupIO"},
    {"Name": "Rohan Mehta",     "Email": "ROHAN@abc.com",        "Company": "ABC Technologies"},  # dup (different case)
    {"Name": "Invalid Row",     "Email": "not-an-email",         "Company": "N/A"},               # invalid
    {"Name": "Empty Email",     "Email": "",                     "Company": "N/A"},               # invalid
    {"Name": "Deepa Pillai",    "Email": "deepa@hrsolutions.com","Company": "HR Solutions"},
]

df = pd.DataFrame(data)
df.to_excel("sample_hr_contacts.xlsx", index=False)
df.to_csv("sample_hr_contacts.csv", index=False)
print("✓ Created sample_hr_contacts.xlsx and sample_hr_contacts.csv")
print(f"  Rows: {len(df)}")
print(f"  Expected valid: 8, duplicates: 1, invalid: 2 (after duplicate check)")
