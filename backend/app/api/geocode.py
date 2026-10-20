from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.geocode import GeocodeRead
from app.services.geocoding_service import Geocoder, GeocodingError, get_geocoder

router = APIRouter(prefix="/api/geocode", tags=["geocode"])


@router.get("", response_model=GeocodeRead)
def geocode(geocoder: Annotated[Geocoder, Depends(get_geocoder)], address: str = "", city: str = ""):
    """Podgląd lokalizacji adresu (formularze sędziego i obiektu pokazują znalezione miejsce)."""
    if not address.strip() and not city.strip():
        raise HTTPException(422, "Podaj adres lub miasto")
    try:
        found = geocoder.geocode(address, city)
    except GeocodingError as exc:
        raise HTTPException(503, "Usługa map jest chwilowo niedostępna") from exc
    if found is None:
        raise HTTPException(404, "Nie znaleziono adresu")
    return found
