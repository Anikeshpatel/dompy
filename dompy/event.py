
class Event:
    """   Initialization of default Event Object.   """
    callbacks: dict = {}

    # Method For Register An Event And Its Appropriate Callbacks
    @staticmethod
    def on(event: str, callback):
        if Event.callbacks.get(event) is not None:
            Event.callbacks.get(event).add(callback)
        else:
            Event.callbacks.update({
                event: {callback}
            })

    # Method for unregistered or stop listening for event
    @staticmethod
    def off(event: str):
        if Event.callbacks.get(event) is not None:
            Event.callbacks.pop(event)

    # Method For Executing And Passing Data To The Callbacked That Is Associated To An Certain Event
    @staticmethod
    def emmit(event: str, data=None):
        callbacks = Event.callbacks.get(event)
        if callbacks is not None:
            for callback in callbacks:
                if data is not None:
                    callback(data)
                else:
                    callback()
