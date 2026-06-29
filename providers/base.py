from abc import ABC, abstractmethod


class CarProvider(ABC):
    name = "Unknown"

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def search(self, pickup, dropoff, pickup_time, return_time, index):
        raise NotImplementedError
