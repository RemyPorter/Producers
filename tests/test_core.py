import unittest
from context import producers
from producers import producer_core as p
import time

class CountProducer(p.Producer):
    """
    Simple demo class to show how production works.

    Launches a process which counts. Only buffers the next
    ten items.
    """
    def __init__(self):
        super(CountProducer, self).__init__(1)
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

class CoreTest(unittest.TestCase):
    def setUp(self):
        self.count = CountProducer()


    def test_correct_generation(self):
        """The count producer should produce a sequence of numbers"""
        c = self.count
        c.start()
        time.sleep(0.125)
        self.assertEqual(c.get(0.25), 0)
        self.assertEqual(c.get(0.25), 1)

    def test_buffering(self):
        """Initially, the producer should produce only ten numbers"""
        c = self.count
        c.start()
        time.sleep(0.125) #give the process time to generate
        self.assertTrue(c.outbound.full())
        self.assertEqual(c.outbound.qsize(), 1)

    def test_rebuffer(self):
        """If I read past the end of the current buffer, there should be more"""
        c = self.count
        c.start()
        time.sleep(0.125) #generate values
        for i in range(12):
            self.assertEqual(c.get(0.25), i)

    def test_message_passing(self):
        """If I pass a message, the producer receives it"""
        c = self.count
        c.start()
        time.sleep(0.125)
        c.send(50)
        time.sleep(0.125)
        self.assertEqual(c.get(), 50)
        self.assertEqual(c.get(), 51)

    def test_start_required(self):
        """Fetching from an unstarted producer raises an exception"""
        with self.assertRaises(p.NotStartedException):
            self.count.get()

    def tearDown(self):
        time.sleep(0.125)
        self.count.stop()

class InjectableTest(unittest.TestCase):
    def setUp(self):
        def inject_handler(msg, state):
            state['i'] = msg
            print('updating with ' + str(msg))
            return state
        def inject_producer(state):

            i = state.get('i', 0)
            state['i'] = i + 1
            return (state, i)
        self.inject = p.InjectableProducer(inject_producer, inject_handler, {'i': 10}, 1)
        self.inject.start()
        time.sleep(0.25)

    def test_basic_inject_production(self):
        for i in range(10):
            self.assertEqual(self.inject.get(0.25), i + 10)

    def test_state_changes(self):
        self.inject.send(0)
        # flush the buffer
        time.sleep(0.125)
        self.inject.get(0.25)
        time.sleep(0.0125)
        for i in range(10):
            self.assertEqual(self.inject.get(0.25), i)
        

    def tearDown(self):
        time.sleep(0.125)
        self.inject.stop()

if __name__ == "__main__":
    unittest.main()