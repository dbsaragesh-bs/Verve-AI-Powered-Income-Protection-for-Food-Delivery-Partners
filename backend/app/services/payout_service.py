from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payout import Payout
from app.schemas.payout import PayoutCreate, PayoutUpdate


class PayoutService:
    @staticmethod
    async def create_payout(session: AsyncSession, payload: PayoutCreate) -> Payout:
        payout = Payout(**payload.model_dump())
        session.add(payout)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("invalid claim_id or worker_id") from exc
        await session.refresh(payout)
        return payout

    @staticmethod
    async def list_payouts(session: AsyncSession) -> list[Payout]:
        result = await session.execute(
            select(Payout).order_by(Payout.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_payout(session: AsyncSession, payout_id: str) -> Payout | None:
        return await session.get(Payout, payout_id)

    @staticmethod
    async def update_payout(
        session: AsyncSession, payout: Payout, payload: PayoutUpdate
    ) -> Payout:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(payout, key, value)
        await session.commit()
        await session.refresh(payout)
        return payout
