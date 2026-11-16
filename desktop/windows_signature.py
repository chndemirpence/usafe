"""Windows Authenticode inspection without network retrieval or trust-store edits.

Fail closed if Windows cannot establish trust from its existing local cache.
The caller must also compare the signer thumbprint with reviewed publisher pins.
"""
import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import Path
import uuid


class GUID(c.Structure):
    _fields_ = [("bytes", c.c_ubyte * 16)]


class FileInfo(c.Structure):
    _fields_ = [("size", w.DWORD), ("path", w.LPCWSTR), ("file", w.HANDLE), ("subject", c.c_void_p)]


class TrustData(c.Structure):
    _fields_ = [("size", w.DWORD), ("policy", c.c_void_p), ("sip", c.c_void_p),
                ("ui", w.DWORD), ("revocation", w.DWORD), ("choice", w.DWORD),
                ("file", c.POINTER(FileInfo)), ("action", w.DWORD), ("state", w.HANDLE),
                ("url", w.LPCWSTR), ("flags", w.DWORD), ("context", w.DWORD), ("settings", c.c_void_p)]


class ProviderCertPrefix(c.Structure):
    # Only the first certificate is accessed, so the remaining structure fields
    # are intentionally not represented and this type is never used for strides.
    _fields_ = [("size", w.DWORD), ("certificate", c.c_void_p)]


class ProviderSigner(c.Structure):
    _fields_ = [("size", w.DWORD), ("verify_time", w.FILETIME), ("cert_count", w.DWORD),
                ("certificates", c.POINTER(ProviderCertPrefix)), ("signer_type", w.DWORD),
                ("signer", c.c_void_p), ("error", w.DWORD), ("timestamp_count", w.DWORD),
                ("timestamps", c.c_void_p), ("chain", c.c_void_p)]


def inspect_signature(path):
    if os.name != "nt":
        raise OSError("Windows signature verification requires Windows")
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    trust = c.WinDLL(str(system / "wintrust.dll"))
    crypt = c.WinDLL(str(system / "crypt32.dll"))
    verify = trust.WinVerifyTrust
    verify.argtypes = [w.HWND, c.POINTER(GUID), c.POINTER(TrustData)]
    verify.restype = w.LONG
    provider = trust.WTHelperProvDataFromStateData
    provider.argtypes, provider.restype = [w.HANDLE], c.c_void_p
    signer = trust.WTHelperGetProvSignerFromChain
    signer.argtypes = [c.c_void_p, w.DWORD, w.BOOL, w.DWORD]
    signer.restype = c.POINTER(ProviderSigner)
    prop = crypt.CertGetCertificateContextProperty
    prop.argtypes = [c.c_void_p, w.DWORD, c.c_void_p, c.POINTER(w.DWORD)]
    prop.restype = w.BOOL
    action = GUID((c.c_ubyte * 16).from_buffer_copy(uuid.UUID("00aac56b-cd44-11d0-8cc2-00c04fc295ee").bytes_le))
    file = FileInfo(c.sizeof(FileInfo), str(Path(path).resolve()), None, None)
    data = TrustData()
    data.size, data.ui, data.choice, data.action = c.sizeof(TrustData), 2, 1, 1
    data.file = c.pointer(file)
    # WTD_CACHE_ONLY_URL_RETRIEVAL | WTD_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT.
    # No certificates, CRLs or OCSP are fetched over a direct Windows connection.
    data.flags = 0x1000 | 0x80
    try:
        status = verify(w.HWND(-1), c.byref(action), c.byref(data))
        result = {"Status": "Valid" if status == 0 else f"WindowsTrustError:0x{status & 0xffffffff:08X}",
                  "Thumbprint": "", "Timestamped": False, "NetworkRetrieval": False}
        if status != 0:
            return result
        prov = provider(data.state)
        signed = signer(prov, 0, False, 0) if prov else None
        if not signed or not signed.contents.cert_count or not signed.contents.certificates:
            raise OSError("Windows did not expose the verified signer")
        digest = (c.c_ubyte * 20)()
        length = w.DWORD(20)
        if not prop(signed.contents.certificates.contents.certificate, 3, digest, c.byref(length)) or length.value != 20:
            raise OSError("Unable to read the verified certificate thumbprint")
        result["Thumbprint"] = bytes(digest).hex().upper()
        result["Timestamped"] = signed.contents.timestamp_count > 0
        return result
    finally:
        data.action = 2  # WTD_STATEACTION_CLOSE, including on verification failure.
        verify(w.HWND(-1), c.byref(action), c.byref(data))
