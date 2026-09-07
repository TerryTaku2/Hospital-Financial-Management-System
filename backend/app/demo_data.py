"""Self-resetting demo sandbox.

`ensure_demo_data()` wipes every branch, patient, invoice, payment, claim,
journal entry and user in the database and regenerates a fresh, believable
month of activity across three branches. It's called both at application
startup and on every `/api/auth/demo-login` request, so a demo visitor —
who has full admin power in the sandbox — can never leave it messy for the
next person. There is no tenant separation in this codebase (unlike a
multi-tenant app where a "demo company" can be isolated from real
customer data), so this wipes the *entire* database: this app must only
ever be run as a demo/pitch instance, never with real patient data.

Deliberately small and fast (regenerates in a couple of seconds) since it
runs on every demo login. For a much larger, slower one-off dataset for a
scripted walkthrough, see `app.seed_investor_demo` — but note that script's
data will be wiped the next time this app restarts or anyone clicks
"Login to Demo Account".
"""

import random
import string
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.audit_log import AuditLog
from app.models.billing import ChargeItem, Deposit, Invoice, InvoiceLine, Payment, Refund
from app.models.branch import Branch
from app.models.currency import Currency, ExchangeRate
from app.models.encounter import Encounter
from app.models.enums import JournalSourceType, PayerType, PaymentMethod, RoleEnum
from app.models.insurance import Claim, ClaimLine, MedicalAidProvider, PatientCover
from app.models.patient import Patient
from app.models.user import User
from app.schemas.billing import DepositApply, DepositCreate, InvoiceCreate, InvoiceLineIn, PaymentCreate, RefundCreate
from app.schemas.insurance import ClaimCreate, ClaimDecision
from app.security import hash_password
from app.seed import seed_core
from app.services.billing_service import create_invoice, finalize_invoice, void_invoice
from app.services.claims_service import create_claim, decide_claim, submit_claim
from app.services.deposit_service import apply_deposit, refund_deposit, take_deposit
from app.services.payment_service import record_payment

DEMO_PASSWORD = "Demo1234!"
RNG_SEED = 42
WINDOW_DAYS = 27

MALE_FIRST_NAMES = [
    "Tapiwa", "Farai", "Kudzai", "Blessing", "Tinashe", "Simbarashe", "Tonderai", "Takudzwa",
    "Munyaradzi", "Tatenda", "Brian", "Emmanuel", "Prince", "Innocent", "Elvis", "Wellington",
]
FEMALE_FIRST_NAMES = [
    "Grace", "Rudo", "Chiedza", "Chipo", "Fadzai", "Rutendo", "Vimbai", "Sekai",
    "Memory", "Precious", "Charity", "Faith", "Patience", "Yeukai", "Anesu", "Rufaro",
]
SURNAMES = [
    "Chikwanha", "Marufu", "Sibanda", "Moyo", "Ncube", "Gumbo", "Marimo", "Mutasa",
    "Chirwa", "Mangwana", "Nyathi", "Dube", "Chatiza", "Muzenda", "Gwati", "Zvobgo",
]

BRANCH_DEFS = [
    ("MAIN", "Main Hospital", None, 24),
    ("NORTH", "North Clinic", "14 Samora Machel Ave, Harare", 16),
    ("WEST", "West Medical Centre", "82 Fifth Street, Bulawayo", 10),
]

CHARGE_TEMPLATES = [
    ("CONSULT-GEN", "General Consultation", "Consultation", Decimal("25.00"), "4000"),
    ("CONSULT-SPEC", "Specialist Consultation", "Consultation", Decimal("55.00"), "4000"),
    ("CONSULT-FOLLOWUP", "Follow-up Consultation", "Consultation", Decimal("15.00"), "4000"),
    ("PHARM-PARACETAMOL", "Paracetamol 500mg (strip)", "Pharmacy", Decimal("2.00"), "4010"),
    ("PHARM-AMOXICILLIN", "Amoxicillin 500mg (course)", "Pharmacy", Decimal("8.00"), "4010"),
    ("PROC-DRESSING", "Wound Dressing", "Procedure", Decimal("15.00"), "4020"),
    ("PROC-SUTURE", "Suturing", "Procedure", Decimal("35.00"), "4020"),
    ("LAB-FBC", "Full Blood Count", "Laboratory", Decimal("18.00"), "4020"),
    ("IMG-XRAY", "X-Ray (single view)", "Imaging", Decimal("45.00"), "4020"),
    ("WARD-GENERAL", "General Ward - per day", "Ward/Bed Fees", Decimal("40.00"), "4030"),
]

