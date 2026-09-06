"""Demo accounts and realistic sample data for showing off the system.

Builds on top of `app.seed` (currencies, main branch, Chart of Accounts,
admin user, medical aid providers, charge items) and adds:

- One user per role (cashier, accountant, auditor, clinician)
- A second branch, so branch-filtered reports have something to filter
- Seven patients covering every invoice/payment/deposit/claim state:
  draft, fully paid, partially paid via deposit (with a refund), medical-aid
  billed and paid, unpaid and aged for AR Aging, voided, and a second-branch
  invoice
- The encounters, invoices, payments, deposits, refunds and a claim that
  produce those states, all posted through the real service layer so the
  books stay balanced

Idempotent: safe to run more than once — it checks for the "cashier1" user
and does nothing if the demo data already exists.

Usage: python -m app.seed_demo
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.branch import Branch
from app.models.encounter import Encounter
from app.models.enums import EncounterStatus, EncounterType, PayerType, PaymentMethod, RoleEnum
from app.models.insurance import MedicalAidProvider, PatientCover
from app.models.patient import Patient
from app.models.user import User
from app.schemas.billing import DepositApply, DepositCreate, InvoiceCreate, InvoiceLineIn, PaymentCreate, RefundCreate
from app.schemas.insurance import ClaimCreate, ClaimDecision
from app.security import hash_password
from app.seed import seed
from app.services.billing_service import create_invoice, finalize_invoice, void_invoice
from app.services.claims_service import create_claim, decide_claim, submit_claim
from app.services.deposit_service import apply_deposit, refund_deposit, take_deposit
from app.services.payment_service import record_payment

DEMO_PASSWORD = "Demo1234!"


async def _get_charge_item_id(db, code: str) -> int:
    from app.models.billing import ChargeItem

    return (await db.execute(select(ChargeItem.id).where(ChargeItem.code == code))).scalar_one()


async def seed_demo() -> None:
    await seed()

    async with AsyncSessionLocal() as db:
        if (await db.execute(select(User).where(User.username == "cashier1"))).scalars().first() is not None:
            print("Demo data already present — nothing to do.")
            return

        main_branch = (await db.execute(select(Branch).where(Branch.code == "MAIN"))).scalars().first()

        north_branch = (await db.execute(select(Branch).where(Branch.code == "NORTH"))).scalars().first()
        if north_branch is None:
            north_branch = Branch(code="NORTH", name="North Clinic", base_currency_code="USD")
            db.add(north_branch)
            await db.flush()

        psmas = (await db.execute(select(MedicalAidProvider).where(MedicalAidProvider.code == "PSMAS"))).scalars().first()

        role_users = {
            "cashier1": ("Chipo Mutasa", RoleEnum.CASHIER),
            "accountant1": ("Tendai Chirwa", RoleEnum.ACCOUNTANT),
            "auditor1": ("Blessing Ncube", RoleEnum.AUDITOR),
            "clinician1": ("Dr. Simba Mangwana", RoleEnum.CLINICIAN),
        }
        users: dict[str, User] = {}
        for username, (full_name, role) in role_users.items():
            user = User(
                branch_id=main_branch.id,
                username=username,
                email=f"{username}@example.com",
                full_name=full_name,
                hashed_password=hash_password(DEMO_PASSWORD),
                role=role,
            )
            db.add(user)
            users[username] = user
        await db.flush()

        cashier = users["cashier1"]
        accountant = users["accountant1"]

        patient_defs = [
            ("Grace", "Chikwanha", date(1988, 3, 14), "F", "63-112233A45", "0771234001", main_branch),
            ("Tapiwa", "Marufu", date(1979, 11, 2), "M", "63-223344B56", "0771234002", main_branch),
            ("Rudo", "Sibanda", date(1995, 6, 21), "F", "63-334455C67", "0771234003", main_branch),
            ("Kudzai", "Moyo", date(2001, 1, 9), "M", "63-445566D78", "0771234004", main_branch),
            ("Farai", "Ncube", date(1966, 8, 30), "M", "63-556677E89", "0771234005", main_branch),
            ("Chiedza", "Gumbo", date(1990, 4, 17), "F", "63-667788F90", "0771234006", main_branch),
            ("Blessing", "Marimo", date(1983, 9, 5), "M", "08-778899G01", "0771234007", north_branch),
        ]
        patients: dict[str, Patient] = {}
        for first, last, dob, sex, national_id, phone, branch in patient_defs:
            patient = Patient(
                branch_id=branch.id,
                first_name=first,
                last_name=last,
                date_of_birth=dob,
                sex=sex,
                national_id=national_id,
                phone=phone,
            )
            db.add(patient)
            patients[last] = patient
        await db.flush()

        db.add(
            PatientCover(
                patient_id=patients["Sibanda"].id,
                medical_aid_provider_id=psmas.id,
                membership_number="PSM-000123",
                scheme_name="Corporate Executive Plan",
            )
        )

        db.add(
            Encounter(
                branch_id=main_branch.id,
                patient_id=patients["Chikwanha"].id,
                type=EncounterType.OPD,
                status=EncounterStatus.CLOSED,
                attending_doctor_name="Dr. Simba Mangwana",
                admission_date=datetime.now(timezone.utc) - timedelta(hours=3),
                discharge_date=datetime.now(timezone.utc) - timedelta(hours=2),
            )
        )
        db.add(
            Encounter(
                branch_id=main_branch.id,
                patient_id=patients["Sibanda"].id,
                type=EncounterType.IPD,
                status=EncounterStatus.OPEN,
                attending_doctor_name="Dr. Simba Mangwana",
                admission_date=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        await db.flush()
        await db.commit()

        consult_gen = await _get_charge_item_id(db, "CONSULT-GEN")
        consult_spec = await _get_charge_item_id(db, "CONSULT-SPEC")
        dressing = await _get_charge_item_id(db, "PROC-DRESSING")
        paracetamol = await _get_charge_item_id(db, "PHARM-PARACETAMOL")

        # 1. Grace Chikwanha — self-pay, finalized, paid in full (cash)
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Chikwanha"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(charge_item_id=consult_gen), InvoiceLineIn(charge_item_id=paracetamol, quantity=Decimal("2"))],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        await record_payment(
            db,
            PaymentCreate(
                branch_id=main_branch.id,
                invoice_id=invoice.id,
                method=PaymentMethod.CASH,
                currency_code="USD",
                amount=invoice.total,
            ),
            cashier,
            idempotency_key=str(uuid.uuid4()),
        )
        await db.commit()

        # 2. Tapiwa Marufu — self-pay, deposit partially applied + remainder refunded, aged 45 days
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Marufu"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(charge_item_id=consult_spec)],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        deposit, _ = await take_deposit(
            db,
            DepositCreate(branch_id=main_branch.id, patient_id=patients["Marufu"].id, currency_code="USD", amount=Decimal("30")),
            cashier,
            idempotency_key=str(uuid.uuid4()),
        )
        await apply_deposit(db, deposit, DepositApply(invoice_id=invoice.id, amount=Decimal("20")), cashier)
        await refund_deposit(
            db,
            deposit,
            RefundCreate(branch_id=main_branch.id, currency_code="USD", amount=Decimal("10"), reason="Patient overpaid deposit — refunding balance"),
            cashier,
            idempotency_key=str(uuid.uuid4()),
        )
        invoice.created_at = datetime.now(timezone.utc) - timedelta(days=45)
        await db.commit()

        # 3. Rudo Sibanda — medical aid billed, claim submitted and approved, paid by PSMAS
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Sibanda"].id,
                currency_code="USD",
                payer_type=PayerType.MEDICAL_AID,
                medical_aid_provider_id=psmas.id,
                lines=[InvoiceLineIn(charge_item_id=consult_spec), InvoiceLineIn(charge_item_id=dressing)],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        claim = await create_claim(
            db,
            ClaimCreate(invoice_id=invoice.id, medical_aid_provider_id=psmas.id, invoice_line_ids=[line.id for line in invoice.lines]),
            cashier,
        )
        claim = await submit_claim(db, claim, cashier)
        await decide_claim(db, claim, ClaimDecision(approve=True), accountant)
        await db.commit()

        # 4. Kudzai Moyo — left as a draft invoice (never finalized)
        await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Moyo"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(charge_item_id=consult_gen)],
            ),
            cashier,
        )
        await db.commit()

        # 5. Farai Ncube — finalized, unpaid, aged 100 days (shows in the 90+ AR bucket)
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Ncube"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(charge_item_id=consult_gen), InvoiceLineIn(charge_item_id=dressing, quantity=Decimal("2"))],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        invoice.created_at = datetime.now(timezone.utc) - timedelta(days=100)
        await db.commit()

        # 6. Chiedza Gumbo — finalized then voided (billed in error)
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=main_branch.id,
                patient_id=patients["Gumbo"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(charge_item_id=consult_gen)],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        await void_invoice(db, invoice, accountant, "Billed in error — duplicate invoice")
        await db.commit()

        # 7. Blessing Marimo — North Clinic branch, finalized, partially paid
        invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=north_branch.id,
                patient_id=patients["Marimo"].id,
                currency_code="USD",
                lines=[InvoiceLineIn(description="General Consultation", unit_price=Decimal("20"))],
            ),
            cashier,
        )
        invoice = await finalize_invoice(db, invoice, accountant)
        await record_payment(
            db,
            PaymentCreate(branch_id=north_branch.id, invoice_id=invoice.id, method=PaymentMethod.CASH, currency_code="USD", amount=Decimal("10")),
            cashier,
            idempotency_key=str(uuid.uuid4()),
        )
        await db.commit()

    print("Demo data seeded.")
    print("Log in as any of:")
    print("  admin / ChangeMe123!         (Administrator)")
    for username, (full_name, role) in role_users.items():
        print(f"  {username} / {DEMO_PASSWORD}    ({role.value})")


if __name__ == "__main__":
    asyncio.run(seed_demo())
