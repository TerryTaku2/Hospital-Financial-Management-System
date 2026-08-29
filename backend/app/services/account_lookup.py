from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account
from app.models.billing import Invoice
from app.models.enums import PayerType, PaymentMethod
from app.models.insurance import MedicalAidProvider
from app.services import coa_codes
from app.services.posting_service import PostingError


async def get_account_id_by_code(db: AsyncSession, code: str) -> int:
    account_id = (await db.execute(select(Account.id).where(Account.code == code))).scalar_one_or_none()
    if account_id is None:
        raise PostingError(f"Chart of accounts is missing required account code {code}")
    return account_id


async def get_ar_account_id(db: AsyncSession, invoice: Invoice) -> int:
    if invoice.payer_type == PayerType.MEDICAL_AID:
        if invoice.medical_aid_provider_id is not None:
            provider = await db.get(MedicalAidProvider, invoice.medical_aid_provider_id)
            if provider is not None and provider.ar_account_id is not None:
                return provider.ar_account_id
        return await get_account_id_by_code(db, coa_codes.AR_MEDICAL_AID)
    return await get_account_id_by_code(db, coa_codes.AR_PATIENTS)


async def get_cash_account_id(db: AsyncSession, method: PaymentMethod) -> int:
    code = coa_codes.CASH if method == PaymentMethod.CASH else coa_codes.BANK
    return await get_account_id_by_code(db, code)
