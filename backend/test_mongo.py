"""MongoDB connection diagnostic - run once then delete"""
import os, ssl as ssl_mod
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("C:/Users/azim4/Downloads/learnsphere-ai/backend/.env")
uri = os.getenv("MONGODB_URI", "")
print("URI prefix:", uri[:50])

tests = [
    ("ssl=False", dict(ssl=False, serverSelectionTimeoutMS=8000)),
    ("tls=True,AllowInvalidCerts", dict(tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=8000)),
    ("no extra args", dict(serverSelectionTimeoutMS=8000)),
]

for label, kwargs in tests:
    try:
        c = MongoClient(uri, **kwargs)
        c.admin.command("ping")
        print(f"SUCCESS [{label}]")
        c.close()
        break
    except Exception as e:
        print(f"FAILED  [{label}]: {str(e)[:120]}")

# Test custom SSL context
ctx = ssl_mod.SSLContext(ssl_mod.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl_mod.CERT_NONE
ctx.minimum_version = ssl_mod.TLSVersion.TLSv1_2
try:
    c4 = MongoClient(uri, ssl_context=ctx, serverSelectionTimeoutMS=8000)
    c4.admin.command("ping")
    print("SUCCESS [custom ssl_context TLS1.2+]")
    c4.close()
except Exception as e:
    print(f"FAILED  [custom ssl_context]: {str(e)[:120]}")

print("Done.")
