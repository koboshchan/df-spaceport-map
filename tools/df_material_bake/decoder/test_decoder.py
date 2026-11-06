import unittest,struct,random
from decoder import decode_payload,DecodeError,sha
def fixture():
    chunk=b"SHEX"+struct.pack("<I",8)+struct.pack("<II",0x50,2)
    return b"DXBC"+bytes(16)+struct.pack("<III",1,52,1)+struct.pack("<I",36)+chunk
class Tests(unittest.TestCase):
    def decode(self,b,offset=0): return decode_payload(b,offset,sha(b))
    def test_valid(self):
        d=self.decode(fixture());self.assertEqual(d["dxbc"]["chunks"][0]["programHeader"]["major"],5)
        self.assertFalse(d["exactDFParity"]);self.assertEqual(d["textureBindings"]["status"],"UNSUPPORTED")
    def test_every_truncation(self):
        b=fixture()
        for n in range(len(b)):
            with self.subTest(n=n),self.assertRaises(DecodeError):self.decode(b[:n])
    def test_negative_offset(self):
        with self.assertRaises(DecodeError):self.decode(fixture(),-1)
    def test_hash(self):
        with self.assertRaises(DecodeError):decode_payload(fixture(),0,"bad")
    def test_count_limit(self):
        b=bytearray(fixture());struct.pack_into("<I",b,28,0xffffffff)
        with self.assertRaises(DecodeError):self.decode(b)
    def test_offset_header(self):
        b=bytearray(fixture());struct.pack_into("<I",b,32,0)
        with self.assertRaises(DecodeError):self.decode(b)
    def test_program_length(self):
        b=bytearray(fixture());struct.pack_into("<I",b,48,0xffffffff)
        with self.assertRaises(DecodeError):self.decode(b)
    def test_size_overrun(self):
        b=bytearray(fixture());struct.pack_into("<I",b,40,0xffffffff)
        with self.assertRaises(DecodeError):self.decode(b)
    def test_unknown_version(self):
        b=bytearray(fixture());struct.pack_into("<I",b,20,99)
        with self.assertRaises(DecodeError):self.decode(b)
    def test_deterministic_mutations_no_crash(self):
        rng=random.Random(91501777)
        for _ in range(10000):
            b=bytearray(fixture())
            for _ in range(rng.randrange(1,5)):b[rng.randrange(len(b))]=rng.randrange(256)
            try:self.decode(b)
            except DecodeError:pass
if __name__=="__main__":unittest.main()
