from abc import ABC, abstractmethod


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
    ):
        return {
            "provider": self.name,
            "pickup": str(pickup),
            "dropoff": str(dropoff),
            "pickup_time": pickup_time,
            "return_time": return_time,
            "days_elapsed": days_elapsed,
            "success": success,
            "vehicle": vehicle,
            "_vehicle_image": vehicle_image,
            "_provider_logo": self.logo_url,
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
