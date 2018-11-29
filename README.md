# Producers
The Producers library is a multiprocessing based framework for creating Producer processes. A Producer is a process which regularly generates output for the main process to act upon.

## Input and Output
A Producer has two queues, an input queue and an output queue. The host process uses the input queue to send configuration data to the Producer. The Producer does some unit of work, and places the output in the output queue. The consumer can then consume that output at its leisure. The key idea, however, is that **Producers run mostly on their own**. This is not a request/response scenario. Producers, once launched, will do some recurring unit of work which produces output. This makes them distinct from something like a worker pool, where the main process is breaking up units of work across workers who all do basically the same thing.

### Output Buffering
Producer may set a maximum buffersize on their output queue. If this is set, when the queue is full, the Producer will simply idle.

# Current Status
Currently, there's just the abstract base class, and one implemented child class for testing purposes. I intend to add a few more concrete implementations.

# Example
The simplest concrete implementation would look something like this:

```python
from producers import Producer
class CountProducer(Producer):
    """
    Simple demo class to show how production works.

    Launches a process which counts. Only buffers the next
    ten items.
    """
    def __init__(self):
        super(CountProducer, self).__init__(10) #buffer size is 10
        self.i = 0

    def handle_message(self, msg):
        """Take the contents of the message, and make the next value that"""
        self.i = msg
        # we also need to flush the output queue
        while not self.outbound.empty():
            self.outbound.get_nowait()

    def production_step(self):
        """Return the current value, increment for the next iteration"""
        res = self.i
        self.i += 1
        return res
```

This producer will produce an infinite sequence of numbers, but will never buffer more than ten at once.

I can use this, thus:

```python
c = CountProducer()
c.start()
n = c.get()
```

Each call to `c.get` will return the next number in the sequence. Since messages can be sent, I may also do something like this:

```python
c.send(50)
n = c.get() #50
n = c.get() #51
```