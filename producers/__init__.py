"""
Basic workflow for a queue-based producer.

This launches an external process which does the production work. The results are placed
in a queue. The host application can then access the queue to get results.


"""

from abc import abstractmethod,ABCMeta
from multiprocessing import Process, Queue

class StopMessage(object):
    pass

STOP_MESSAGE = StopMessage()

class AlreadyStartedError(Exception):
    """The producer was previously started, and cannot be restarted"""
    pass

class NotStartedException(Exception):
    """The producer was never started"""
    pass

class ProductionError(Exception):
    """An error occurred in the underlying production process"""
    pass

class MessageHandlingError(ProductionError):
    """
    An error occurred in the underlying production process when attempting
    to handle an inbound message
    """
    def __init__(self, base):
        self.base_exception = base

class ProductionStepError(ProductionError):
    """
    An error occured in the underlying production process during
    the production step.
    """
    def __init__(self, base):
        self.base_exception = base

class Producer(object):
    """
    Abstract base class for all production activities

    Manages a process and its inbound/outbound queues.

    Child classes should implement:
        * handle_message: receive messages from the host application
        * production_step: do the next production step for this process
    """
    __metaclass__ = ABCMeta

    def __init__(self, buffer_size=None):
        """
        Args:
            * buffer_size: how many outbound productions to cache.
                If buffer_size is None, will continue producing for all time
                If buffer_size is an integer, it will fill the outbound queue with
                    exactly that many items. It will only produce again when the 
                    queue drops under the buffer size
        """
        self.process = None
        self.inbound = Queue()
        if buffer_size is None:
            self.outbound = Queue()
        else:
            self.outbound = Queue(maxsize=buffer_size)
        self._did_start = False
        self._running = False

    def _shutdown(self):
        self.inbound.close()
        self.outbound.close()
        self._running = False

    @abstractmethod
    def handle_message(self, msg):
        """Handle an inbound message from the host application"""
        pass

    @abstractmethod
    def production_step(self):
        """Produce the next step in the output sequence"""
        pass

    def run(self, inbound, outbound):
        """
        The "run step" for this process. Handles
        inbound messages, and generating production steps

        Args:
            * inbound: the inbound message queue, which can send commands
                to the process. If a STOP_MSG item is sent,
                the process terminates
            * outbound: the outbound production queue- the output

        NB: I tried having these as `self` accesses, and not parameters,
        but it seems like the queues wouldn't get populated.
        """
        while self._running:
            while not inbound.empty():
                msg = inbound.get_nowait()
                if isinstance(msg, StopMessage):
                    self._shutdown()
                    break
                try:
                    self.handle_message(msg)
                except Exception as e:
                    self.outbound.put(MessageHandlingError(e))
            if not outbound.full():
                try:
                    outbound.put(self.production_step())
                except Exception as e:
                    self.outbound.put(ProductionStepError(e))
        return None

    def start(self):
        """
        Start the child production process
        """
        if self._did_start:
            raise AlreadyStartedError()
        self.process = Process(target=self.run, args=(self.inbound, self.outbound))
        self._did_start = True
        self._running = True
        self.process.start()


    def stop(self):
        """
        Send a stop message to end the child process. The child process
        will take this to shutdown gracefully.
        """
        if self._did_start:
            self.send(STOP_MESSAGE)

    def send(self, msg):
        """
        Send a message to the child process

        Args:
            msg: whatever arbitrary data the child process
                wishes to handle
        """
        self.inbound.put_nowait(msg)

    def get(self, timeout=0.05):
        """
        Return the next message in the outbound queue.

        If that message contains an exception, raises the
        exception instead.

        If the process hasn't been started, starts the process
        instead.
        """
        if not self._did_start:
            raise NotStartedException()
        res = self.outbound.get(timeout=timeout)
        if isinstance(res, ProductionError):
            raise res
        return res
