
import unittest
import history.utils as HUtils

class TestUtils(unittest.TestCase):
  def setUp(self):
      pass

  def test_generate_arguments(self):
    arguments = {"status": 4, "last": 1, "rowtype": 2}
    statement, arg_values = HUtils.get_built_statement_from_kwargs("id", status=4, last=1, rowtype=2)
    print(statement)
    print(arg_values)
    self.assertTrue(statement.find("status") >= 0)
    self.assertTrue(statement.find("last") >= 0)
    self.assertTrue(statement.find("rowtype") >= 0)
    self.assertTrue(statement.find(" ORDER BY id") >= 0)

  def test_generate_arguments_kwargs(self):
    def inner_call(expid, **kwargs):
      return HUtils.get_built_statement_from_kwargs("created", **kwargs)
    arguments = {"status": 4, "last": 1, "rowtype": 2}
    answer, arg_values = inner_call("a28v", **arguments)
    print(answer)
    print(arg_values)
    self.assertTrue(answer.find("status") >= 0)
    self.assertTrue(answer.find("last") >= 0)
    self.assertTrue(answer.find("rowtype") >= 0)
    self.assertTrue(answer.find(" ORDER BY created") >= 0)

if __name__ == "__main__":
  unittest.main()