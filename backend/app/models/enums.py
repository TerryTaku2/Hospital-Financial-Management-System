import enum


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    CASHIER = "cashier"
    AUDITOR = "auditor"
    CLINICIAN = "clinician"
    MEDICAL_SUPERINTENDENT = "medical_superintendent"
    MATRON = "matron"
    ACCOUNTS_CLERK = "accounts_clerk"


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


class RequisitionStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ORDERED = "ordered"
    CANCELLED = "cancelled"


class RequisitionSignatory(str, enum.Enum):
    """The three sign-offs a purchase requisition needs. Values match the
    RoleEnum value of the user who is allowed to give that signature."""

    MEDICAL_SUPERINTENDENT = "medical_superintendent"
    MATRON = "matron"
    ADMIN = "admin"


class CashVoucherStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    DISBURSED = "disbursed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class StockLocation(str, enum.Enum):
    STORE = "store"
    PHARMACY = "pharmacy"


class StockRequisitionStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    CANCELLED = "cancelled"


class JournalSourceType(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    DEPOSIT_APPLICATION = "deposit_application"
    REFUND = "refund"
    PURCHASE_ORDER = "purchase_order"
    SUPPLIER_PAYMENT = "supplier_payment"
    PAYROLL = "payroll"
    PAYROLL_PAYMENT = "payroll_payment"
    MANUAL = "manual"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    PAID = "paid"
    VOID = "void"


class AssetStatus(str, enum.Enum):
    ACTIVE = "active"
    DISPOSED = "disposed"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    VOID = "void"
    DELETE = "delete"
