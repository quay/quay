from _ldap import *
import threading
from ldap.dn import dn2str as dn2str, explode_dn as explode_dn, explode_rdn as explode_rdn, str2dn as str2dn
from ldap.functions import escape_str as escape_str, get_option as get_option, initialize as initialize, set_option as set_option, strf_secs as strf_secs, strp_secs as strp_secs
from ldap.ldapobject import LDAPBytesWarning as LDAPBytesWarning, NO_UNIQUE_ENTRY as NO_UNIQUE_ENTRY
from typing import Any, Optional

LIBLDAP_API_INFO: Any
OPT_NAMES_DICT: Any

class DummyLock:
    def __init__(self) -> None: ...
    def acquire(self) -> None: ...
    def release(self) -> None: ...
LDAPLockBaseClass = DummyLock
LDAPLockBaseClass = threading.Lock

class LDAPLock:
    def __init__(self, lock_class: Optional[Any] = ..., desc: str = ...) -> None: ...
    def acquire(self): ...
    def release(self): ...
OPT_DIAGNOSTIC_MESSAGE = OPT_ERROR_STRING
