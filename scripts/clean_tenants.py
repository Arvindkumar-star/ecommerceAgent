import sqlite3

conn = sqlite3.connect('data/support_platform.db')
c = conn.cursor()

# Insert Apex Retail Inc.
c.execute("INSERT OR REPLACE INTO companies (id, name, created_at) VALUES ('apex_retail', 'Apex Retail Inc.', datetime('now'))")

# Update documents, chunks, and metrics from api_test_tenant to apex_retail
c.execute("UPDATE documents SET company_id='apex_retail' WHERE company_id='api_test_tenant'")
c.execute("UPDATE chunks SET company_id='apex_retail' WHERE company_id='api_test_tenant'")
c.execute("UPDATE metrics SET company_id='apex_retail' WHERE company_id='api_test_tenant'")

# Remove temporary test companies
c.execute("DELETE FROM companies WHERE id IN ('api_test_tenant', 'tenant_test_alpha', 'tenant_test_beta')")
c.execute("UPDATE companies SET name='Acme Corporation' WHERE id='acme_corp'")

conn.commit()

c.execute("SELECT id, name FROM companies")
print("Updated companies:", c.fetchall())

c.execute("SELECT company_id, filename FROM documents")
print("Updated documents:", c.fetchall())

conn.close()
