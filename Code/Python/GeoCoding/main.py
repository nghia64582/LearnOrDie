from geopy.geocoders import Nominatim
import time

geolocator = Nominatim(user_agent="my_geocoder_app")
location = geolocator.geocode("Số 250 Minh Khai, Hai Bà Trưng, Hà Nội")
address = geolocator.reverse("21.012571, 105.855345")

print("Address:", location.address)
print("Latitude:", location.latitude)
print("Longitude:", location.longitude)
print(address)
