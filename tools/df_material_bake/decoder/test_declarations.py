import unittest
from declaration_probe157 import declarations
class Tests(unittest.TestCase):
 def test_sparse(self):
  r=declarations("dcl_resource_texture2d (float,float,float,float) t7\ndcl_constantbuffer CB4[23], immediateIndexed\ndcl_sampler s3, mode_default\ndcl_uav_typed_texture2d (float,float,float,float) u2")
  self.assertEqual(r["metrics"]["srv"]["uniqueRegisterCount"],1)
  self.assertEqual(r["metrics"]["srv"]["registerSpan"],8)
  self.assertEqual(r["metrics"]["cb"]["registerSpan"],5)
  self.assertEqual(r["rows"][1]["float4Vectors"],23)
 def test_unsupported(self):
  r=declarations("dcl_resource_texture2d t[dynamic]\n// dcl_sampler s5\ndcl_input v0.xy")
  self.assertEqual(len(r["unparsedResourceDeclarations"]),1)
  self.assertEqual(r["metrics"]["sampler"]["registerSpan"],0)
 def test_duplicates(self):
  r=declarations("dcl_sampler s0, mode_default\ndcl_sampler s0, mode_default")
  self.assertEqual(r["metrics"]["sampler"]["uniqueRegisterCount"],1)
  self.assertEqual(r["metrics"]["sampler"]["declarationLines"],2)
if __name__=="__main__":unittest.main()
