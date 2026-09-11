"""Well-known Chart of Accounts codes the service layer posts against.

These must exist in the `accounts` table (created by app.seed) before any
billing/payment/deposit flow can post a journal entry.
"""

CASH = "1000"
BANK = "1010"
AR_PATIENTS = "1100"
AR_MEDICAL_AID = "1200"
DEPOSITS_HELD = "2100"
AP_SUPPLIERS = "2200"
PAYROLL_PAYABLE = "2300"
PAYROLL_DEDUCTIONS_PAYABLE = "2310"
REVENUE_GENERAL = "4090"
COGS_DRUGS = "5000"
SALARIES_EXPENSE = "5010"
