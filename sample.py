from typing import Callable, NamedTuple


# def auth_idpw(id: str, pw: str):
#     return True


# def auth(
#     auth_strategy: Callable[[], None],
#     **kwargs,
# ) -> bool:
#     auth_strategy(**kwargs)


# auth(auth_idpw, id='asdf', pw='asdf')


class Subsciber(NamedTuple):
    name: str
    func: Callable[[str], None]


class Publisher:
    def __init__(self) -> None:
        self.subscribers: list[Subsciber] = []

    def sub(self, subscriber: Subsciber) -> None:
        self.subscribers.append(subscriber)

    def desub(self, subscriber_name: str) -> None:
        for sub in self.subscribers:
            if sub.name == subscriber_name:
                self.subscribers.remove(sub)

    def pub(self, message: str) -> None:
        for subscriber in self.subscribers:
            subscriber.func(message)


publisher = Publisher()

publisher.sub(Subsciber('sub1', lambda message: print(message)))
publisher.sub(Subsciber('sub2', lambda message: print('sub2:', message)))

publisher.pub('message')

publisher.desub('sub1')

publisher.pub('1')


class ServiceInterface:
    def operation(self) -> None:
        raise NotImplementedError()


class Service(ServiceInterface):
    def operation(self) -> None:
        print('operation')


class ServiceProxy(ServiceInterface):
    def operation(self) -> None:
        print('operation by proxy')


# polymorphism
service1: ServiceInterface = Service()
service2: ServiceInterface = ServiceProxy()
