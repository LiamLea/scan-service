import unittest
import json
from scan_service.main import app
from unittest import mock
from parameterized import  parameterized

class APITest(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()


    @parameterized.expand([
        ({"id": "1", "params": {"hosts": "1.1.1.1"}},),
        ({"id": "1", "param": {"hosts": "1.1.1.1"}},),
        ({"id": "1", "params": {"hosts": "1.1.1.1"}, "other": {}},),
        ({"id": 1, "params": {"hosts": "1.1.1.1"}}, )
    ])
    @mock.patch("views.scan.when_finshed")
    @mock.patch("views.scan.run_scan")
    def test_nmap(self, args, mock_run_scan, mock_callback):

        mock_run_scan.return_value = {"result": "run scan"}
        mock_callback.return_value = True
        reponse = self.client.post("/scan/nmap", data = json.dumps(args).encode())
        result = json.loads(reponse.data.decode())
        self.assertIsInstance(result, dict, "接口调用失败")

    @parameterized.expand([
        (
                {
                    "id": "1",

                    "params": [
                        {
                            "type": "linux",
                            "credential": {},
                            "kafka": {
                                "server": "",
                                "topic": ""
                            }
                        }
                    ]
                },
        ),

        (
                {
                    "id": "1",

                    "params": (
                        {
                            "type": "linux",
                            "credential": {},
                            "kafka": {
                                "server": "",
                                "topic": ""
                            }
                        }
                    )
                },
        )
    ])
    @mock.patch("views.scan.when_finshed")
    @mock.patch("views.scan.run_deploy")
    def test_deploy(self, args, mock_run_deploy, mock_callback):

        mock_run_deploy.return_value = {"result": "run deploy"}
        mock_callback.return_value = True
        reponse = self.client.post("/scan/deploy", data=json.dumps(args).encode())
        result = json.loads(reponse.data.decode())
        self.assertIsInstance(result, dict, "接口调用失败")

    @parameterized.expand([
        (
                {
                    "id": "1",

                    "params": {
                        "type": "linux",
                        "credential": {},
                        "kafka": {
                            "server": "",
                            "topic": ""
                        }
                    }
                },
        ),

    ])
    @mock.patch("views.scan.run_test")
    def test_test(self, args, mock_run_test):
        mock_run_test.return_value = {"result": "run test"}
        reponse = self.client.post("/scan/test", data=json.dumps(args).encode())
        result = json.loads(reponse.data.decode())
        self.assertIsInstance(result, dict, "接口调用失败")

    @parameterized.expand([
        ({"id": "1"},),
        ({"id": "2"},),
        ({"id": 3},),
        (["id", "4"],)
    ])
    @mock.patch("views.scan.future_dict")
    def test_query(self, args, mock_dict):
        mock_dict["1"] = {"result": "query"}
        reponse = self.client.post("/scan/query", data=json.dumps(args).encode())
        result = json.loads(reponse.data.decode())
        self.assertIsInstance(result, dict, "接口调用失败")



if __name__ == '__main__':
    unittest.main()