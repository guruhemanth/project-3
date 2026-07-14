"""Subscription CRUD + dashboard/calendar feed."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BillingCycle, SubSource, SubStatus, Subscription, User
from ..schemas import (
    CalendarItem,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionUpdate,
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

_VALID = {
    "billing_cycle": [e.value for e in BillingCycle],
    "status": [e.value for e in SubStatus],
    "source": [e.value for e in SubSource],
}
_SORTABLE = {"merchant_name", "amount", "status", "next_renewal_date", "created_at"}


def _owner(sub: Subscription, user: User) -> Subscription:
    if sub.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return sub


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_sub(payload: SubscriptionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.billing_cycle not in _VALID["billing_cycle"]:
        raise HTTPException(status_code=422, detail="Invalid billing_cycle")
    if payload.status not in _VALID["status"]:
        raise HTTPException(status_code=422, detail="Invalid status")
    if payload.source not in _VALID["source"]:
        raise HTTPException(status_code=422, detail="Invalid source")
    sub = Subscription(user_id=user.id, **payload.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("", response_model=list[SubscriptionOut])
def list_subs(
    status_filter: str | None = Query(None, alias="status"),
    billing_cycle: str | None = Query(None),
    sort: str = Query("next_renewal_date"),
    order: str = Query("asc"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Subscription).filter(Subscription.user_id == user.id)
    if status_filter:
        if status_filter not in _VALID["status"]:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        q = q.filter(Subscription.status == status_filter)
    if billing_cycle:
        if billing_cycle not in _VALID["billing_cycle"]:
            raise HTTPException(status_code=422, detail="Invalid billing_cycle filter")
        q = q.filter(Subscription.billing_cycle == billing_cycle)
    if sort not in _SORTABLE:
        sort = "next_renewal_date"
    column = getattr(Subscription, sort)
    q = q.order_by(column.asc() if order == "asc" else column.desc())
    return q.all()


@router.get("/calendar", response_model=list[CalendarItem])
def calendar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    horizon = today + timedelta(days=90)
    items: list[CalendarItem] = []
    subs = db.query(Subscription).filter(Subscription.user_id == user.id).all()
    for s in subs:
        if s.trial_end_date and today <= s.trial_end_date <= horizon:
            items.append(CalendarItem(subscription_id=s.id, merchant_name=s.merchant_name,
                                      kind="trial_end", date=s.trial_end_date))
        if s.next_renewal_date and today <= s.next_renewal_date <= horizon:
            items.append(CalendarItem(subscription_id=s.id, merchant_name=s.merchant_name,
                                      kind="renewal", date=s.next_renewal_date))
    items.sort(key=lambda i: i.date)
    return items


@router.get("/{sub_id}", response_model=SubscriptionOut)
def get_sub(sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    return _owner(sub, user)


@router.put("/{sub_id}", response_model=SubscriptionOut)
def update_sub(sub_id: int, payload: SubscriptionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    _owner(sub, user)
    data = payload.model_dump(exclude_unset=True)
    if "billing_cycle" in data and data["billing_cycle"] not in _VALID["billing_cycle"]:
        raise HTTPException(status_code=422, detail="Invalid billing_cycle")
    if "status" in data and data["status"] not in _VALID["status"]:
        raise HTTPException(status_code=422, detail="Invalid status")
    for k, v in data.items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub(sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    _owner(sub, user)
    db.delete(sub)
    db.commit()
