from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, not_found
from app.models import Match, Venue
from app.schemas.venue import VenueCreate, VenueRead, VenueUpdate

router = APIRouter(prefix="/api/venues", tags=["venues"])


@router.get("", response_model=list[VenueRead])
def list_venues(db: DbSession) -> list[Venue]:
    return list(db.scalars(select(Venue).order_by(Venue.city, Venue.name)))


@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create_venue(data: VenueCreate, db: DbSession) -> Venue:
    venue = Venue(**data.model_dump())
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.put("/{venue_id}", response_model=VenueRead)
def update_venue(venue_id: int, data: VenueUpdate, db: DbSession) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise not_found("Obiekt", venue_id)
    for key, value in data.model_dump().items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venue(venue_id: int, db: DbSession) -> None:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise not_found("Obiekt", venue_id)
    if db.scalar(select(Match.id).where(Match.venue_id == venue_id).limit(1)) is not None:
        raise HTTPException(409, "Na tym obiekcie są zaplanowane mecze — najpierw je przenieś lub usuń")
    db.delete(venue)
    db.commit()
