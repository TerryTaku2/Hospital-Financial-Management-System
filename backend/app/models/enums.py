import enum


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    CASHIER = "cashier"
    AUDITOR = "auditor"
    CLINICIAN = "clinician"


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class EncounterType(str, enum.Enum):
    OPD = "opd"
    IPD = "ipd"


class EncounterStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class DepositStatus(str, enum.Enum):
    HELD = "held"
    APPLIED = "applied"
    REFUNDED = "refunded"
    PARTIALLY_APPLIED = "partially_applied"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    EFT = "eft"
    MEDICAL_AID = "medical_aid"


class PayerType(str, enum.Enum):
    PATIENT = "patient"
    MEDICAL_AID = "medical_aid"


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    RECEIVED = "received"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class JournalSourceType(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    DEPOSIT_APPLICATION = "deposit_application"
    REFUND = "refund"
    PURCHASE_ORDER = "purchase_order"
    SUPPLIER_PAYMENT = "supplier_payment"
    MANUAL = "manual"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    VOID = "void"
    DELETE = "delete"
