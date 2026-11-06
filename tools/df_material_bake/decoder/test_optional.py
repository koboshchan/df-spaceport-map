import unittest,struct
from optional_analysis import optional_blocks,strings
from decoder import DecodeError
class OptionalTests(unittest.TestCase):
 def test_blocks(self):
  d=struct.pack("<ii",1,5)+b"View\0"; t=b"u"+struct.pack("<I",len(d))+d
  t+=struct.pack("<I",len(t)+4)
  self.assertEqual(optional_blocks(t)["blocks"][0]["candidateStringArray"][0]["text"],"View")
  for i in range(len(t)):
   with self.assertRaises(DecodeError): optional_blocks(t[:i])
 def test_bad_length(self):
  with self.assertRaises(DecodeError):optional_blocks(b"u\xff\xff\xff\xff"+struct.pack("<I",9))
 def test_strings(self):
  for d in [b"",struct.pack("<i",-1),struct.pack("<ii",1,9),struct.pack("<ii",1,1)+b"x",struct.pack("<i",0)+b"x"]:
   with self.assertRaises(DecodeError):strings(d)
if __name__=="__main__":unittest.main()