VOID_REASONS = ["Billed in error — duplicate invoice", "Patient declined services after billing"]
MEMBERSHIP_PLANS = ["Standard Plan", "Executive Plan", "Family Plan"]


async def _reset_all(db: AsyncSession) -> None:
    """Deletes every row of business data, in FK-safe (children-first) order."""
    for model in [
        ClaimLine, Claim,
        InvoiceLine, Refund, Payment, Deposit, Invoice,
        Encounter, PatientCover, Patient,
        AuditLog, ChargeItem,
        JournalLine, JournalEntry,
        MedicalAidProvider,
        User, Branch,
        Account, ExchangeRate, Currency,
    ]:
        await db.execute(delete(model))
    await db.commit()


def _random_patient(rng: random.Random, branch_id: int) -> Patient:
    sex = rng.choice(["M", "F"])
    first = rng.choice(MALE_FIRST_NAMES if sex == "M" else FEMALE_FIRST_NAMES)
    last = rng.choice(SURNAMES)
    dob = date(rng.randint(1948, 2019), rng.randint(1, 12), rng.randint(1, 28))
    national_id = (
        f"{rng.choice(['63', '08', '04', '75'])}-{rng.randint(100000, 999999)}"
        f"{rng.choice(string.ascii_uppercase)}{rng.randint(10, 99)}"
    )
    phone = f"0{rng.choice([71, 73, 77, 78])}{rng.randint(1000000, 9999999)}"
    return Patient(branch_id=branch_id, first_name=first, last_name=last, date_of_birth=dob, sex=sex, national_id=national_id, phone=phone)


def _clamp(dt: datetime) -> datetime:
    return min(dt, datetime.now(timezone.utc))


def _txn_dt(rng: random.Random, days_ago: int) -> datetime:
    target_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date()
    return datetime(target_date.year, target_date.month, target_date.day, rng.randint(7, 17), rng.randint(0, 59), tzinfo=timezone.utc)


def _pick_lines(rng: random.Random, charge_items: list[ChargeItem]) -> list[InvoiceLineIn]:
    n = rng.choices([1, 2, 3], weights=[50, 35, 15])[0]
    chosen = rng.sample(charge_items, k=min(n, len(charge_items)))
    lines = []
    for item in chosen:
        qty = Decimal(rng.choice([1, 1, 1, 2])) if item.category == "Pharmacy" else Decimal("1")
        lines.append(InvoiceLineIn(charge_item_id=item.id, quantity=qty))
    return lines


async def _backdate_journal(db: AsyncSession, source_type: JournalSourceType, source_id: int, dt: datetime) -> None:
    await db.execute(
        update(JournalEntry)
        .where(JournalEntry.source_type == source_type, JournalEntry.source_id == source_id)
        .values(entry_date=dt.date(), created_at=dt, updated_at=dt)
    )


