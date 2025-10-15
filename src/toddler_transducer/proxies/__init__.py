"""
Proxies

Package containing all the code for proxying things when not on the raspberry pi.
"""
from .multithreading_proxy import MultithreadingValueProxy
from .mfrc522_proxy import SimpleMFRC522Proxy

__all__ = ['MultithreadingValueProxy', 'SimpleMFRC522Proxy']
