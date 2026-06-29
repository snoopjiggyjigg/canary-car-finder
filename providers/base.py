from abc import ABC, abstractmethod


TYPE_KEYWORDS = {
    "Mini": ["mini", "fiat 500", "picanto", "up"],
    "Economy": ["economy", "polo", "ibiza", "yaris", "clio", "corsa"],
    "Compact": ["compact", "focus", "leon", "golf", "astra", "megane"],
    "Family": ["family", "estate", "tourer", "berlingo", "rifter"],
    "SUV": ["suv", "crossover", "captur", "duster", "kamiq", "t-roc"],
    "Van": ["van", "minibus", "transporter", "9 seats", "9 seater", "7 seats", "7 seater"],
}


class CarProvider(ABC):
    name = "Unknown"
    logo_url = None

    def result(
        self,
        pickup,
        dropoff,
        pickup_time,
        return_time,
        days_elapsed,
        success,
        vehicle,
        vehicle_image,
        daily,
        price,
        vehicles_found,
        url,
        status,
        requested_pickup_time=None,
        requested_return_time=None,
    ):
        requested_pickup_time = requested_pickup_time or pickup_time
        requested_return_time = requested_return_time or return_time
        return {
            "provider": self.name,
            "pickup": str(pickup),
            "dropoff": str(dropoff),
            "requested_pickup_time": requested_pickup_time,
            "requested_return_time": requested_return_time,
            "actual_pickup_time": pickup_time,
            "actual_return_time": return_time,
            "pickup_time": pickup_time,
            "return_time": return_time,
            "days_elapsed": days_elapsed,
            "success": success,
            "vehicle": vehicle,
            "_vehicle_image": vehicle_image,
            "_provider_logo": self.logo_url,
            "_seats": _infer_seats(vehicle),
            "_transmission": _infer_transmission(vehicle),
            "_vehicle_type": _infer_vehicle_type(vehicle),
            "site_daily_rate": daily,
            "price": price,
            "effective_daily": round(price / days_elapsed, 2) if price else None,
            "site_rental_days": round(price / daily, 2) if price and daily else None,
            "vehicles_found": vehicles_found,
            "url": url,
            "status": status,
        }

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def search(self, pickup, dropoff, pickup_time, return_time, index):
        raise NotImplementedError

    def adjust_times(self, pickup_time, return_time):
        return pickup_time, return_time


def _infer_seats(vehicle):
    text = str(vehicle or "").lower()
    for seats in (9, 7, 5, 4, 2):
        if f"{seats} seats" in text or f"{seats} seater" in text or f"{seats}p" in text:
            return seats
    return None


def _infer_transmission(vehicle):
    text = str(vehicle or "").lower()
    if "automatic" in text or "auto" in text:
        return "Automatic"
    if "manual" in text:
        return "Manual"
    return None


def _infer_vehicle_type(vehicle):
    text = str(vehicle or "").lower()
    for vehicle_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return vehicle_type
    return None