async def _run_episode(
    db: AsyncSession,
    rng: random.Random,
    *,
    branch: Branch,
    patient: Patient,
    cashier: User,
    accountant: User,
    charge_items: list[ChargeItem],
    providers: list[MedicalAidProvider],
    txn_dt: datetime,
) -> None:
    is_medical_aid = rng.random() < 0.25
    payer_type = PayerType.MEDICAL_AID if is_medical_aid else PayerType.PATIENT
    provider = rng.choice(providers) if is_medical_aid else None

    invoice = await create_invoice(
        db,
        InvoiceCreate(
            branch_id=branch.id,
            patient_id=patient.id,
            currency_code="USD",
            payer_type=payer_type,
            medical_aid_provider_id=provider.id if provider else None,
            lines=_pick_lines(rng, charge_items),
        ),
        cashier,
    )
    invoice.created_at = txn_dt
    invoice.updated_at = txn_dt

    if rng.random() < 0.08:
        return  # left as a draft invoice

    invoice = await finalize_invoice(db, invoice, accountant)
    await _backdate_journal(db, JournalSourceType.INVOICE, invoice.id, txn_dt)

    if is_medical_aid:
        if rng.random() < 0.90:
            claim = await create_claim(
                db,
                ClaimCreate(invoice_id=invoice.id, medical_aid_provider_id=provider.id, invoice_line_ids=[line.id for line in invoice.lines]),
                cashier,
            )
            claim = await submit_claim(db, claim, cashier)
            decide_dt = _clamp(txn_dt + timedelta(days=rng.randint(1, 5)))
            if rng.random() < 0.85:
                fraction = Decimal("1") if rng.random() < 0.8 else Decimal(str(round(rng.uniform(0.5, 0.9), 2)))
                approved_amount = (claim.submitted_amount * fraction).quantize(Decimal("0.01"))
                claim = await decide_claim(db, claim, ClaimDecision(approve=True, approved_amount=approved_amount), accountant)
                claim_payment = (
                    await db.execute(select(Payment).where(Payment.idempotency_key == f"claim-payment-{claim.id}"))
                ).scalars().first()
                if claim_payment is not None:
                    claim_payment.created_at = decide_dt
                    claim_payment.updated_at = decide_dt
                    await _backdate_journal(db, JournalSourceType.PAYMENT, claim_payment.id, decide_dt)
            else:
                claim = await decide_claim(db, claim, ClaimDecision(approve=False, rejection_reason="Documentation incomplete"), accountant)
            claim.submitted_at = _clamp(txn_dt + timedelta(hours=6))
            claim.decided_at = decide_dt
            claim.created_at = txn_dt
            claim.updated_at = decide_dt
        return

    method = rng.choices([PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.EFT], weights=[50, 30, 20])[0]
    r = rng.random()
    if r < 0.55:
        payment, _ = await record_payment(
            db,
            PaymentCreate(branch_id=branch.id, invoice_id=invoice.id, method=method, currency_code="USD", amount=invoice.total),
            cashier,
            idempotency_key=f"demo-pay-{invoice.id}",
        )
        pay_dt = _clamp(txn_dt + timedelta(hours=rng.randint(0, 48)))
        payment.created_at = pay_dt
        payment.updated_at = pay_dt
        await _backdate_journal(db, JournalSourceType.PAYMENT, payment.id, pay_dt)
    elif r < 0.72:
        partial = (invoice.total * Decimal(str(round(rng.uniform(0.2, 0.7), 2)))).quantize(Decimal("0.01"))
        if partial > 0:
            payment, _ = await record_payment(
                db,
                PaymentCreate(branch_id=branch.id, invoice_id=invoice.id, method=method, currency_code="USD", amount=partial),
                cashier,
                idempotency_key=f"demo-pay-{invoice.id}",
            )
            pay_dt = _clamp(txn_dt + timedelta(hours=rng.randint(0, 48)))
            payment.created_at = pay_dt
            payment.updated_at = pay_dt
            await _backdate_journal(db, JournalSourceType.PAYMENT, payment.id, pay_dt)
    elif r < 0.90:
        pass  # left unpaid
    elif r < 0.96:
        deposit_amount = (invoice.total * Decimal(str(round(rng.uniform(0.5, 0.9), 2)))).quantize(Decimal("0.01"))
        if deposit_amount > 0:
            deposit, _ = await take_deposit(
                db,
                DepositCreate(branch_id=branch.id, patient_id=patient.id, currency_code="USD", amount=deposit_amount),
                cashier,
                idempotency_key=f"demo-dep-{invoice.id}",
            )
            deposit.created_at = txn_dt
            deposit.updated_at = txn_dt
            await _backdate_journal(db, JournalSourceType.DEPOSIT, deposit.id, txn_dt)

            apply_fraction = Decimal(str(round(rng.uniform(0.6, 1.0), 2)))
            apply_amount = min((deposit_amount * apply_fraction).quantize(Decimal("0.01")), invoice.total)
            if apply_amount > 0:
                apply_dt = _clamp(txn_dt + timedelta(hours=rng.randint(0, 24)))
                await apply_deposit(db, deposit, DepositApply(invoice_id=invoice.id, amount=apply_amount), cashier)
                await _backdate_journal(db, JournalSourceType.DEPOSIT_APPLICATION, deposit.id, apply_dt)

            leftover = deposit_amount - apply_amount
            if leftover > 0 and rng.random() < 0.4:
                refund, _ = await refund_deposit(
                    db,
                    deposit,
                    RefundCreate(branch_id=branch.id, currency_code="USD", amount=leftover, reason="Patient overpaid deposit — refunding balance"),
                    cashier,
                    idempotency_key=f"demo-refund-{invoice.id}",
                )
                refund_dt = _clamp(txn_dt + timedelta(hours=rng.randint(24, 72)))
                refund.created_at = refund_dt
                refund.updated_at = refund_dt
                await _backdate_journal(db, JournalSourceType.REFUND, refund.id, refund_dt)
    else:
        void_dt = _clamp(txn_dt + timedelta(hours=rng.randint(0, 24)))
        await void_invoice(db, invoice, accountant, rng.choice(VOID_REASONS))
        await _backdate_journal(db, JournalSourceType.INVOICE, invoice.id, void_dt)


