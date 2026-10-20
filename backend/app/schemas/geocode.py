from pydantic import BaseModel


class GeocodeRead(BaseModel):
    latitude: float
    longitude: float
    city: str
    district: str
    formatted_address: str
