import unittest
from context import producers as p
import time

class CountProducer(p.Producer):
    """
    Simple demo class to show how production works.

    Launches a process which counts. Only buffers the next
    ten items.
    """
    def __init__(self):
        super(CountProducer, self).__init__(10)
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
        time.sleep(0.0125)
        self.assertEqual(c.get(), 0)
        self.assertEqual(c.get(), 1)

    def test_buffering(self):
        """Initially, the producer should produce only ten numbers"""
        c = self.count
        c.start()
        time.sleep(0.0125) #give the process time to generate
        self.assertTrue(c.outbound.full())
        self.assertEqual(c.outbound.qsize(), 10)

    def test_rebuffer(self):
        """If I read past the end of the current buffer, there should be more"""
        c = self.count
        c.start()
        time.sleep(0.0125) #generate values
        for i in range(12):
            self.assertEqual(c.get(), i)

    def test_message_passing(self):
        """If I pass a message, the producer receives it"""
        c = self.count
        c.start()
        time.sleep(0.0125)
        c.send(50)
        time.sleep(0.0125)
        self.assertEqual(c.get(), 50)
        self.assertEqual(c.get(), 51)

    def test_start_required(self):
        """Fetching from an unstarted producer raises an exception"""
        with self.assertRaises(p.NotStartedException):
            self.count.get()

    def tearDown(self):
        time.sleep(0.0125)
        self.count.stop()

if __name__ == "__main__":
    unittest.main()