from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import HelpRequest, HelpRequestStatus, Offer, OfferStatus, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is not None:
        user.username = username
        user.first_name = first_name
        await session.commit()
        await session.refresh(user)
        return user

    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_location(
    session: AsyncSession,
    user: User,
    city: str,
    district: str | None,
) -> User:
    user.city = city.strip()
    user.district = district.strip() if district else None
    await session.commit()
    await session.refresh(user)
    return user


async def create_help_request(
    session: AsyncSession,
    user: User,
    category: str,
    title: str,
    description: str,
    city: str | None,
    district: str | None,
    address_hint: str | None,
    needed_at_text: str | None,
    reward_type: str,
    reward_amount: float | None,
    status: HelpRequestStatus,
) -> HelpRequest:
    request = HelpRequest(
        user_id=user.id,
        category=category,
        title=title.strip(),
        description=description.strip(),
        city=city,
        district=district,
        address_hint=address_hint.strip() if address_hint else None,
        needed_at_text=needed_at_text.strip() if needed_at_text else None,
        reward_type=reward_type,
        reward_amount=reward_amount,
        status=status.value,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def list_published_requests(
    session: AsyncSession,
    city: str | None,
    district: str | None,
    limit: int = 10,
) -> list[HelpRequest]:
    query: Select[tuple[HelpRequest]] = (
        select(HelpRequest)
        .join(User, User.id == HelpRequest.user_id)
        .options(selectinload(HelpRequest.owner))
        .where(HelpRequest.status == HelpRequestStatus.PUBLISHED.value)
        .where(User.is_banned.is_(False))
        .order_by(HelpRequest.created_at.desc())
        .limit(limit)
    )
    if city:
        query = query.where(HelpRequest.city == city)
    if district:
        query = query.where(HelpRequest.district == district)
    return list(await session.scalars(query))


async def list_user_requests(session: AsyncSession, user: User, limit: int = 10) -> list[HelpRequest]:
    query = (
        select(HelpRequest)
        .where(HelpRequest.user_id == user.id)
        .order_by(HelpRequest.created_at.desc())
        .limit(limit)
    )
    return list(await session.scalars(query))


async def get_request_by_id(session: AsyncSession, request_id: int) -> HelpRequest | None:
    return await session.scalar(
        select(HelpRequest)
        .options(selectinload(HelpRequest.owner))
        .where(HelpRequest.id == request_id)
    )


async def create_offer(
    session: AsyncSession,
    request: HelpRequest,
    helper: User,
    message: str | None,
) -> Offer:
    existing_offer = await session.scalar(
        select(Offer).where(
            Offer.request_id == request.id,
            Offer.helper_id == helper.id,
            Offer.status.in_([OfferStatus.PENDING.value, OfferStatus.ACCEPTED.value]),
        )
    )
    if existing_offer is not None:
        return existing_offer

    offer = Offer(request_id=request.id, helper_id=helper.id, message=message)
    session.add(offer)
    await session.commit()
    await session.refresh(offer)
    return offer


async def set_request_status(
    session: AsyncSession,
    request: HelpRequest,
    status: HelpRequestStatus,
) -> HelpRequest:
    request.status = status.value
    await session.commit()
    await session.refresh(request)
    return request
