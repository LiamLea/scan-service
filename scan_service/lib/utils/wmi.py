from scan_service.lib.framework import AuthException
from scan_service.lib.framework import BusinessException
try:
    import wmi_client_wrapper
    from sh import ErrorReturnCode
    from sh import TimeoutException
except ImportError:
    pass

class WMIC:
    def __init__(self, credential):
        self.credential_dict = credential
        self.wmi_client = wmi_client_wrapper.WmiClientWrapper(**credential)

    def query(self, command):
        try:
            result = self.wmi_client.query(command)
        except ErrorReturnCode:
            raise AuthException("凭证错误")
        except TimeoutException:
            raise TimeoutException("主机无法连接")
        except Exception:
            raise BusinessException("wmi连接异常")
        return result