async def _ensure_branch(db: AsyncSession, code: str, name: str, address: str | None) -> Branch:
    # seed_core() already creates "MAIN" as part of the base Chart of Accounts setup.
    branch = (await db.execute(select(Branch).where(Branch.code == code))).scalars().first()
    if branch is None:
        branch = Branch(code=code, name=name, address=address, base_currency_code="USD", is_main=(code == "MAIN"))
        db.add(branch)
        await db.flush()
    return branch


async def _ensure_user(db: AsyncSession, *, branch_id: int, username: str, full_name: str, role: RoleEnum) -> User:
    user = User(
        branch_id=branch_id,
        username=username,
        email=f"{username}@example.com",
        full_name=full_name,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def _ensure_charge_items(db: AsyncSession, branch: Branch, account_ids: dict[str, int]) -> list[ChargeItem]:
    items = []
    for suffix, name, category, price, revenue_code in CHARGE_TEMPLATES:
        item = ChargeItem(
            branch_id=branch.id,
            code=f"{suffix}-{branch.code}",
            name=name,
            category=category,
            default_price=price,
            currency_code="USD",
            revenue_account_id=account_ids[revenue_code],
        )
        db.add(item)
        items.append(item)
    await db.flush()
    return items


async def ensure_demo_data(db: AsyncSession) -> User:
    """Wipes the database and regenerates a fresh demo dataset. Returns the
    admin user to log in as."""
    await _reset_all(db)
    await seed_core(db)

    rng = random.Random(RNG_SEED)

    account_rows = (await db.execute(select(Account.code, Account.id).where(Account.code.in_(["4000", "4010", "4020", "4030"])))).all()
    account_ids = {code: acc_id for code, acc_id in account_rows}
    providers = list((await db.execute(select(MedicalAidProvider))).scalars().all())

    for code, name, address, patient_count in BRANCH_DEFS:
        branch = await _ensure_branch(db, code, name, address)
        slug = code.lower()
        cashier = await _ensure_user(db, branch_id=branch.id, username=f"cashier.{slug}", full_name=f"Cashier — {name}", role=RoleEnum.CASHIER)
        accountant = await _ensure_user(db, branch_id=branch.id, username=f"accountant.{slug}", full_name=f"Accountant — {name}", role=RoleEnum.ACCOUNTANT)
        charge_items = await _ensure_charge_items(db, branch, account_ids)

        for i in range(patient_count):
            patient = _random_patient(rng, branch.id)
            db.add(patient)
            await db.flush()

            num_episodes = rng.choices([1, 2], weights=[70, 30])[0]
            days_ago_list = sorted((rng.randint(0, WINDOW_DAYS) for _ in range(num_episodes)), reverse=True)
            txn_dts = [_txn_dt(rng, d) for d in days_ago_list]

            patient.created_at = txn_dts[0] - timedelta(hours=rng.randint(0, 48))
            patient.updated_at = patient.created_at

            if providers and rng.random() < 0.25:
                provider = rng.choice(providers)
                db.add(
                    PatientCover(
                        patient_id=patient.id,
                        medical_aid_provider_id=provider.id,
                        membership_number=f"{provider.code}-{rng.randint(100000, 999999)}",
                        scheme_name=rng.choice(MEMBERSHIP_PLANS),
                    )
                )

            for txn_dt in txn_dts:
                await _run_episode(
                    db, rng,
                    branch=branch, patient=patient, cashier=cashier, accountant=accountant,
                    charge_items=charge_items, providers=providers, txn_dt=txn_dt,
                )

        # One deliberately aged, unpaid invoice per branch so AR Aging has a
        # 90+ bucket to show off, regardless of how the random draws above land.
        showcase_patient = _random_patient(rng, branch.id)
        db.add(showcase_patient)
        await db.flush()
        showcase_dt = datetime.now(timezone.utc) - timedelta(days=95)
        showcase_patient.created_at = showcase_dt
        showcase_patient.updated_at = showcase_dt
        showcase_invoice = await create_invoice(
            db,
            InvoiceCreate(
                branch_id=branch.id,
                patient_id=showcase_patient.id,
                currency_code="USD",
                lines=_pick_lines(rng, charge_items),
            ),
            cashier,
        )
        showcase_invoice = await finalize_invoice(db, showcase_invoice, accountant)
        showcase_invoice.created_at = showcase_dt
        showcase_invoice.updated_at = showcase_dt
        await _backdate_journal(db, JournalSourceType.INVOICE, showcase_invoice.id, showcase_dt)

        await db.commit()

    admin = (await db.execute(select(User).where(User.username == "admin"))).scalars().first()
    return admin
