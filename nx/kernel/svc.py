from ..types import Result, ResultException

import _nx

def send_sync_request(h):
    result = Result(_nx.svcSendSyncRequest(h))
    
    if result.failed:
        raise ResultException(result)

def connect_to_named_port(name):
    result, handle = _nx.svcConnectToNamedPort(name)
    result = Result(result)

    if result.failed:
        raise ResultException(result)

    return handle

def sleep_thread(nano):
    _nx.svcSleepThread(nano)