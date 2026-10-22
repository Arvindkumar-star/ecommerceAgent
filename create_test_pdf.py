import os
import fitz

def generate_sample_pdf():
    pdf_path = os.path.join(os.path.dirname(__file__), "sample_company_policy.pdf")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4

    text = """APEX RETAIL INC. — CUSTOMER SUPPORT & RETURN POLICY
Effective Date: January 1, 2026 | Document ID: POL-2026-v2

1. Return & Refund Eligibility
Customers may return any eligible product within thirty (30) days of the confirmed delivery date. To qualify for a refund, returned items must be in new, unworn, and unwashed condition, complete with original tags, accessories, and manufacturer packaging.

Restocking Fees:
- Change-of-mind returns are subject to a 10% restocking fee deducted from the total refund amount.
- Returns due to damaged, defective, or incorrectly shipped merchandise are exempt from restocking fees and will receive a 100% full refund including original shipping costs.

Non-Returnable Items:
- Gift cards and electronic vouchers.
- Personalized, engraved, or customized items.
- Final sale clearance merchandise.
- Perishable goods and intimate apparel.

2. Shipping & Delivery Guidelines
- Standard Shipping: Delivers within 3 to 5 business days across the continental United States. Standard delivery is free for all orders over $50.00; otherwise, a flat rate of $4.99 applies.
- Express Expedited Shipping: Delivers within 1 to 2 business days for a flat rate of $14.99.
- Tracking Numbers: Dispatched via email and SMS within 24 hours of warehouse fulfillment.

3. Warranty & Defective Item Policy
All consumer electronics, smart gadgets, and lifestyle hardware products carry a comprehensive 1-Year Limited Manufacturer Warranty covering hardware defects and technical malfunctions.
For eligible warranty claims, Apex Retail provides immediate replacement or repair within 5 business days of receiving the defective unit.

4. Customer Support Contact & Hours
- Support Hours: Monday through Friday, 9:00 AM to 6:00 PM EST.
- Official Email: support@apexretail.com
- Customer Portal: https://support.apexretail.com
"""

    rect = fitz.Rect(50, 50, 545, 790)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    print(f"Sample PDF created: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")

if __name__ == "__main__":
    generate_sample_pdf()
