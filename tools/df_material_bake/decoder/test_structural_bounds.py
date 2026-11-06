import unittest,struct
from prefix_analysis import analyze_prefix
from optional_analysis import strings,optional_blocks
from decoder import DecodeError
class Bounds(unittest.TestCase):
 def test_prefix_negative_and_overrun(self):
  for n in (-1,65537,2147483647,1):
   self.assertEqual(analyze_prefix(bytes(4)+struct.pack('<i',n))['status'],'UNSUPPORTED')
 def test_prefix_truncated(self):
  for b in (b'',bytes(3),bytes(5),bytes(7)):
   self.assertEqual(analyze_prefix(b)['status'],'UNSUPPORTED')
 def test_optional_negative_length(self):
  with self.assertRaises(DecodeError):optional_blocks(b'p'+struct.pack('<i',-1)+struct.pack('<I',9))
 def test_strings_negative_length(self):
  with self.assertRaises(DecodeError):strings(struct.pack('<ii',1,-1))
